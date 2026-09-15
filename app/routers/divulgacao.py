from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Optional

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.divulgacao import ArteDivulgacao

router = APIRouter(prefix="/partidas/{partida_id}/artes-divulgacao", tags=["divulgacao"], dependencies=[Depends(usuario_atual)])


class ArteDivulgacaoCreate(BaseModel):
    tipo: str
    template: str = "padrao"
    jogadores_destaque: list[int] = []
    frase_personalizada: Optional[str] = None
    patrocinadores_exibidos: list[int] = []
    criado_por: str


class ArteDivulgacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    partida_id: int
    tipo: str
    template: str
    jogadores_destaque: Optional[list[int]] = None
    frase_personalizada: Optional[str] = None
    patrocinadores_exibidos: Optional[list[int]] = None


@router.post("", response_model=ArteDivulgacaoOut, status_code=201)
def registrar_arte(partida_id: int, dados: ArteDivulgacaoCreate, db: Session = Depends(get_db)):
    """
    Só guarda os metadados de qual arte foi gerada — a renderização/imagem em
    si acontece no navegador (template fixo, não IA de imagem), esse endpoint
    é só o histórico de quando/como cada arte foi montada.
    """
    arte = ArteDivulgacao(
        partida_id=partida_id, criado_em=datetime.now(timezone.utc), **dados.model_dump()
    )
    db.add(arte)
    db.commit()
    db.refresh(arte)
    return arte


@router.get("", response_model=list[ArteDivulgacaoOut])
def listar_artes(partida_id: int, db: Session = Depends(get_db)):
    return db.query(ArteDivulgacao).filter(ArteDivulgacao.partida_id == partida_id).order_by(ArteDivulgacao.id.desc()).all()
