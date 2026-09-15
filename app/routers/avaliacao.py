from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.models.core import Atleta
from app.models.avaliacao import SessaoAvaliacao, AvaliacaoAtleta
from app.schemas.avaliacao import (
    SessaoAvaliacaoCreate, SessaoAvaliacaoOut, SessaoAvaliacaoPublica,
    AtletaParaAvaliar, EnviarAvaliacoes,
)

router = APIRouter(tags=["avaliacao"])


@router.post("/avaliacoes/sessoes", response_model=SessaoAvaliacaoOut, status_code=201, dependencies=[Depends(usuario_atual)])
def criar_sessao_avaliacao(dados: SessaoAvaliacaoCreate, db: Session = Depends(get_db)):
    """
    Gera o link único pra mandar ao técnico. Cobre todos os atletas ativos do
    clube no momento da criação — a lista fica fixa a partir daqui, mesmo
    que algum atleta seja desativado depois.
    """
    tem_ativos = db.query(Atleta).filter(Atleta.clube_id == dados.clube_id, Atleta.ativo.is_(True)).first()
    if not tem_ativos:
        raise HTTPException(status_code=400, detail="Nenhum atleta ativo cadastrado para esse clube")

    sessao = SessaoAvaliacao(clube_id=dados.clube_id, criado_em=datetime.now(timezone.utc))
    db.add(sessao)
    db.commit()
    db.refresh(sessao)

    return SessaoAvaliacaoOut(
        id=sessao.id, clube_id=sessao.clube_id, link_token=str(sessao.link_token),
        status=sessao.status, avaliador_nome=sessao.avaliador_nome,
    )


@router.get("/avaliar/{token}", response_model=SessaoAvaliacaoPublica)
def ver_sessao_avaliacao(token: str, db: Session = Depends(get_db)):
    """Página pública que o técnico vê ao abrir o link — sem login."""
    sessao = db.query(SessaoAvaliacao).filter(SessaoAvaliacao.link_token == token).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Link inválido")

    atletas = db.query(Atleta).filter(Atleta.clube_id == sessao.clube_id, Atleta.ativo.is_(True)).order_by(Atleta.nome).all()

    lista = []
    for atleta in atletas:
        ja_avaliado = db.query(AvaliacaoAtleta).filter(
            AvaliacaoAtleta.atleta_id == atleta.id,
            AvaliacaoAtleta.avaliado_por == sessao.avaliador_nome,
        ).first() is not None if sessao.avaliador_nome else False
        lista.append(AtletaParaAvaliar(
            atleta_id=atleta.id, nome=atleta.nome,
            posicao_principal=atleta.posicao_principal, ja_avaliado=ja_avaliado,
        ))

    return SessaoAvaliacaoPublica(avaliador_nome=sessao.avaliador_nome, status=sessao.status, atletas=lista)


@router.post("/avaliar/{token}", response_model=SessaoAvaliacaoPublica)
def enviar_avaliacoes(token: str, dados: EnviarAvaliacoes, db: Session = Depends(get_db)):
    """
    Recebe as notas de um ou mais atletas de uma vez. Pode ser chamado várias
    vezes (o técnico avalia aos poucos) — só quando `finalizar=true` a sessão
    fecha de vez.
    """
    sessao = db.query(SessaoAvaliacao).filter(SessaoAvaliacao.link_token == token).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Link inválido")
    if sessao.status == "concluida":
        raise HTTPException(status_code=410, detail="Essa avaliação já foi concluída")

    sessao.avaliador_nome = dados.avaliador_nome
    sessao.status = "em_andamento"

    ids_validos = {a.id for a in db.query(Atleta.id).filter(Atleta.clube_id == sessao.clube_id).all()}

    for nota in dados.notas:
        if nota.atleta_id not in ids_validos:
            continue  # ignora silenciosamente um id fora da lista dessa sessão

        if nota.posicao_principal:
            atleta = db.get(Atleta, nota.atleta_id)
            atleta.posicao_principal = nota.posicao_principal

        avaliacao = AvaliacaoAtleta(
            atleta_id=nota.atleta_id,
            data_avaliacao=date.today(),
            avaliado_por=dados.avaliador_nome,
            **nota.model_dump(exclude={"atleta_id", "posicao_principal"}),
        )
        db.add(avaliacao)

    if dados.finalizar:
        sessao.status = "concluida"
        sessao.concluido_em = datetime.now(timezone.utc)

    db.commit()
    return ver_sessao_avaliacao(token, db)
