"""
Serviço oferecido pela barbearia (ex.: Corte, Barba, Corte + Barba).
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, new_uuid


class Service(TimestampMixin, Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    barbershop_id: Mapped[str] = mapped_column(
        ForeignKey("barbershops.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    barbershop: Mapped["Barbershop"] = relationship(back_populates="services")
    barbers: Mapped[List["Barber"]] = relationship(
        secondary="barber_services", back_populates="services"
    )
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="service")
