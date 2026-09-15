from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ScoutingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    partida_id: int
    tipo_pergunta: str
    pergunta: str
    tipo_resposta: str
    opcoes: Optional[list[str]] = None
    resposta: Optional[str] = None
    respondido_por: Optional[str] = None
    respondido_em: Optional[datetime] = None


class ScoutingResponder(BaseModel):
    resposta: str
    respondido_por: str


class PerguntaDinamicaCreate(BaseModel):
    """Usado pela integração com a IA (Modo 1) para inserir as perguntas geradas."""
    pergunta: str
    tipo_resposta: str = "texto"
    opcoes: Optional[list[str]] = None


class ComentarioAdversarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    adversario_id: int
    partida_id: Optional[int] = None
    origem: str
    comentario: str
    autor: Optional[str] = None
    criado_em: Optional[datetime] = None


class ComentarioAdversarioCreate(BaseModel):
    comentario: str
    autor: str
    partida_id: Optional[int] = None
