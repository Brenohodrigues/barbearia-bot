"""
Registro de mensagens trocadas com o cliente via WhatsApp (auditoria e
histórico, exibido também no painel para o atendente humano).
"""
from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, new_uuid


class MessageDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    barbershop_id: Mapped[str] = mapped_column(
        ForeignKey("barbershops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    direction: Mapped[MessageDirection] = mapped_column(Enum(MessageDirection), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    whatsapp_message_id: Mapped[Optional[str]] = mapped_column(String(120))
    raw_payload: Mapped[Optional[str]] = mapped_column(Text)
