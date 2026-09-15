from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SessaoAvaliacaoCreate(BaseModel):
    clube_id: int


class SessaoAvaliacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    clube_id: int
    link_token: str
    status: str
    avaliador_nome: Optional[str] = None


class AtletaParaAvaliar(BaseModel):
    """O que o técnico vê na tela pra cada atleta — nota atual, se já tiver."""
    atleta_id: int
    nome: str
    posicao_principal: str
    ja_avaliado: bool


class SessaoAvaliacaoPublica(BaseModel):
    avaliador_nome: Optional[str] = None
    status: str
    atletas: list[AtletaParaAvaliar]


class NotaAtleta(BaseModel):
    """Todas as notas são opcionais — o técnico pode pular alguma categoria."""
    atleta_id: int
    posicao_principal: Optional[str] = None  # técnico pode definir/ajustar aqui
    passe: Optional[int] = None
    finalizacao: Optional[int] = None
    drible: Optional[int] = None
    cabeceio: Optional[int] = None
    desarme: Optional[int] = None
    cruzamento: Optional[int] = None
    controle_bola: Optional[int] = None
    visao_jogo: Optional[int] = None
    posicionamento: Optional[int] = None
    marcacao: Optional[int] = None
    lideranca: Optional[int] = None
    versatilidade: Optional[int] = None
    cobranca_penalti: Optional[int] = None
    defesa_penalti: Optional[int] = None
    observacoes: Optional[str] = None


class EnviarAvaliacoes(BaseModel):
    avaliador_nome: str
    notas: list[NotaAtleta]
    finalizar: bool = False  # true = marca a sessão como concluída
