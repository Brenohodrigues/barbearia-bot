"""
Conversa/estado do bot para um cliente.

Guarda o estado atual da máquina de estados (ver app/services/conversation_engine.py)
e um "rascunho" (JSON) com as escolhas feitas até o momento (serviço, barbeiro,
data, horário) antes de virarem um Appointment de verdade.
"""
from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import JSON, Enum, ForeignKey, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, new_uuid


class ConversationState(str, enum.Enum):
    START = "start"
    MENU = "menu"
    CHOOSING_SERVICE = "choosing_service"
    CHOOSING_BARBER = "choosing_barber"
    CHOOSING_DATE = "choosing_date"
    CHOOSING_TIME = "choosing_time"
    CONFIRMING = "confirming"
    VIEWING_APPOINTMENTS = "viewing_appointments"
    RESCHEDULING_PICK = "rescheduling_pick"
    RESCHEDULING_DATE = "rescheduling_date"
    RESCHEDULING_TIME = "rescheduling_time"
    CANCELLING_PICK = "cancelling_pick"
    HUMAN_HANDOFF = "human_handoff"


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    barbershop_id: Mapped[str] = mapped_column(
        ForeignKey("barbershops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    state: Mapped[ConversationState] = mapped_column(
        Enum(ConversationState), default=ConversationState.START
    )
    draft: Mapped[dict] = mapped_column(JSON, default=dict)
    is_human_handled: Mapped[bool] = mapped_column(Boolean, default=False)

    customer: Mapped["Customer"] = relationship(back_populates="conversation")
