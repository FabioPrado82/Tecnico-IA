from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_senha, verificar_senha, criar_access_token
from app.core.deps import usuario_atual
from app.models.usuario import Usuario
from app.schemas.auth import UsuarioCreate, UsuarioOut, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/usuarios", response_model=UsuarioOut, status_code=201)
def criar_usuario(dados: UsuarioCreate, db: Session = Depends(get_db)):
    """
    Cadastra um membro da comissão (ou auxiliar — mesmo login, acesso completo).
    Em produção isso ficaria restrito a um admin; sem essa restrição por
    enquanto porque ainda não existe hierarquia de papéis definida.
    """
    ja_existe = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if ja_existe:
        raise HTTPException(status_code=400, detail="Já existe um usuário com esse e-mail")

    usuario = Usuario(
        clube_id=dados.clube_id,
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
        criado_em=datetime.now(timezone.utc),
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2PasswordRequestForm espera 'username' — usamos o e-mail nesse campo."""
    usuario = db.query(Usuario).filter(Usuario.email == form.username).first()
    if not usuario or not verificar_senha(form.password, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Usuário desativado")

    token = criar_access_token(usuario.id, usuario.clube_id)
    return TokenOut(access_token=token)


@router.get("/me", response_model=UsuarioOut)
def meus_dados(usuario: Usuario = Depends(usuario_atual)):
    return usuario
