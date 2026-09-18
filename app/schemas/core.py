"""
Schemas Pydantic — o que a API aceita como entrada e devolve como saída.
Separados dos modelos SQLAlchemy de propósito: nem todo campo do banco deve
ser exposto ou aceito diretamente da API.
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AtletaBase(BaseModel):
    nome: str
    apelido: Optional[str] = None
    cpf: Optional[str] = None
    data_nascimento: Optional[date] = None
    posicao_principal: Optional[str] = None
    posicoes_secundarias: list[str] = []
    pe_dominante: Optional[str] = None
    altura_cm: Optional[int] = None
    peso_kg: Optional[float] = None
    foto_url: Optional[str] = None


class AtletaCreate(AtletaBase):
    clube_id: int


class AtletaOut(AtletaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clube_id: int
    ativo: bool
    foto_url: Optional[str] = None
    criado_em: datetime


class PartidaBase(BaseModel):
    campeonato_id: int
    adversario_id: int
    fase: Optional[str] = None
    data_hora: datetime
    horario_chegada_vestiario: Optional[datetime] = None
    duracao_tempo_min: int = 45
    quantidade_tempos: int = 2
    tem_prorrogacao: bool = False
    local: Optional[str] = None
    local_nome: Optional[str] = None


class PartidaCreate(PartidaBase):
    clube_id: int


class PartidaOut(PartidaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clube_id: int
    status: str
    periodo_atual: str
    substituicoes_permitidas: int
    substituicoes_realizadas: int
    placar_nosso: Optional[int] = None
    placar_adversario: Optional[int] = None


class ConvocacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    partida_id: int
    atleta_id: int
    disponivel: bool
    presenca_confirmada: str
    presenca_respondida_em: Optional[datetime] = None
    jogos_antes_desta_partida: Optional[int] = None
    convocado: bool
    titular: bool


class ConfirmacaoPresenca(BaseModel):
    """O que o atleta envia na página pública do link — só isso, nada mais."""
    presenca_confirmada: str  # 'confirmado' ou 'recusado'
    motivo_indisponibilidade: Optional[str] = None
    jogos_antes_desta_partida: Optional[int] = None
