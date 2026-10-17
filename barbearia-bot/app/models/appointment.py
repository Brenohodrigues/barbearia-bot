"""
Agendamento. É a entidade central do sistema: liga cliente, barbeiro e
serviço em uma janela de tempo, e nunca pode conflitar com outro
agendamento do mesmo barbeiro (ver app/services/scheduling.py).
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, new_uuid


class AppointmentStatus(str, enum.Enum):
    PENDING = "pending"          # aguardando confirmação
    CONFIRMED = "confirmed"      # confirmado
    COMPLETED = "completed"      # concluído
    CANCELLED = "cancelled"      # cancelado
    NO_SHOW = "no_show"          # não compareceu


class Appointment(TimestampMixin, Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    barbershop_id: Mapped[str] = mapped_column(
        ForeignKey("barbershops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    barber_id: Mapped[str] = mapped_column(
        ForeignKey("barbers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_id: Mapped[str] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=False, index=True
    )

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(nullable=False)
    price_at_booking: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus), default=AppointmentStatus.PENDING, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500))
    cancelled_reason: Mapped[Optional[str]] = mapped_column(String(255))
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    barbershop: Mapped["Barbershop"] = relationship(back_populates="appointments")
    customer: Mapped["Customer"] = relationship(back_populates="appointments")
    barber: Mapped["Barber"] = relationship(back_populates="appointments")
    service: Mapped["Service"] = relationship(back_populates="appointments")
