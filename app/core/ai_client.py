"""
Cliente da API da Claude — usado pelos 8 modos documentados em
logica_tecnico_ia.md. Centralizado aqui pra não duplicar a lógica de
autenticação/erro em cada endpoint que precisa chamar a IA.
"""
import json
from anthropic import Anthropic, APIError

from app.core.config import settings

PERSONA_BASE = """Você é o auxiliar técnico de IA do Save FC. Fala como um profissional de futebol
experiente: direto, curto, sem rodeios — o usuário está lendo isso no meio de um
jogo ou numa reunião de preparação, não tem tempo para textão.
Baseie toda sugestão nos dados fornecidos. Nunca invente informação sobre o
adversário, o atleta ou o histórico que não esteja no contexto.
Se os dados forem insuficientes para uma recomendação segura, diga isso
explicitamente em vez de arriscar um palpite."""

_client: Anthropic | None = None


def get_client() -> Anthropic:
    global _client
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY não configurada. Veja .env.example — "
            "sem ela, nenhum dos 8 modos de IA funciona."
        )
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def chamar_ia(instrucao_especifica: str, contexto: dict, max_tokens: int = 1024) -> dict:
    """
    Faz uma chamada à Claude combinando a persona base + a instrução do modo
    específico (Modo 1 a 8) + o contexto montado pela aplicação. Espera
    resposta em JSON — força isso via instrução explícita no prompt.
    """
    client = get_client()

    prompt = f"""{instrucao_especifica}

Contexto (JSON):
{json.dumps(contexto, ensure_ascii=False, indent=2)}

Responda APENAS com um JSON válido, sem markdown, sem texto antes ou depois."""

    try:
        extra_headers = {}
        if settings.anthropic_workspace_id:
            extra_headers["anthropic-workspace-id"] = settings.anthropic_workspace_id

        resposta = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=max_tokens,
            system=PERSONA_BASE,
            messages=[{"role": "user", "content": prompt}],
            extra_headers=extra_headers,
        )
    except APIError as e:
        raise RuntimeError(f"Erro ao chamar a API da Claude: {e}") from e

    texto = next((bloco.text for bloco in resposta.content if bloco.type == "text"), None)
    if texto is None:
        return {"erro_parsing": True, "texto_bruto": None, "detalhe": "Nenhum bloco de texto na resposta da IA."}
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        # A IA não seguiu o formato pedido — melhor devolver o texto bruto
        # pra investigar do que quebrar silenciosamente.
        return {"erro_parsing": True, "texto_bruto": texto}
