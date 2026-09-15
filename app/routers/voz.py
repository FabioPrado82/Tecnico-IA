from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.core.ai_client import chamar_ia
from app.models.partida import Partida, Convocacao
from app.models.core import Atleta
from app.models.pos_jogo_e_extras import TranscricaoVoz
from app.schemas.extras import InterpretarVozIn, TranscricaoVozOut

router = APIRouter(prefix="/partidas/{partida_id}/voz", tags=["voz"], dependencies=[Depends(usuario_atual)])


@router.post("/interpretar", response_model=TranscricaoVozOut, status_code=201)
def interpretar_voz(partida_id: int, dados: InterpretarVozIn, db: Session = Depends(get_db)):
    """
    Modo 8 — interpreta a transcrição bruta (já convertida pelo STT do
    navegador) em texto estruturado. Nunca comita direto num evento/resposta
    — fica salvo aqui pra a tela mostrar e o auxiliar confirmar manualmente.
    """
    partida = db.get(Partida, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida não encontrada")

    if dados.contexto == "evento":
        jogadores_em_campo = db.query(Atleta.id, Atleta.nome).join(
            Convocacao, Convocacao.atleta_id == Atleta.id
        ).filter(Convocacao.partida_id == partida_id, Convocacao.titular.is_(True)).all()
        contexto = {
            "transcricao": dados.transcricao_bruta,
            "jogadores_em_campo": [{"id": j.id, "nome": j.nome} for j in jogadores_em_campo],
            "tipos_evento_possiveis": [
                "gol", "cartao_amarelo", "cartao_vermelho", "falta",
                "substituicao", "escanteio",
            ],
        }
        instrucao = (
            "Interprete a transcrição de voz do auxiliar e identifique tipo de "
            "evento, time (nosso/adversário) e jogador envolvido, usando fuzzy "
            "matching contra a lista de jogadores em campo (apelidos e "
            "pronúncias imprecisas são esperados). Se a transcrição for "
            "ambígua ou não bater com nada esperado, retorne isso "
            "explicitamente. Responda em JSON: {\"tipo_evento\": str|null, "
            "\"time\": str|null, \"atleta_id\": int|null, \"ambiguo\": bool, "
            "\"observacao\": str}."
        )
    else:  # resposta_ciclo
        contexto = {
            "transcricao": dados.transcricao_bruta,
            "opcoes_disponiveis": dados.opcoes_disponiveis or [],
        }
        instrucao = (
            "Identifique qual das opções disponíveis mais se aproxima do que "
            "foi dito na transcrição. Se ambíguo, retorne isso explicitamente "
            "em vez de forçar uma opção. Responda em JSON: {\"opcao_escolhida\": "
            "str|null, \"ambiguo\": bool}."
        )

    try:
        interpretacao = chamar_ia(instrucao, contexto, max_tokens=1024)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    registro = TranscricaoVoz(
        partida_id=partida_id,
        contexto=dados.contexto,
        transcricao_bruta=dados.transcricao_bruta,
        interpretacao=interpretacao,
        confirmado_pelo_auxiliar=False,
        criado_em=datetime.now(timezone.utc),
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


@router.patch("/transcricoes/{transcricao_id}/confirmar", response_model=TranscricaoVozOut)
def confirmar_transcricao(partida_id: int, transcricao_id: int, db: Session = Depends(get_db)):
    """
    Marca que o auxiliar confirmou a interpretação (o registro real do
    evento/resposta acontece pelos endpoints normais, chamados pelo cliente
    depois dessa confirmação — este endpoint só fecha o log de auditoria).
    """
    registro = db.get(TranscricaoVoz, transcricao_id)
    if not registro or registro.partida_id != partida_id:
        raise HTTPException(status_code=404, detail="Transcrição não encontrada")
    registro.confirmado_pelo_auxiliar = True
    db.commit()
    db.refresh(registro)
    return registro
