from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Optional

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.core import Campeonato

router = APIRouter(prefix="/campeonatos", tags=["campeonatos"], dependencies=[Depends(usuario_atual)])


class CampeonatoCreate(BaseModel):
    clube_id: int
    nome: str
    temporada: Optional[str] = None
    fase_atual: Optional[str] = None


class CampeonatoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    clube_id: int
    nome: str
    temporada: Optional[str] = None
    fase_atual: Optional[str] = None
    status: str


@router.post("", response_model=CampeonatoOut, status_code=201)
def criar_campeonato(dados: CampeonatoCreate, db: Session = Depends(get_db)):
    campeonato = Campeonato(**dados.model_dump())
    db.add(campeonato)
    db.commit()
    db.refresh(campeonato)
    return campeonato


@router.get("", response_model=list[CampeonatoOut])
def listar_campeonatos(clube_id: int, db: Session = Depends(get_db)):
    return db.query(Campeonato).filter(Campeonato.clube_id == clube_id).order_by(Campeonato.id.desc()).all()
