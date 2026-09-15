from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Optional

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.core import Adversario

router = APIRouter(prefix="/adversarios", tags=["adversarios"], dependencies=[Depends(usuario_atual)])


class AdversarioCreate(BaseModel):
    nome: str
    logo_url: Optional[str] = None


class AdversarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    logo_url: Optional[str] = None


@router.post("", response_model=AdversarioOut, status_code=201)
def criar_adversario(dados: AdversarioCreate, db: Session = Depends(get_db)):
    adversario = Adversario(**dados.model_dump())
    db.add(adversario)
    db.commit()
    db.refresh(adversario)
    return adversario


@router.get("", response_model=list[AdversarioOut])
def listar_adversarios(db: Session = Depends(get_db)):
    return db.query(Adversario).order_by(Adversario.nome).all()
