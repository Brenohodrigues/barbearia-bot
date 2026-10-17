"""
Barbearia (tenant).

Toda entidade de negócio (clientes, barbeiros, serviços, agendamentos, etc.)
pertence a uma `Barbershop`. Isso prepara o sistema para multi-tenant no
futuro: basta cadastrar uma nova barbearia e todo o restante do modelo já
funciona isolado por `barbershop_id`.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, new_uuid


class Barbershop(TimestampMixin, Base):
    __tablename__ = "barbershops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)

    phone: Mapped[Optional[str]] = mapped_column(String(20))
    address: Mapped[Optional[str]] = mapped_column(String(255))
    instagram: Mapped[Optional[str]] = mapped_column(String(120))
    logo_url: Mapped[Optional[str]] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo")

    # Regra de antecedência mínima (em minutos) para cancelamento/reagendamento
    min_cancel_notice_minutes: Mapped[int] = mapped_column(default=120)

    # Mensagem de boas-vindas customizável usada pelo bot
    welcome_message: Mapped[Optional[str]] = mapped_column(String(1000))

    is_active: Mapped[bool] = mapped_column(default=True)

    users: Mapped[List["User"]] = relationship(back_populates="barbershop")
    barbers: Mapped[List["Barber"]] = relationship(back_populates="barbershop")
    customers: Mapped[List["Customer"]] = relationship(back_populates="barbershop")
    services: Mapped[List["Service"]] = relationship(back_populates="barbershop")
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="barbershop")
    business_hours: Mapped[List["BusinessHours"]] = relationship(back_populates="barbershop")
