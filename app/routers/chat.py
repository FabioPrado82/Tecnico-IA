from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.core.ai_client import chamar_ia
from app.models.partida import Partida
from app.models.pos_jogo_e_extras import MensagemChatIA
from app.schemas.extras import MensagemChatCreate, MensagemChatOut

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Depends(usuario_atual)])


@router.post("/mensagens", response_model=MensagemChatOut, status_code=201)
def enviar_mensagem(dados: MensagemChatCreate, db: Session = Depends(get_db)):
    """
    Modo 6 — chat livre. Se partida_id vier preenchido, inclui o contexto da
    partida na conversa; caso contrário roda só com a persona base.
    """
    contexto = {"pergunta_do_usuario": dados.mensagem}
    if dados.partida_id:
        partida = db.get(Partida, dados.partida_id)
        if not partida:
            raise HTTPException(status_code=404, detail="Partida não encontrada")
        contexto["contexto_da_partida"] = {
            "placar_nosso": partida.placar_nosso,
            "placar_adversario": partida.placar_adversario,
            "periodo_atual": partida.periodo_atual,
        }

    instrucao = (
        "Responda à pergunta do usuário livremente, mantendo a persona de "
        "auxiliar técnico. Se a pergunta depender de dados de uma partida "
        "específica e o contexto não tiver essa partida vinculada, pergunte a "
        "qual partida ele se refere em vez de assumir. Responda em JSON: "
        "{\"resposta\": str}."
    )

    try:
        resultado = chamar_ia(instrucao, contexto, max_tokens=800)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    mensagem = MensagemChatIA(
        partida_id=dados.partida_id,
        autor=dados.autor,
        mensagem=dados.mensagem,
        resposta=resultado.get("resposta", resultado.get("texto_bruto", "")),
        criado_em=datetime.now(timezone.utc),
    )
    db.add(mensagem)
    db.commit()
    db.refresh(mensagem)
    return mensagem


@router.get("/mensagens", response_model=list[MensagemChatOut])
def listar_mensagens(partida_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(MensagemChatIA)
    if partida_id:
        query = query.filter(MensagemChatIA.partida_id == partida_id)
    return query.order_by(MensagemChatIA.id).all()
