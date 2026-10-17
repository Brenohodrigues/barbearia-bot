"""
Chave-valor genérico por barbearia, para configurações adicionais que não
merecem uma coluna própria (ex.: textos de mensagens customizadas,
feature flags). Mantém o schema principal enxuto.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin, new_uuid


class Setting(TimestampMixin, Base):
    __tablename__ = "settings"
    __table_args__ = (
        UniqueConstraint("barbershop_id", "key", name="uq_setting_key_per_shop"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    barbershop_id: Mapped[str] = mapped_column(
        ForeignKey("barbershops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
