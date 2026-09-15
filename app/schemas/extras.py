from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


# --- Tempo real -------------------------------------------------
class AjusteCronometroIn(BaseModel):
    segundos_anterior: int
    segundos_novo: int
    periodo_anterior: Optional[str] = None
    periodo_novo: str
    motivo: Optional[str] = None
    ajustado_por: str


class AjusteCronometroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    periodo_atual: str


class SubstituicaoAjusteIn(BaseModel):
    delta: int  # +1 ou -1


class EventoCreate(BaseModel):
    time: str = "nosso"
    atleta_id: Optional[int] = None
    atleta_entrou_id: Optional[int] = None
    assistente_id: Optional[int] = None
    jogador_adversario: Optional[str] = None
    minuto: int
    tipo_evento: str
    detalhes: Optional[dict] = None
    registrado_por: Optional[str] = None


class EventoOut(EventoCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    partida_id: int
    criado_em: Optional[datetime] = None


class CicloRespostaIn(BaseModel):
    resposta_staff: dict
    respondido_por: Optional[str] = None


class CicloOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    partida_id: int
    minuto_jogo: int
    origem: str
    evento_gatilho_id: Optional[int] = None
    pergunta_ia: Optional[Any] = None
    resposta_staff: Optional[Any] = None
    sugestao_ia: Optional[str] = None


# --- Pós-jogo -----------------------------------------------------
class RetrospectoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    partida_id: int
    pontos_positivos: Optional[str] = None
    pontos_negativos: Optional[str] = None
    licoes_aprendidas: Optional[str] = None
    status: str


class RetrospectoAprovar(BaseModel):
    revisado_por: str
    pontos_positivos: Optional[str] = None
    pontos_negativos: Optional[str] = None
    licoes_aprendidas: Optional[str] = None


# --- Chat -----------------------------------------------------------
class MensagemChatCreate(BaseModel):
    mensagem: str
    autor: str
    partida_id: Optional[int] = None


class MensagemChatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    partida_id: Optional[int] = None
    autor: Optional[str] = None
    mensagem: str
    resposta: Optional[str] = None


# --- Pênaltis ---------------------------------------------------
class PenaltiSugestaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    atleta_id: int
    ordem_sugerida: int
    aproveitamento_historico: Optional[float] = None
    motivo: Optional[str] = None
    ordem_final: Optional[int] = None


class PenaltiOrdemFinal(BaseModel):
    atleta_id: int
    ordem_final: int


class PenaltiCobrancaCreate(BaseModel):
    lado: str
    atleta_id: Optional[int] = None
    nome_jogador_adversario: Optional[str] = None
    ordem: int
    resultado: str
    lado_chute: Optional[str] = None


class PenaltiCobrancaOut(PenaltiCobrancaCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    partida_id: int


# --- Voz ------------------------------------------------------------
class InterpretarVozIn(BaseModel):
    contexto: str  # 'evento' ou 'resposta_ciclo'
    transcricao_bruta: str
    opcoes_disponiveis: Optional[list[str]] = None  # quando contexto = resposta_ciclo


class TranscricaoVozOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    partida_id: int
    contexto: str
    transcricao_bruta: str
    interpretacao: Optional[Any] = None
    confirmado_pelo_auxiliar: bool
