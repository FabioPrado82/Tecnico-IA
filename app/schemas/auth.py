from pydantic import BaseModel, EmailStr, ConfigDict


class UsuarioCreate(BaseModel):
    clube_id: int
    nome: str
    email: EmailStr
    senha: str


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    clube_id: int
    nome: str
    email: str
    ativo: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
