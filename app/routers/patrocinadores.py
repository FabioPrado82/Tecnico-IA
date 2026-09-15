from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Optional

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.divulgacao import Patrocinador

router = APIRouter(prefix="/patrocinadores", tags=["patrocinadores"], dependencies=[Depends(usuario_atual)])


class PatrocinadorCreate(BaseModel):
    clube_id: int
    nome: str
    logo_url: Optional[str] = None


class PatrocinadorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    clube_id: int
    nome: str
    logo_url: Optional[str] = None
    ativo: bool


@router.post("", response_model=PatrocinadorOut, status_code=201)
def criar_patrocinador(dados: PatrocinadorCreate, db: Session = Depends(get_db)):
    patrocinador = Patrocinador(criado_em=datetime.now(timezone.utc), **dados.model_dump())
    db.add(patrocinador)
    db.commit()
    db.refresh(patrocinador)
    return patrocinador


@router.get("", response_model=list[PatrocinadorOut])
def listar_patrocinadores(clube_id: int, ativo: bool = True, db: Session = Depends(get_db)):
    return db.query(Patrocinador).filter(
        Patrocinador.clube_id == clube_id, Patrocinador.ativo == ativo
    ).order_by(Patrocinador.nome).all()
