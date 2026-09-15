from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.core.ai_client import chamar_ia
from app.models.partida import Partida
from app.models.core import Adversario
from app.models.scouting import ScoutingAdversario, ComentarioAdversario
from app.schemas.scouting import (
    ScoutingOut, ScoutingResponder, PerguntaDinamicaCreate,
    ComentarioAdversarioOut, ComentarioAdversarioCreate,
)

router = APIRouter(tags=["scouting"], dependencies=[Depends(usuario_atual)])

# As 11 perguntas fixas fechadas no planejamento — múltipla escolha onde a
# resposta é previsível, texto livre onde precisa de nome/detalhe específico.
PERGUNTAS_FIXAS = [
    ("Qual o esquema mais usado por eles?", "multipla_escolha", ["4-4-2", "4-3-3", "3-5-2", "Outro"]),
    ("Saída de bola é curta ou direta?", "multipla_escolha", ["Curta", "Direta", "Mista"]),
    ("Joga mais pelo lado direito, esquerdo ou pelo centro?", "multipla_escolha", ["Direita", "Esquerda", "Centro", "Equilibrado"]),
    ("Pressiona alto ou recua?", "multipla_escolha", ["Pressiona alto", "Equilibrado", "Recua"]),
    ("É um time que joga duro fisicamente?", "multipla_escolha", ["Leve", "Moderado", "Joga duro"]),
    ("Costuma reclamar de arbitragem?", "multipla_escolha", ["Sim", "Não", "Às vezes"]),
    ("Como se comportam em bola parada?", "multipla_escolha", ["Mais ofensivo", "Mais defensivo", "Equilibrado"]),
    ("Qual a motivação deles nesse jogo?", "multipla_escolha", ["Precisa da vitória", "Já classificado", "Neutro"]),
    ("Tem algum jogador decisivo que precisamos neutralizar?", "texto", None),
    ("Algum jogador suspenso/lesionado que não deve jogar?", "texto", None),
    ("Tem cobrador de falta perigoso?", "texto", None),
]


@router.post("/partidas/{partida_id}/scouting/inicializar", response_model=list[ScoutingOut], status_code=201)
def inicializar_scouting(partida_id: int, db: Session = Depends(get_db)):
    """
    Cria as perguntas fixas para essa partida, se ainda não existirem.
    Chamado quando a comissão abre o formulário de scouting pela primeira vez.
    """
    partida = db.get(Partida, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida não encontrada")

    ja_existe = db.query(ScoutingAdversario).filter(
        ScoutingAdversario.partida_id == partida_id
    ).first()
    if ja_existe:
        return db.query(ScoutingAdversario).filter(ScoutingAdversario.partida_id == partida_id).all()

    novas = []
    for pergunta, tipo_resposta, opcoes in PERGUNTAS_FIXAS:
        item = ScoutingAdversario(
            partida_id=partida_id,
            tipo_pergunta="fixa",
            pergunta=pergunta,
            tipo_resposta=tipo_resposta,
            opcoes=opcoes,
        )
        db.add(item)
        novas.append(item)
    db.commit()
    for item in novas:
        db.refresh(item)
    return novas


@router.get("/partidas/{partida_id}/scouting", response_model=list[ScoutingOut])
def listar_scouting(partida_id: int, db: Session = Depends(get_db)):
    return db.query(ScoutingAdversario).filter(
        ScoutingAdversario.partida_id == partida_id
    ).order_by(ScoutingAdversario.id).all()


@router.post("/partidas/{partida_id}/scouting/gerar-dinamicas", response_model=list[ScoutingOut], status_code=201)
def gerar_perguntas_dinamicas(partida_id: int, db: Session = Depends(get_db)):
    """
    Modo 1 da lógica da IA — gera de 1 a 3 perguntas específicas pra esse
    confronto, considerando fase do campeonato e histórico do adversário.
    Idempotente: se já existirem perguntas dinâmicas pra essa partida, só
    devolve as que já existem, sem gerar de novo.
    """
    partida = db.get(Partida, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida não encontrada")

    ja_existentes = db.query(ScoutingAdversario).filter(
        ScoutingAdversario.partida_id == partida_id,
        ScoutingAdversario.tipo_pergunta == "dinamica",
    ).all()
    if ja_existentes:
        return ja_existentes

    comentarios = db.query(ComentarioAdversario).filter(
        ComentarioAdversario.adversario_id == partida.adversario_id
    ).order_by(ComentarioAdversario.criado_em.desc()).limit(5).all()

    contexto = {
        "fase_do_campeonato": partida.fase,
        "tem_prorrogacao": partida.tem_prorrogacao,
        "comentarios_historicos_sobre_o_adversario": [c.comentario for c in comentarios],
    }
    instrucao = (
        "Gere de 1 a 3 perguntas de múltipla escolha adicionais para o scouting "
        "deste confronto específico, considerando a fase do campeonato e o "
        "histórico já registrado sobre o adversário. Não repita perguntas fixas "
        "padrão (esquema tático, saída de bola, postura defensiva, intensidade "
        "física, arbitragem, bola parada, motivação, jogador decisivo, "
        "suspensão/lesão, cobrador de falta). Se for mata-mata, considere incluir "
        "uma pergunta sobre pênaltis. Responda com uma lista JSON de objetos no "
        "formato {\"pergunta\": str, \"opcoes\": [str, str, str]}."
    )

    try:
        resultado = chamar_ia(instrucao, contexto)
    except RuntimeError as e:
        # Erro de configuração (chave ausente) ou falha da própria API da
        # Claude — 503 porque é um problema temporário/externo, não do cliente.
        raise HTTPException(status_code=503, detail=str(e))
    perguntas_geradas = resultado if isinstance(resultado, list) else resultado.get("perguntas", [])

    novas = []
    for p in perguntas_geradas:
        item = ScoutingAdversario(
            partida_id=partida_id,
            tipo_pergunta="dinamica",
            pergunta=p["pergunta"],
            tipo_resposta="multipla_escolha",
            opcoes=p.get("opcoes"),
        )
        db.add(item)
        novas.append(item)
    db.commit()
    for item in novas:
        db.refresh(item)
    return novas


@router.patch("/scouting/{pergunta_id}/responder", response_model=ScoutingOut)
def responder_pergunta(pergunta_id: int, dados: ScoutingResponder, db: Session = Depends(get_db)):
    item = db.get(ScoutingAdversario, pergunta_id)
    if not item:
        raise HTTPException(status_code=404, detail="Pergunta não encontrada")
    item.resposta = dados.resposta
    item.respondido_por = dados.respondido_por
    item.respondido_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item


@router.get("/adversarios/{adversario_id}/comentarios", response_model=list[ComentarioAdversarioOut])
def listar_comentarios_adversario(adversario_id: int, db: Session = Depends(get_db)):
    """Histórico de comentários sobre esse adversário, acumulado entre confrontos."""
    adversario = db.get(Adversario, adversario_id)
    if not adversario:
        raise HTTPException(status_code=404, detail="Adversário não encontrado")
    return db.query(ComentarioAdversario).filter(
        ComentarioAdversario.adversario_id == adversario_id
    ).order_by(ComentarioAdversario.criado_em.desc()).all()


@router.post("/partidas/{partida_id}/comentarios-adversario", response_model=ComentarioAdversarioOut, status_code=201)
def criar_comentario_adversario(partida_id: int, dados: ComentarioAdversarioCreate, db: Session = Depends(get_db)):
    partida = db.get(Partida, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida não encontrada")

    comentario = ComentarioAdversario(
        adversario_id=partida.adversario_id,
        partida_id=partida_id,
        origem="comissao",
        comentario=dados.comentario,
        autor=dados.autor,
        criado_em=datetime.now(timezone.utc),
    )
    db.add(comentario)
    db.commit()
    db.refresh(comentario)
    return comentario
