from sqlalchemy import Column, Integer, String, SmallInteger, Text, TIMESTAMP, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class EventoPartida(Base):
    __tablename__ = "eventos_partida"

    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    time = Column(String(10), nullable=False, default="nosso")
    atleta_id = Column(Integer, ForeignKey("atletas.id"))
    atleta_entrou_id = Column(Integer, ForeignKey("atletas.id"))
    assistente_id = Column(Integer, ForeignKey("atletas.id"))
    jogador_adversario = Column(String(120))
    minuto = Column(SmallInteger, nullable=False)
    tipo_evento = Column(String(30), nullable=False)
    detalhes = Column(JSONB)
    registrado_por = Column(String(120))
    criado_em = Column(TIMESTAMP(timezone=True))


class AjusteCronometro(Base):
    __tablename__ = "ajustes_cronometro"

    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    segundos_anterior = Column(Integer, nullable=False)
    segundos_novo = Column(Integer, nullable=False)
    periodo_anterior = Column(String(20))
    periodo_novo = Column(String(20))
    motivo = Column(String(120))
    ajustado_por = Column(String(120))
    ajustado_em = Column(TIMESTAMP(timezone=True))


class CicloIA(Base):
    __tablename__ = "ciclos_ia"

    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    minuto_jogo = Column(SmallInteger, nullable=False)
    origem = Column(String(10), nullable=False)  # 'ciclo' ou 'gatilho'
    evento_gatilho_id = Column(Integer, ForeignKey("eventos_partida.id"))
    pergunta_ia = Column(JSONB)
    resposta_staff = Column(JSONB)
    sugestao_ia = Column(Text)
    criado_em = Column(TIMESTAMP(timezone=True))
