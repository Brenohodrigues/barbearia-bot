"""
Bloqueio pontual de horário: feriado da barbearia inteira (barber_id nulo)
ou folga/compromisso de um barbeiro específico.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, new_uuid


class BlockedTime(TimestampMixin, Base):
    __tablename__ = "blocked_times"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    barbershop_id: Mapped[str] = mapped_column(
        ForeignKey("barbershops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    barber_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("barbers.id", ondelete="CASCADE"), nullable=True, index=True
    )

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(255))

    barber: Mapped[Optional["Barber"]] = relationship(back_populates="blocked_times")
