"""
Configuração central da aplicação.
Lê variáveis de ambiente (ou usa defaults de desenvolvimento local).
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/tecnico_ia"
    secret_key: str = "troque-esta-chave-em-producao"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12  # 12h — turno de trabalho da comissão
    anthropic_api_key: str = ""  # obrigatória pra qualquer chamada real à IA
    anthropic_workspace_id: str = ""  # só necessário se a chave não for vinculada a um workspace

    class Config:
        env_file = ".env"


settings = Settings()
