from sqlalchemy import Column, Integer, String, SmallInteger, Numeric, Text, TIMESTAMP, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class RetrospectoPartida(Base):
    __tablename__ = "retrospecto_partida"

    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False, unique=True)
    pontos_positivos = Column(Text)
    pontos_negativos = Column(Text)
    licoes_aprendidas = Column(Text)
    status = Column(String(20), nullable=False, default="rascunho_ia")
    revisado_por = Column(String(120))
    revisado_em = Column(TIMESTAMP(timezone=True))
    gerado_em = Column(TIMESTAMP(timezone=True))


class MensagemChatIA(Base):
    __tablename__ = "mensagens_chat_ia"

    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"))
    autor = Column(String(120))
    mensagem = Column(Text, nullable=False)
    resposta = Column(Text)
    criado_em = Column(TIMESTAMP(timezone=True))


class PenaltiCobranca(Base):
    __tablename__ = "penaltis_cobranca"

    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    lado = Column(String(10), nullable=False)  # 'nosso' ou 'adversario'
    atleta_id = Column(Integer, ForeignKey("atletas.id"))
    nome_jogador_adversario = Column(String(120))
    ordem = Column(SmallInteger, nullable=False)
    resultado = Column(String(15), nullable=False)  # gol / perdido / defendido
    lado_chute = Column(String(10))
    criado_em = Column(TIMESTAMP(timezone=True))


class PenaltiSugestaoOrdem(Base):
    __tablename__ = "penaltis_sugestao_ordem"

    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    atleta_id = Column(Integer, ForeignKey("atletas.id"), nullable=False)
    ordem_sugerida = Column(SmallInteger, nullable=False)
    aproveitamento_historico = Column(Numeric(5, 2))
    motivo = Column(Text)
    ordem_final = Column(SmallInteger)
    criado_em = Column(TIMESTAMP(timezone=True))


class TranscricaoVoz(Base):
    __tablename__ = "transcricoes_voz"

    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    contexto = Column(String(20), nullable=False)  # 'evento' ou 'resposta_ciclo'
    transcricao_bruta = Column(Text, nullable=False)
    interpretacao = Column(JSONB)
    confirmado_pelo_auxiliar = Column(Boolean, nullable=False, default=False)
    criado_em = Column(TIMESTAMP(timezone=True))
