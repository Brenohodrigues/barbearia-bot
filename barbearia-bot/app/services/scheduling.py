"""
Regras de negócio da agenda: cálculo de disponibilidade e detecção de
conflitos de horário. Esta é a única parte do sistema autorizada a decidir
se um horário está livre - nem o bot nem uma futura IA podem inventar
disponibilidade sem passar por aqui (ver seção 22 do briefing original).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.barber import Barber
from app.models.blocked_time import BlockedTime
from app.models.business_hours import BarberHours, BusinessHours
from app.models.service import Service

ACTIVE_STATUSES = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)

# Granularidade dos slots oferecidos ao cliente (minutos)
SLOT_STEP_MINUTES = 15


class SchedulingError(Exception):
    """Erro de regra de negócio da agenda (ex.: conflito de horário)."""


def _tz(barbershop_timezone: Optional[str] = None) -> ZoneInfo:
    return ZoneInfo(barbershop_timezone or settings.DEFAULT_TIMEZONE)


def get_business_hours_for_day(db: Session, barbershop_id: str, day: date) -> Optional[BusinessHours]:
    weekday = day.weekday()
    return (
        db.query(BusinessHours)
        .filter(BusinessHours.barbershop_id == barbershop_id, BusinessHours.weekday == weekday)
        .first()
    )


def get_barber_hours_for_day(db: Session, barber_id: str, day: date) -> Optional[BarberHours]:
    weekday = day.weekday()
    return (
        db.query(BarberHours)
        .filter(BarberHours.barber_id == barber_id, BarberHours.weekday == weekday)
        .first()
    )


def _effective_window(db: Session, barbershop_id: str, barber_id: str, day: date):
    """Retorna (abre, fecha) considerando primeiro o horário do barbeiro,
    e caindo para o horário geral da barbearia quando o barbeiro não tem
    um horário próprio cadastrado para o dia."""
    barber_hours = get_barber_hours_for_day(db, barber_id, day)
    if barber_hours is not None:
        if barber_hours.is_off or not barber_hours.starts_at or not barber_hours.ends_at:
            return None
        return barber_hours.starts_at, barber_hours.ends_at

    shop_hours = get_business_hours_for_day(db, barbershop_id, day)
    if shop_hours is None or shop_hours.is_closed or not shop_hours.opens_at or not shop_hours.closes_at:
        return None
    return shop_hours.opens_at, shop_hours.closes_at


def _is_blocked(db: Session, barbershop_id: str, barber_id: str, start: datetime, end: datetime) -> bool:
    q = db.query(BlockedTime).filter(
        BlockedTime.barbershop_id == barbershop_id,
        or_(BlockedTime.barber_id == barber_id, BlockedTime.barber_id.is_(None)),
        BlockedTime.starts_at < end,
        BlockedTime.ends_at > start,
    )
    return db.query(q.exists()).scalar()


def has_conflict(
    db: Session,
    barber_id: str,
    start: datetime,
    end: datetime,
    ignore_appointment_id: Optional[str] = None,
) -> bool:
    """Verifica se o barbeiro já possui um agendamento ativo que se sobrepõe
    ao intervalo [start, end)."""
    query = db.query(Appointment).filter(
        Appointment.barber_id == barber_id,
        Appointment.status.in_(ACTIVE_STATUSES),
        Appointment.starts_at < end,
        Appointment.ends_at > start,
    )
    if ignore_appointment_id:
        query = query.filter(Appointment.id != ignore_appointment_id)
    return db.query(query.exists()).scalar()


def list_available_slots(
    db: Session,
    barbershop_id: str,
    barber: Barber,
    service: Service,
    day: date,
    barbershop_timezone: Optional[str] = None,
) -> List[time]:
    """Lista horários de início disponíveis para um barbeiro+serviço em um dia."""
    window = _effective_window(db, barbershop_id, barber.id, day)
    if window is None:
        return []
    opens_at, closes_at = window

    tz = _tz(barbershop_timezone)
    duration = timedelta(minutes=service.duration_minutes)
    cursor = datetime.combine(day, opens_at, tzinfo=tz)
    day_end = datetime.combine(day, closes_at, tzinfo=tz)

    now = datetime.now(tz)
    slots: List[time] = []
    step = timedelta(minutes=SLOT_STEP_MINUTES)

    while cursor + duration <= day_end:
        slot_end = cursor + duration
        if cursor > now and not _is_blocked(db, barbershop_id, barber.id, cursor, slot_end):
            if not has_conflict(db, barber.id, cursor, slot_end):
                slots.append(cursor.timetz().replace(tzinfo=None))
        cursor += step

    return slots


def validate_new_appointment(
    db: Session,
    barbershop_id: str,
    barber: Barber,
    service: Service,
    starts_at: datetime,
    ignore_appointment_id: Optional[str] = None,
) -> datetime:
    """Valida um horário proposto e retorna o `ends_at` calculado.
    Lança SchedulingError com uma mensagem amigável se algo estiver errado."""
    if starts_at.tzinfo is None:
        raise SchedulingError("Data/hora deve conter fuso horário.")

    day = starts_at.date()
    window = _effective_window(db, barbershop_id, barber.id, day)
    if window is None:
        raise SchedulingError("O barbeiro não atende neste dia.")
    opens_at, closes_at = window

    ends_at = starts_at + timedelta(minutes=service.duration_minutes)
    day_start = datetime.combine(day, opens_at, tzinfo=starts_at.tzinfo)
    day_end = datetime.combine(day, closes_at, tzinfo=starts_at.tzinfo)

    if starts_at < day_start or ends_at > day_end:
        raise SchedulingError("Horário fora do funcionamento do barbeiro.")

    if starts_at < datetime.now(starts_at.tzinfo):
        raise SchedulingError("Não é possível agendar em um horário no passado.")

    if _is_blocked(db, barbershop_id, barber.id, starts_at, ends_at):
        raise SchedulingError("Este horário está bloqueado.")

    if has_conflict(db, barber.id, starts_at, ends_at, ignore_appointment_id):
        raise SchedulingError("Este horário já está ocupado para este barbeiro.")

    return ends_at


def can_cancel(barbershop_min_notice_minutes: int, starts_at: datetime) -> bool:
    tz = starts_at.tzinfo or _tz()
    now = datetime.now(tz)
    return (starts_at - now) >= timedelta(minutes=barbershop_min_notice_minutes)
