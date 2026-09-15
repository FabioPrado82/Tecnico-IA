from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.core import Atleta
from app.models.usuario import Usuario
from app.schemas.core import AtletaCreate, AtletaOut

router = APIRouter(prefix="/atletas", tags=["atletas"], dependencies=[Depends(usuario_atual)])


@router.post("", response_model=AtletaOut, status_code=201)
def criar_atleta(dados: AtletaCreate, db: Session = Depends(get_db)):
    atleta = Atleta(**dados.model_dump())
    db.add(atleta)
    db.commit()
    db.refresh(atleta)
    return atleta


@router.get("", response_model=list[AtletaOut])
def listar_atletas(clube_id: int, ativo: bool | None = None, db: Session = Depends(get_db)):
    query = db.query(Atleta).filter(Atleta.clube_id == clube_id)
    if ativo is not None:
        query = query.filter(Atleta.ativo == ativo)
    return query.order_by(Atleta.nome).all()


@router.get("/{atleta_id}", response_model=AtletaOut)
def obter_atleta(atleta_id: int, db: Session = Depends(get_db)):
    atleta = db.get(Atleta, atleta_id)
    if not atleta:
        raise HTTPException(status_code=404, detail="Atleta não encontrado")
    return atleta
