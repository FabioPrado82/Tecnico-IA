from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.core.retrospecto_service import gerar_retrospecto_para_partida
from app.models.partida import Partida
from app.models.pos_jogo_e_extras import RetrospectoPartida
from app.schemas.extras import RetrospectoOut, RetrospectoAprovar

router = APIRouter(prefix="/partidas/{partida_id}/retrospecto", tags=["pos-jogo"], dependencies=[Depends(usuario_atual)])


@router.post("/gerar", response_model=RetrospectoOut, status_code=201)
def gerar_retrospecto(partida_id: int, db: Session = Depends(get_db)):
    """
    Modo 5 — cruza o scouting pré-jogo com o que de fato aconteceu (eventos +
    ciclos) e gera o retrospecto como rascunho, mais um comentário automático
    pro histórico do adversário. Fica como 'rascunho_ia' até a comissão aprovar.
    """
    partida = db.get(Partida, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida não encontrada")

    try:
        return gerar_retrospecto_para_partida(partida_id, partida, db)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.patch("/aprovar", response_model=RetrospectoOut)
def aprovar_retrospecto(partida_id: int, dados: RetrospectoAprovar, db: Session = Depends(get_db)):
    """Comissão revisa (podendo editar o texto) e aprova o retrospecto."""
    retrospecto = db.query(RetrospectoPartida).filter(RetrospectoPartida.partida_id == partida_id).first()
    if not retrospecto:
        raise HTTPException(status_code=404, detail="Retrospecto ainda não foi gerado")

    if dados.pontos_positivos is not None:
        retrospecto.pontos_positivos = dados.pontos_positivos
    if dados.pontos_negativos is not None:
        retrospecto.pontos_negativos = dados.pontos_negativos
    if dados.licoes_aprendidas is not None:
        retrospecto.licoes_aprendidas = dados.licoes_aprendidas

    retrospecto.status = "aprovado"
    retrospecto.revisado_por = dados.revisado_por
    retrospecto.revisado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(retrospecto)
    return retrospecto
