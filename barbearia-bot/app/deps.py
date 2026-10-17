"""
Dependências reutilizáveis do FastAPI: sessão de banco, usuário autenticado
e a barbearia (tenant) do usuário logado.
"""
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.barbershop import Barbershop
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_error

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise credentials_error

    user = db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise credentials_error
    return user


def get_current_barbershop(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Barbershop:
    barbershop = db.get(Barbershop, user.barbershop_id)
    if not barbershop or not barbershop.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Barbearia inativa ou não encontrada.")
    return barbershop
