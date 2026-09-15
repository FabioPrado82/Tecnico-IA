from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.core.retrospecto_service import gerar_retrospecto_para_partida
from app.models.core import Atleta
from app.models.partida import Partida, Convocacao
from app.schemas.core import PartidaCreate, PartidaOut, ConvocacaoOut

router = APIRouter(prefix="/partidas", tags=["partidas"], dependencies=[Depends(usuario_atual)])


class FinalizarPartidaIn(BaseModel):
    placar_nosso: int
    placar_adversario: int


@router.post("", response_model=PartidaOut, status_code=201)
def criar_partida(dados: PartidaCreate, db: Session = Depends(get_db)):
    """
    Cria a partida e já gera automaticamente uma linha de convocação (com
    link_token próprio) para cada atleta ativo do clube — é o gatilho que
    abre o processo de confirmação de presença via link.
    """
    partida = Partida(**dados.model_dump())
    db.add(partida)
    db.flush()  # garante o id da partida sem fechar a transação ainda

    atletas_ativos = db.query(Atleta).filter(
        Atleta.clube_id == dados.clube_id, Atleta.ativo.is_(True)
    ).all()
    for atleta in atletas_ativos:
        db.add(Convocacao(partida_id=partida.id, atleta_id=atleta.id))

    db.commit()
    db.refresh(partida)
    return partida


@router.get("", response_model=list[PartidaOut])
def listar_partidas(clube_id: int, status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Partida).filter(Partida.clube_id == clube_id)
    if status:
        query = query.filter(Partida.status == status)
    return query.order_by(Partida.data_hora.desc()).all()


@router.get("/{partida_id}", response_model=PartidaOut)
def obter_partida(partida_id: int, db: Session = Depends(get_db)):
    partida = db.get(Partida, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida não encontrada")
    return partida


@router.get("/{partida_id}/convocacao", response_model=list[ConvocacaoOut])
def listar_convocacao(partida_id: int, db: Session = Depends(get_db)):
    """Painel que a comissão usa para acompanhar quem já confirmou presença."""
    return db.query(Convocacao).filter(Convocacao.partida_id == partida_id).all()


@router.patch("/{partida_id}/finalizar")
def finalizar_partida(partida_id: int, dados: FinalizarPartidaIn, db: Session = Depends(get_db)):
    """
    Fecha a partida (placar final, status='finalizada', periodo_atual=
    'finalizado') e já dispara a geração do retrospecto (Modo 5)
    automaticamente. Se a IA falhar (ex: sem chave configurada), a partida
    ainda assim fica finalizada — o retrospecto pode ser gerado manualmente
    depois via POST /retrospecto/gerar. Fechar a partida nunca deve travar
    por causa de um problema externo à IA.
    """
    partida = db.get(Partida, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida não encontrada")
    if partida.status == "finalizada":
        raise HTTPException(status_code=400, detail="Esta partida já está finalizada")

    partida.placar_nosso = dados.placar_nosso
    partida.placar_adversario = dados.placar_adversario
    partida.status = "finalizada"
    partida.periodo_atual = "finalizado"
    db.commit()
    db.refresh(partida)

    retrospecto_gerado = False
    erro_retrospecto = None
    try:
        gerar_retrospecto_para_partida(partida_id, partida, db)
        retrospecto_gerado = True
    except RuntimeError as e:
        erro_retrospecto = str(e)

    return {
        "partida": PartidaOut.model_validate(partida),
        "retrospecto_gerado": retrospecto_gerado,
        "erro_retrospecto": erro_retrospecto,
    }
