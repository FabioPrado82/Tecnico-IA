"""
Conexão com o PostgreSQL via SQLAlchemy.
As tabelas já existem no banco (criadas pelo schema.sql) — os modelos abaixo
mapeiam pra elas, não recriam nada.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency do FastAPI — abre uma sessão por request e sempre fecha depois."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
