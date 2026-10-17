"""
Barbeiro e a tabela de associação barbeiro<->serviço (muitos-para-muitos).
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import ForeignKey, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, new_uuid

barber_services = Table(
    "barber_services",
    Base.metadata,
    Column("barber_id", String(36), ForeignKey("barbers.id", ondelete="CASCADE"), primary_key=True),
    Column("service_id", String(36), ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
)


class Barber(TimestampMixin, Base):
    __tablename__ = "barbers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    barbershop_id: Mapped[str] = mapped_column(
        ForeignKey("barbershops.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    photo_url: Mapped[Optional[str]] = mapped_column(String(255))
    bio: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True)

    barbershop: Mapped["Barbershop"] = relationship(back_populates="barbers")
    services: Mapped[List["Service"]] = relationship(
        secondary=barber_services, back_populates="barbers"
    )
    working_hours: Mapped[List["BarberHours"]] = relationship(
        back_populates="barber", cascade="all, delete-orphan"
    )
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="barber")
    blocked_times: Mapped[List["BlockedTime"]] = relationship(back_populates="barber")
