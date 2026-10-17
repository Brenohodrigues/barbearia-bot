"""
Horário de funcionamento da barbearia e horário de trabalho de cada
barbeiro. `weekday` segue a convenção Python: 0 = segunda ... 6 = domingo.
"""
from __future__ import annotations

from datetime import time
from typing import Optional

from sqlalchemy import ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, new_uuid


class BusinessHours(TimestampMixin, Base):
    __tablename__ = "business_hours"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    barbershop_id: Mapped[str] = mapped_column(
        ForeignKey("barbershops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weekday: Mapped[int] = mapped_column(nullable=False)  # 0=segunda ... 6=domingo
    is_closed: Mapped[bool] = mapped_column(default=False)
    opens_at: Mapped[Optional[time]] = mapped_column(Time)
    closes_at: Mapped[Optional[time]] = mapped_column(Time)
    break_start: Mapped[Optional[time]] = mapped_column(Time)
    break_end: Mapped[Optional[time]] = mapped_column(Time)

    barbershop: Mapped["Barbershop"] = relationship(back_populates="business_hours")


class BarberHours(TimestampMixin, Base):
    """Disponibilidade individual do barbeiro (opcional - sobrepõe a da barbearia)."""

    __tablename__ = "barber_hours"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    barber_id: Mapped[str] = mapped_column(
        ForeignKey("barbers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weekday: Mapped[int] = mapped_column(nullable=False)
    is_off: Mapped[bool] = mapped_column(default=False)
    starts_at: Mapped[Optional[time]] = mapped_column(Time)
    ends_at: Mapped[Optional[time]] = mapped_column(Time)

    barber: Mapped["Barber"] = relationship(back_populates="working_hours")
