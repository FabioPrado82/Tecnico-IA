"""
Tempo real — Modos 2 (ciclo regular), 3 (sugestão) e 4 (gatilho).

Importante: isso é a camada REST. O empurrão em tempo real de verdade pro
auxiliar (WebSocket) ainda não está implementado — por enquanto o cliente
precisaria dar polling nesses endpoints. Ver README.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import usuario_atual
from app.core.ai_client import chamar_ia
from app.core.ws_manager import manager
from app.models.partida import Partida
from app.models.tempo_real import EventoPartida, CicloIA, AjusteCronometro
from app.schemas.extras import (
    EventoCreate, EventoOut, CicloRespostaIn, CicloOut,
    AjusteCronometroIn, SubstituicaoAjusteIn,
)

router = APIRouter(tags=["tempo-real"], dependencies=[Depends(usuario_atual)])

EVENTOS_QUE_DISPARAM_GATILHO = {"gol", "cartao_amarelo", "cartao_vermelho"}

# Perguntas de gatilho são templates fixos (Modo 4) — só a sugestão depois é
# gerada pela IA (Modo 3). Chave é (tipo_evento, time).
GATILHOS = {
    ("gol", "nosso"): {
        "tag": "Gatilho: gol marcado",
        "pergunta": "Ajustar postura tática?",
        "opcoes": ["Manter pressão", "Recuar e proteger vantagem", "Sem mudança"],
    },
    ("gol", "adversario"): {
        "tag": "Gatilho: gol sofrido",
        "pergunta": "Qual foi a causa do gol?",
        "opcoes": ["Erro defensivo", "Bola parada", "Contra-ataque"],
    },
    ("cartao_amarelo", "nosso"): {
        "tag": "Gatilho: cartão em jogador nosso",
        "pergunta": "Considera substituição preventiva?",
        "opcoes": ["Sim", "Não", "Aguardar mais um pouco"],
    },
    ("cartao_vermelho", "nosso"): {
        "tag": "Gatilho: expulsão nossa",
        "pergunta": "Como ajustar o esquema com um a menos?",
        "opcoes": ["Recuar uma linha", "Manter postura", "Já decidido"],
    },
    ("cartao_amarelo", "adversario"): {
        "tag": "Gatilho: cartão no adversário",
        "pergunta": "Como aproveitar essa vantagem?",
        "opcoes": ["Pressionar mais", "Manter ritmo atual"],
    },
    ("cartao_vermelho", "adversario"): {
        "tag": "Gatilho: expulsão do adversário",
        "pergunta": "Como aproveitar a superioridade numérica?",
        "opcoes": ["Adiantar linhas", "Manter organização e paciência"],
    },
}


@router.post("/partidas/{partida_id}/eventos", response_model=EventoOut, status_code=201)
def registrar_evento(partida_id: int, dados: EventoCreate, db: Session = Depends(get_db)):
    """
    Registra o evento e, se for gol ou cartão, já cria o ciclo de gatilho
    automaticamente (Modo 4) com a pergunta template correspondente.
    """
    partida = db.get(Partida, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida não encontrada")

    evento = EventoPartida(partida_id=partida_id, criado_em=datetime.now(timezone.utc), **dados.model_dump())
    db.add(evento)
    db.flush()

    if dados.tipo_evento == "substituicao" and partida.substituicoes_realizadas < partida.substituicoes_permitidas:
        partida.substituicoes_realizadas += 1

    if dados.tipo_evento in EVENTOS_QUE_DISPARAM_GATILHO:
        gatilho = GATILHOS.get((dados.tipo_evento, dados.time))
        if gatilho:
            ciclo = CicloIA(
                partida_id=partida_id,
                minuto_jogo=dados.minuto,
                origem="gatilho",
                evento_gatilho_id=evento.id,
                pergunta_ia={"tag": gatilho["tag"], "pergunta": gatilho["pergunta"], "opcoes": gatilho["opcoes"]},
                criado_em=datetime.now(timezone.utc),
            )
            db.add(ciclo)
            db.flush()
            manager.broadcast(partida_id, {
                "tipo": "novo_ciclo",
                "ciclo": {
                    "id": ciclo.id, "origem": "gatilho", "minuto_jogo": ciclo.minuto_jogo,
                    "pergunta_ia": ciclo.pergunta_ia, "evento_gatilho_id": evento.id,
                },
            })

    db.commit()
    db.refresh(evento)
    return evento


@router.post("/partidas/{partida_id}/ciclos/gerar-pergunta", response_model=CicloOut, status_code=201)
def gerar_pergunta_ciclo(partida_id: int, minuto_jogo: int, db: Session = Depends(get_db)):
    """Modo 2 — pergunta de múltipla escolha do ciclo regular (a cada 2-3min)."""
    partida = db.get(Partida, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida não encontrada")

    ultimos_ciclos = db.query(CicloIA).filter(
        CicloIA.partida_id == partida_id
    ).order_by(CicloIA.id.desc()).limit(3).all()

    contexto = {
        "minuto_atual": minuto_jogo,
        "placar_nosso": partida.placar_nosso,
        "placar_adversario": partida.placar_adversario,
        "periodo_atual": partida.periodo_atual,
        "ultimas_perguntas_feitas": [c.pergunta_ia for c in ultimos_ciclos if c.pergunta_ia],
    }
    instrucao = (
        "Gere uma pergunta de múltipla escolha (2-4 opções) sobre o momento atual "
        "do jogo, para o auxiliar responder rapidamente. Varie o foco em relação "
        "às últimas perguntas já feitas nesta partida (controle de jogo, desgaste "
        "físico do time, ameaça do adversário, etc.) — não repita o mesmo tema em "
        "ciclos seguidos. Responda em JSON: {\"pergunta\": str, \"opcoes\": [str, ...]}."
    )

    try:
        resultado = chamar_ia(instrucao, contexto)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    ciclo = CicloIA(
        partida_id=partida_id,
        minuto_jogo=minuto_jogo,
        origem="ciclo",
        pergunta_ia=resultado,
        criado_em=datetime.now(timezone.utc),
    )
    db.add(ciclo)
    db.commit()
    db.refresh(ciclo)
    manager.broadcast(partida_id, {
        "tipo": "novo_ciclo",
        "ciclo": {"id": ciclo.id, "origem": "ciclo", "minuto_jogo": ciclo.minuto_jogo, "pergunta_ia": ciclo.pergunta_ia},
    })
    return ciclo


@router.patch("/ciclos/{ciclo_id}/responder", response_model=CicloOut)
def responder_ciclo(ciclo_id: int, dados: CicloRespostaIn, db: Session = Depends(get_db)):
    """
    Auxiliar responde o ciclo (regular ou gatilho) — e a sugestão (Modo 3) já
    é gerada na hora e volta junto na resposta, sem precisar de nova chamada.
    """
    ciclo = db.get(CicloIA, ciclo_id)
    if not ciclo:
        raise HTTPException(status_code=404, detail="Ciclo não encontrado")

    ciclo.resposta_staff = dados.resposta_staff
    db.flush()

    partida = db.get(Partida, ciclo.partida_id)
    contexto = {
        "minuto_jogo": ciclo.minuto_jogo,
        "placar_nosso": partida.placar_nosso,
        "placar_adversario": partida.placar_adversario,
        "substituicoes_realizadas": partida.substituicoes_realizadas,
        "substituicoes_permitidas": partida.substituicoes_permitidas,
        "pergunta_feita": ciclo.pergunta_ia,
        "resposta_do_auxiliar": dados.resposta_staff,
        "origem": ciclo.origem,
    }
    instrucao = (
        "Com base na resposta do auxiliar e no estado atual da partida, dê uma "
        "sugestão tática objetiva (1-3 frases): ajuste de posicionamento, "
        "substituição, ou alerta disciplinar. Considere as substituições já "
        "usadas e o tempo restante de jogo. Se a resposta não indicar "
        "necessidade de mudança, diga isso claramente em vez de forçar uma "
        "sugestão. Responda em JSON: {\"sugestao\": str}."
    )

    try:
        resultado = chamar_ia(instrucao, contexto, max_tokens=600)
        ciclo.sugestao_ia = resultado.get("sugestao", resultado.get("texto_bruto", ""))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    db.commit()
    db.refresh(ciclo)
    manager.broadcast(ciclo.partida_id, {
        "tipo": "sugestao_pronta",
        "ciclo_id": ciclo.id,
        "sugestao_ia": ciclo.sugestao_ia,
    })
    return ciclo


@router.get("/partidas/{partida_id}/ciclos", response_model=list[CicloOut])
def listar_ciclos(partida_id: int, db: Session = Depends(get_db)):
    return db.query(CicloIA).filter(CicloIA.partida_id == partida_id).order_by(CicloIA.id).all()


@router.patch("/partidas/{partida_id}/cronometro/ajustar")
def ajustar_cronometro(partida_id: int, dados: AjusteCronometroIn, db: Session = Depends(get_db)):
    """
    Cobre o cenário do auxiliar esquecer de iniciar o cronômetro (ou qualquer
    outra correção manual). Sempre registra o ajuste em `ajustes_cronometro`
    pra auditoria — nunca sobrescreve o tempo silenciosamente.
    """
    partida = db.get(Partida, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida não encontrada")

    ajuste = AjusteCronometro(
        partida_id=partida_id,
        segundos_anterior=dados.segundos_anterior,
        segundos_novo=dados.segundos_novo,
        periodo_anterior=dados.periodo_anterior or partida.periodo_atual,
        periodo_novo=dados.periodo_novo,
        motivo=dados.motivo,
        ajustado_por=dados.ajustado_por,
        ajustado_em=datetime.now(timezone.utc),
    )
    db.add(ajuste)
    partida.periodo_atual = dados.periodo_novo
    db.commit()
    return {"id": ajuste.id, "periodo_atual": partida.periodo_atual}


@router.patch("/partidas/{partida_id}/substituicoes")
def ajustar_substituicoes(partida_id: int, dados: SubstituicaoAjusteIn, db: Session = Depends(get_db)):
    """
    Contador editável pelo auxiliar (não só incrementado automaticamente por
    evento) — cobre correção manual de troca registrada fora de hora ou por
    engano, mesma lógica do ajuste de cronômetro.
    """
    partida = db.get(Partida, partida_id)
    if not partida:
        raise HTTPException(status_code=404, detail="Partida não encontrada")

    nova = partida.substituicoes_realizadas + dados.delta
    if nova < 0 or nova > partida.substituicoes_permitidas:
        raise HTTPException(status_code=400, detail="Fora do limite de substituições permitidas")

    partida.substituicoes_realizadas = nova
    db.commit()
    return {
        "substituicoes_realizadas": partida.substituicoes_realizadas,
        "substituicoes_permitidas": partida.substituicoes_permitidas,
    }
