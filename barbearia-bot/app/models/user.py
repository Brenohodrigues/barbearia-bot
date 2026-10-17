"""
Usuário administrativo (login no painel web).

A senha nunca é armazenada em texto puro - somente o hash bcrypt.
"""
from __future__ import annotations

import enum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, new_uuid


class UserRole(str, enum.Enum):
    OWNER = "owner"          # dono da barbearia - acesso total
    MANAGER = "manager"      # gerente - acesso quase total
    ATTENDANT = "attendant"  # atendente - agenda e atendimento humano


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    barbershop_id: Mapped[str] = mapped_column(
        ForeignKey("barbershops.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.OWNER)

    is_active: Mapped[bool] = mapped_column(default=True)
    must_change_password: Mapped[bool] = mapped_column(default=False)

    barbershop: Mapped["Barbershop"] = relationship(back_populates="users")
