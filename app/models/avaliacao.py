import uuid
from sqlalchemy import Column, Integer, String, SmallInteger, Text, TIMESTAMP, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class AvaliacaoAtleta(Base):
    __tablename__ = "avaliacoes_atleta"

    id = Column(Integer, primary_key=True)
    atleta_id = Column(Integer, ForeignKey("atletas.id"), nullable=False)
    data_avaliacao = Column(Date)
    passe = Column(SmallInteger)
    finalizacao = Column(SmallInteger)
    drible = Column(SmallInteger)
    cabeceio = Column(SmallInteger)
    desarme = Column(SmallInteger)
    cruzamento = Column(SmallInteger)
    controle_bola = Column(SmallInteger)
    visao_jogo = Column(SmallInteger)
    posicionamento = Column(SmallInteger)
    marcacao = Column(SmallInteger)
    lideranca = Column(SmallInteger)
    versatilidade = Column(SmallInteger)
    cobranca_penalti = Column(SmallInteger)
    defesa_penalti = Column(SmallInteger)
    avaliado_por = Column(String(120))
    observacoes = Column(Text)


class SessaoAvaliacao(Base):
    """
    Sessão de avaliação em lote — gera um link único que o técnico usa pra
    avaliar vários atletas de uma vez, sem precisar de login (mesmo padrão
    do link de confirmação de presença do atleta).
    """
    __tablename__ = "sessoes_avaliacao"

    id = Column(Integer, primary_key=True)
    clube_id = Column(Integer, ForeignKey("clubes.id"), nullable=False)
    link_token = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4, unique=True)
    avaliador_nome = Column(String(120))
    status = Column(String(20), nullable=False, default="pendente")
    criado_em = Column(TIMESTAMP(timezone=True))
    concluido_em = Column(TIMESTAMP(timezone=True))
