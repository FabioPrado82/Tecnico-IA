from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY

from app.core.database import Base


class Patrocinador(Base):
    __tablename__ = "patrocinadores"

    id = Column(Integer, primary_key=True)
    clube_id = Column(Integer, ForeignKey("clubes.id"), nullable=False)
    nome = Column(String(120), nullable=False)
    logo_url = Column(String(255))
    ativo = Column(Boolean, nullable=False, default=True)
    criado_em = Column(TIMESTAMP(timezone=True))


class ArteDivulgacao(Base):
    __tablename__ = "artes_divulgacao"

    id = Column(Integer, primary_key=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"), nullable=False)
    tipo = Column(String(10), nullable=False)  # 'pre_jogo' ou 'pos_jogo'
    template = Column(String(50), nullable=False, default="padrao")
    jogadores_destaque = Column(ARRAY(Integer))
    frase_personalizada = Column(String(150))
    patrocinadores_exibidos = Column(ARRAY(Integer))
    arquivo_gerado_url = Column(String(255))
    criado_por = Column(String(120))
    criado_em = Column(TIMESTAMP(timezone=True))
