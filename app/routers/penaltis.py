from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.core.ai_client import chamar_ia
from app.models.partida import Partida, Convocacao
from app.models.core import Atleta
from app.models.pos_jogo_e_extras import PenaltiCobranca, PenaltiSugestaoOrdem
from app.schemas.extras import PenaltiSugestaoOut, PenaltiOrdemFinal, PenaltiCobrancaCreate, PenaltiCobrancaOut

router = APIRouter(prefix="/partidas/{partida_id}/penaltis", tags=["penaltis"], dependencies=[Depends(usuario_atual)])


@router.post("/sugestao-ordem", response_model=list[PenaltiSugestaoOut], status_code=201)
def gerar_sugestao_ordem(partida_id: int, db: Session = Depends(get_db)):
    """
    Modo 7 — sugere ordem de batedores. Aproveitamento é calculado pela
    aplicação (não pela IA), pra garantir que o número é sempre exato.

    Simplificação desta versão: usa os convocados como titulares (`titular =
    true`) como proxy de "quem está em campo" — ainda não rastreamos
    substituições em tempo real o suficiente pra saber a escalação exata no
    momento da disputa.
    """
    partida = db.get(Partida, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida não encontrada")

    ja_existe = db.query(PenaltiSugestaoOrdem).filter(PenaltiSugestaoOrdem.partida_id == partida_id).first()
    if ja_existe:
        return db.query(PenaltiSugestaoOrdem).filter(PenaltiSugestaoOrdem.partida_id == partida_id).all()

    titulares = db.query(Convocacao, Atleta).join(Atleta, Convocacao.atleta_id == Atleta.id).filter(
        Convocacao.partida_id == partida_id, Convocacao.titular.is_(True)
    ).all()
    if not titulares:
        raise HTTPException(status_code=400, detail="Nenhum titular convocado para esta partida ainda")

    atletas_contexto = []
    for _, atleta in titulares:
        cobrancas = db.query(PenaltiCobranca).filter(
            PenaltiCobranca.lado == "nosso", PenaltiCobranca.atleta_id == atleta.id
        ).all()
        total = len(cobrancas)
        gols = sum(1 for c in cobrancas if c.resultado == "gol")
        aproveitamento = round((gols / total) * 100, 2) if total >= 3 else None
        atletas_contexto.append({
            "atleta_id": atleta.id,
            "nome": atleta.nome,
            "total_cobrancas_historicas": total,
            "aproveitamento_pct": aproveitamento,
        })

    instrucao = (
        "Sugira uma ordem de batedores entre os atletas listados como em campo, "
        "do 1º ao 5º (ou mais, se necessário). Priorize aproveitamento histórico "
        "real quando houver dado suficiente (aproveitamento_pct preenchido). "
        "Para atletas sem esse mínimo (aproveitamento_pct nulo), posicione com "
        "base em critérios gerais e deixe claro no motivo que não há dado real "
        "suficiente. Dê um motivo de uma frase para cada posição. Responda em "
        "JSON: {\"ordem\": [{\"atleta_id\": int, \"motivo\": str}, ...]}."
    )

    try:
        resultado = chamar_ia(instrucao, {"atletas_disponiveis": atletas_contexto}, max_tokens=1000)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    mapa_aproveitamento = {a["atleta_id"]: a["aproveitamento_pct"] for a in atletas_contexto}
    novas = []
    for posicao, item in enumerate(resultado.get("ordem", []), start=1):
        sugestao = PenaltiSugestaoOrdem(
            partida_id=partida_id,
            atleta_id=item["atleta_id"],
            ordem_sugerida=posicao,
            aproveitamento_historico=mapa_aproveitamento.get(item["atleta_id"]),
            motivo=item.get("motivo"),
            criado_em=datetime.now(timezone.utc),
        )
        db.add(sugestao)
        novas.append(sugestao)
    db.commit()
    for item in novas:
        db.refresh(item)
    return novas


@router.patch("/ordem-final", response_model=list[PenaltiSugestaoOut])
def confirmar_ordem_final(partida_id: int, ordens: list[PenaltiOrdemFinal], db: Session = Depends(get_db)):
    """Comissão pode reordenar livremente antes de confirmar a ordem real."""
    for item in ordens:
        sugestao = db.query(PenaltiSugestaoOrdem).filter(
            PenaltiSugestaoOrdem.partida_id == partida_id, PenaltiSugestaoOrdem.atleta_id == item.atleta_id
        ).first()
        if sugestao:
            sugestao.ordem_final = item.ordem_final
    db.commit()
    return db.query(PenaltiSugestaoOrdem).filter(PenaltiSugestaoOrdem.partida_id == partida_id).all()


@router.get("/cobrancas", response_model=list[PenaltiCobrancaOut])
def listar_cobrancas(partida_id: int, db: Session = Depends(get_db)):
    """
    Recarrega o estado real das cobranças já registradas — usado pela tela
    do auxiliar ao entrar/recarregar, pra não perder a numeração da ordem
    em caso de reload no meio da disputa.
    """
    return db.query(PenaltiCobranca).filter(
        PenaltiCobranca.partida_id == partida_id
    ).order_by(PenaltiCobranca.ordem).all()


@router.post("/cobrancas", response_model=PenaltiCobrancaOut, status_code=201)
def registrar_cobranca(partida_id: int, dados: PenaltiCobrancaCreate, db: Session = Depends(get_db)):
    """Registro em tempo real de cada cobrança — não envolve IA, é só log do fato."""
    cobranca = PenaltiCobranca(partida_id=partida_id, criado_em=datetime.now(timezone.utc), **dados.model_dump())
    db.add(cobranca)
    db.commit()
    db.refresh(cobranca)
    return cobranca
