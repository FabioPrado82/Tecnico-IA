"""
Modelos das entidades centrais — mapeiam para tabelas já criadas pelo schema.sql.
"""
from sqlalchemy import Column, Integer, String, Boolean, Numeric, SmallInteger, ARRAY, Date, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Clube(Base):
    __tablename__ = "clubes"

    id = Column(Integer, primary_key=True)
    nome = Column(String(120), nullable=False)
    logo_url = Column(String(255))
    cor_primaria = Column(String(7))
    cor_secundaria = Column(String(7))
    limite_patrocinadores = Column(SmallInteger, nullable=False, default=5)
    slogan = Column(String(150))

    atletas = relationship("Atleta", back_populates="clube")


class Atleta(Base):
    __tablename__ = "atletas"

    id = Column(Integer, primary_key=True)
    clube_id = Column(Integer, ForeignKey("clubes.id"), nullable=False)
    nome = Column(String(120), nullable=False)
    apelido = Column(String(60))
    cpf = Column(String(14))
    data_nascimento = Column(Date)
    posicao_principal = Column(String(30))
    posicoes_secundarias = Column(ARRAY(String(30)), default=list)
    pe_dominante = Column(String(10))
    altura_cm = Column(SmallInteger)
    peso_kg = Column(Numeric(5, 2))
    ativo = Column(Boolean, nullable=False, default=True)
    foto_url = Column(Text)  # armazena a foto como base64 (data URI), não como arquivo — Render não persiste disco
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())

    clube = relationship("Clube", back_populates="atletas")


class Campeonato(Base):
    __tablename__ = "campeonatos"

    id = Column(Integer, primary_key=True)
    clube_id = Column(Integer, nullable=False)
    nome = Column(String(120), nullable=False)
    temporada = Column(String(20))
    fase_atual = Column(String(50))
    status = Column(String(20), nullable=False, default="em_andamento")
    posicao_tabela = Column(SmallInteger)
    pontos = Column(SmallInteger)
    jogos_restantes = Column(SmallInteger)


class Adversario(Base):
    __tablename__ = "adversarios"

    id = Column(Integer, primary_key=True)
    nome = Column(String(120), nullable=False, unique=True)
    logo_url = Column(String(255))
