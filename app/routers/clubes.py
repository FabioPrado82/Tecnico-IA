from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Optional

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.core import Clube

router = APIRouter(prefix="/clubes", tags=["clubes"], dependencies=[Depends(usuario_atual)])


class ClubeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    logo_url: Optional[str] = None
    cor_primaria: Optional[str] = None
    cor_secundaria: Optional[str] = None
    slogan: Optional[str] = None
    limite_patrocinadores: int


@router.get("/{clube_id}", response_model=ClubeOut)
def obter_clube(clube_id: int, db: Session = Depends(get_db)):
    clube = db.get(Clube, clube_id)
    if not clube:
        raise HTTPException(status_code=404, detail="Clube não encontrado")
    return clube
