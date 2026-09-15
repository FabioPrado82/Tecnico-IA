from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY

from app.core.database import Base


class ScoutingAdversario(Base):
    __tablename__ = "scouting_adversario"

    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    tipo_pergunta = Column(String(10), nullable=False)  # 'fixa' ou 'dinamica'
    pergunta = Column(Text, nullable=False)
    tipo_resposta = Column(String(20), nullable=False, default="texto")
    opcoes = Column(ARRAY(String(60)))
    resposta = Column(Text)
    respondido_por = Column(String(120))
    respondido_em = Column(TIMESTAMP(timezone=True))


class ComentarioAdversario(Base):
    __tablename__ = "comentarios_adversario"

    id = Column(Integer, primary_key=True)
    adversario_id = Column(Integer, ForeignKey("adversarios.id"), nullable=False)
    partida_id = Column(Integer, ForeignKey("partidas.id"))
    origem = Column(String(15), nullable=False, default="comissao")  # 'comissao' ou 'ia_pos_jogo'
    comentario = Column(Text, nullable=False)
    autor = Column(String(120))
    criado_em = Column(TIMESTAMP(timezone=True))
