"""
Modelos de partida e convocação — o núcleo do fluxo pré-jogo.
"""
import uuid
from sqlalchemy import Column, Integer, String, Boolean, SmallInteger, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class Partida(Base):
    __tablename__ = "partidas"

    id = Column(Integer, primary_key=True)
    clube_id = Column(Integer, nullable=False)
    campeonato_id = Column(Integer, nullable=False)
    adversario_id = Column(Integer, nullable=False)
    fase = Column(String(50))
    data_hora = Column(TIMESTAMP(timezone=True), nullable=False)
    horario_chegada_vestiario = Column(TIMESTAMP(timezone=True))
    duracao_tempo_min = Column(SmallInteger, nullable=False, default=45)
    quantidade_tempos = Column(SmallInteger, nullable=False, default=2)
    tem_prorrogacao = Column(Boolean, nullable=False, default=False)
    duracao_prorrogacao_min = Column(SmallInteger, default=15)
    periodo_atual = Column(String(20), nullable=False, default="1_tempo")
    substituicoes_permitidas = Column(SmallInteger, nullable=False, default=5)
    substituicoes_realizadas = Column(SmallInteger, nullable=False, default=0)
    local = Column(String(10))
    local_nome = Column(String(150))
    status = Column(String(20), nullable=False, default="agendada")
    placar_nosso = Column(SmallInteger)
    placar_adversario = Column(SmallInteger)


class Convocacao(Base):
    __tablename__ = "convocacao"
    __table_args__ = (UniqueConstraint("partida_id", "atleta_id"),)

    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    atleta_id = Column(Integer, ForeignKey("atletas.id"), nullable=False)
    disponivel = Column(Boolean, nullable=False, default=True)
    motivo_indisponibilidade = Column(String(120))
    convocado = Column(Boolean, nullable=False, default=False)
    titular = Column(Boolean, nullable=False, default=False)

    link_token = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    link_enviado_em = Column(TIMESTAMP(timezone=True))
    lembrete_enviado_em = Column(TIMESTAMP(timezone=True))
    quantidade_lembretes = Column(SmallInteger, nullable=False, default=0)
    presenca_confirmada = Column(String(10), nullable=False, default="pendente")
    presenca_respondida_em = Column(TIMESTAMP(timezone=True))

    jogos_antes_desta_partida = Column(SmallInteger)

    jogos_previos_confirmado = Column(SmallInteger)
    jogou_em_confirmado = Column(TIMESTAMP(timezone=True))
    nivel_desgaste_confirmado = Column(String(10))
    confirmado_por = Column(String(120))
    confirmado_em = Column(TIMESTAMP(timezone=True))
