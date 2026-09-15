"""
Endpoint público do link enviado no WhatsApp — sem login, só o token identifica
o atleta e a partida. É a página que o atleta vê ao abrir o link.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.core import Atleta, Adversario
from app.models.partida import Convocacao, Partida
from app.schemas.core import ConfirmacaoPresenca

router = APIRouter(prefix="/confirmar", tags=["confirmacao-publica"])


@router.get("/{token}")
def ver_confirmacao(token: str, db: Session = Depends(get_db)):
    convocacao = db.query(Convocacao).filter(Convocacao.link_token == token).first()
    if not convocacao:
        raise HTTPException(status_code=404, detail="Link inválido ou expirado")

    partida = db.get(Partida, convocacao.partida_id)
    atleta = db.get(Atleta, convocacao.atleta_id)
    adversario = db.get(Adversario, partida.adversario_id)

    # Link expira quando a partida já foi finalizada — sem coluna de expiração
    # dedicada, validado direto contra o status da partida (decisão já registrada
    # no schema).
    if partida.status == "finalizada":
        raise HTTPException(status_code=410, detail="Este link não está mais disponível")

    return {
        "atleta_nome": atleta.nome,
        "adversario_nome": adversario.nome if adversario else None,
        "data_hora": partida.data_hora,
        "horario_chegada_vestiario": partida.horario_chegada_vestiario,
        "local_nome": partida.local_nome,
        "fase": partida.fase,
        "presenca_confirmada": convocacao.presenca_confirmada,
    }


@router.post("/{token}")
def responder_confirmacao(token: str, resposta: ConfirmacaoPresenca, db: Session = Depends(get_db)):
    convocacao = db.query(Convocacao).filter(Convocacao.link_token == token).first()
    if not convocacao:
        raise HTTPException(status_code=404, detail="Link inválido ou expirado")

    partida = db.get(Partida, convocacao.partida_id)
    if partida.status == "finalizada":
        raise HTTPException(status_code=410, detail="Este link não está mais disponível")

    convocacao.presenca_confirmada = resposta.presenca_confirmada
    convocacao.presenca_respondida_em = datetime.now(timezone.utc)
    if resposta.presenca_confirmada == "recusado":
        convocacao.motivo_indisponibilidade = resposta.motivo_indisponibilidade
    if resposta.presenca_confirmada == "confirmado":
        convocacao.jogos_antes_desta_partida = resposta.jogos_antes_desta_partida

    db.commit()
    return {"ok": True, "presenca_confirmada": convocacao.presenca_confirmada}
