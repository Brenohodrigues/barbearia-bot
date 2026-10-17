"""
Cliente. O telefone (formato E.164, ex.: 5519999999999) é o identificador
natural vindo do WhatsApp e é único por barbearia.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import ForeignKey, String, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, new_uuid


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("barbershop_id", "phone", name="uq_customer_phone_per_shop"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    barbershop_id: Mapped[str] = mapped_column(
        ForeignKey("barbershops.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[Optional[str]] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    last_visit_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    visits_count: Mapped[int] = mapped_column(default=0)
    is_blocked: Mapped[bool] = mapped_column(default=False)

    # LGPD: consentimento explícito de contato/armazenamento de dados
    consent_given: Mapped[bool] = mapped_column(default=True)

    barbershop: Mapped["Barbershop"] = relationship(back_populates="customers")
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="customer")
    conversation: Mapped[Optional["Conversation"]] = relationship(
        back_populates="customer", uselist=False, cascade="all, delete-orphan"
    )
