"""
Lógica compartilhada do Modo 5 (retrospecto). Extraída num módulo próprio pra
poder ser chamada tanto pelo endpoint manual (POST /retrospecto/gerar) quanto
automaticamente ao finalizar uma partida (PATCH /partidas/{id}/finalizar) —
sem duplicar a lógica nos dois lugares.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.ai_client import chamar_ia
from app.models.partida import Partida
from app.models.scouting import ScoutingAdversario, ComentarioAdversario
from app.models.tempo_real import EventoPartida, CicloIA
from app.models.pos_jogo_e_extras import RetrospectoPartida

INSTRUCAO_RETROSPECTO = (
    "Gere um retrospecto da partida com três seções: pontos positivos, "
    "pontos negativos e lições aprendidas. Cruze o que foi previsto no "
    "scouting pré-jogo com o que de fato aconteceu (ex: se o scouting "
    "alertou sobre bola parada do adversário e o time sofreu gol de bola "
    "parada, isso é uma lição relevante). Gere também um comentário curto "
    "(1-2 frases) para o histórico deste adversário específico, com o que "
    "foi aprendido sobre o padrão de jogo dele neste confronto. Responda em "
    "JSON: {\"pontos_positivos\": str, \"pontos_negativos\": str, "
    "\"licoes_aprendidas\": str, \"comentario_adversario\": str}."
)


def gerar_retrospecto_para_partida(partida_id: int, partida: Partida, db: Session) -> RetrospectoPartida:
    """
    Faz a chamada à IA e persiste o retrospecto + comentário automático do
    adversário. Levanta RuntimeError se a IA falhar — quem chama decide como
    tratar (endpoint manual devolve 503; finalização de partida só registra
    o problema sem impedir o fechamento da partida em si).
    """
    ja_existe = db.query(RetrospectoPartida).filter(RetrospectoPartida.partida_id == partida_id).first()
    if ja_existe:
        return ja_existe

    scouting_respondido = db.query(ScoutingAdversario).filter(
        ScoutingAdversario.partida_id == partida_id, ScoutingAdversario.resposta.isnot(None)
    ).all()
    eventos = db.query(EventoPartida).filter(EventoPartida.partida_id == partida_id).order_by(EventoPartida.minuto).all()
    ciclos = db.query(CicloIA).filter(CicloIA.partida_id == partida_id).all()

    contexto = {
        "placar_nosso": partida.placar_nosso,
        "placar_adversario": partida.placar_adversario,
        "scouting_pre_jogo": [{"pergunta": s.pergunta, "resposta": s.resposta} for s in scouting_respondido],
        "eventos": [{"minuto": e.minuto, "tipo": e.tipo_evento, "time": e.time} for e in eventos],
        "ciclos_ia": [
            {"pergunta": c.pergunta_ia, "resposta": c.resposta_staff, "sugestao": c.sugestao_ia}
            for c in ciclos
        ],
    }

    resultado = chamar_ia(INSTRUCAO_RETROSPECTO, contexto, max_tokens=1500)  # pode levantar RuntimeError

    retrospecto = RetrospectoPartida(
        partida_id=partida_id,
        pontos_positivos=resultado.get("pontos_positivos"),
        pontos_negativos=resultado.get("pontos_negativos"),
        licoes_aprendidas=resultado.get("licoes_aprendidas"),
        status="rascunho_ia",
        gerado_em=datetime.now(timezone.utc),
    )
    db.add(retrospecto)

    comentario_texto = resultado.get("comentario_adversario")
    if comentario_texto:
        db.add(ComentarioAdversario(
            adversario_id=partida.adversario_id,
            partida_id=partida_id,
            origem="ia_pos_jogo",
            comentario=comentario_texto,
            autor="Técnico IA",
            criado_em=datetime.now(timezone.utc),
        ))

    db.commit()
    db.refresh(retrospecto)
    return retrospecto
