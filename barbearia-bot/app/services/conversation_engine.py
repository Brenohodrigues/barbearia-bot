"""
Motor de conversação do bot (máquina de estados).

Cada mensagem recebida do cliente é processada aqui. O estado atual da
conversa fica salvo em `Conversation.state` e as escolhas parciais (serviço,
barbeiro, data, horário) em `Conversation.draft` (JSON), até virarem um
`Appointment` de verdade.

Importante (seção 22 do briefing): nenhuma informação crítica (preço,
horário, serviço, barbeiro) é inventada aqui. Tudo vem do banco de dados,
através de `app.services.scheduling` e das tabelas `Service`/`Barber`.
Este módulo também é o ponto de extensão natural para, no futuro, uma IA
apenas interpretar a *intenção* do texto livre do cliente - a decisão sobre
disponibilidade real continua sempre em `scheduling.py`.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.barber import Barber
from app.models.barbershop import Barbershop
from app.models.conversation import Conversation, ConversationState
from app.models.customer import Customer
from app.models.message import Message, MessageDirection
from app.models.service import Service
from app.core.logging import logger
from app.services import scheduling
from app.services.whatsapp_client import WhatsAppNotConfiguredError, whatsapp_client

HUMAN_REQUEST_KEYWORDS = {"atendente", "humano", "falar com atendente", "5"}
CANCEL_FLOW_KEYWORDS = {"cancelar", "sair", "menu", "0"}


def _tz(barbershop: Barbershop) -> ZoneInfo:
    return ZoneInfo(barbershop.timezone or settings.DEFAULT_TIMEZONE)


def get_or_create_customer(db: Session, barbershop: Barbershop, phone: str, name: Optional[str]) -> Customer:
    customer = (
        db.query(Customer)
        .filter(Customer.barbershop_id == barbershop.id, Customer.phone == phone)
        .first()
    )
    if customer:
        if name and not customer.name:
            customer.name = name
        return customer
    customer = Customer(barbershop_id=barbershop.id, phone=phone, name=name)
    db.add(customer)
    db.flush()
    return customer


def get_or_create_conversation(db: Session, barbershop: Barbershop, customer: Customer) -> Conversation:
    conv = db.query(Conversation).filter(Conversation.customer_id == customer.id).first()
    if conv:
        return conv
    conv = Conversation(barbershop_id=barbershop.id, customer_id=customer.id,
                         state=ConversationState.START, draft={})
    db.add(conv)
    db.flush()
    return conv


def log_message(db: Session, barbershop: Barbershop, customer: Customer,
                 direction: MessageDirection, content: str, wa_id: Optional[str] = None):
    db.add(Message(barbershop_id=barbershop.id, customer_id=customer.id,
                    direction=direction, content=content, whatsapp_message_id=wa_id))


async def _reply(db: Session, barbershop: Barbershop, customer: Customer, text: str):
    try:
        await whatsapp_client.send_text(customer.phone, text)
    except WhatsAppNotConfiguredError:
        # Permite testar todo o fluxo de conversa (e ver o resultado no painel/
        # logs) mesmo antes de preencher as credenciais do WhatsApp no .env.
        logger.warning(
            "WhatsApp não configurado - mensagem NÃO enviada de verdade (apenas registrada): %s",
            text.replace("\n", " ")[:80],
        )
    log_message(db, barbershop, customer, MessageDirection.OUTBOUND, text)


def _money(value) -> str:
    return f"R$ {Decimal(value):.2f}".replace(".", ",")


def _welcome_menu(barbershop: Barbershop) -> str:
    base = barbershop.welcome_message or f"Olá! 👋 Seja bem-vindo(a) à {barbershop.name}."
    return (
        f"{base}\n\nComo posso ajudar?\n\n"
        "1️⃣ Agendar horário\n"
        "2️⃣ Ver serviços e preços\n"
        "3️⃣ Consultar meu agendamento\n"
        "4️⃣ Endereço e horário de funcionamento\n"
        "5️⃣ Falar com atendente"
    )


def _active_services(db: Session, barbershop_id: str):
    return (
        db.query(Service)
        .filter(Service.barbershop_id == barbershop_id, Service.is_active.is_(True))
        .order_by(Service.name)
        .all()
    )


def _active_barbers_for_service(db: Session, barbershop_id: str, service: Service):
    return [b for b in service.barbers if b.is_active]


async def handle_incoming_message(
    db: Session,
    barbershop: Barbershop,
    from_phone: str,
    text: str,
    profile_name: Optional[str] = None,
    button_id: Optional[str] = None,
) -> None:
    """Ponto de entrada único chamado pelo webhook para cada mensagem recebida."""
    text_norm = (text or "").strip()
    lowered = text_norm.lower()

    customer = get_or_create_customer(db, barbershop, from_phone, profile_name)
    conversation = get_or_create_conversation(db, barbershop, customer)
    log_message(db, barbershop, customer, MessageDirection.INBOUND, text_norm)

    # Atendimento humano ativo: bot não responde, apenas registra
    if conversation.is_human_handled:
        db.commit()
        return

    choice = button_id or lowered

    if choice in HUMAN_REQUEST_KEYWORDS:
        conversation.is_human_handled = True
        conversation.state = ConversationState.HUMAN_HANDOFF
        db.commit()
        await _reply(
            db, barbershop, customer,
            "Ok! Um atendente humano vai continuar sua conversa por aqui em breve. 🙋"
        )
        return

    if choice in CANCEL_FLOW_KEYWORDS and conversation.state != ConversationState.START:
        conversation.state = ConversationState.MENU
        conversation.draft = {}
        db.commit()
        await _reply(db, barbershop, customer, _welcome_menu(barbershop))
        return

    handler = _STATE_HANDLERS.get(conversation.state, _handle_start)
    await handler(db, barbershop, customer, conversation, choice, text_norm)
    db.commit()


# --------------------------------------------------------------------- #
# Handlers por estado
# --------------------------------------------------------------------- #

async def _handle_start(db, barbershop, customer, conversation, choice, raw_text):
    conversation.state = ConversationState.MENU
    await _reply(db, barbershop, customer, _welcome_menu(barbershop))


async def _handle_menu(db, barbershop, customer, conversation, choice, raw_text):
    if choice in ("1", "agendar", "agendar horário"):
        services = _active_services(db, barbershop.id)
        if not services:
            await _reply(db, barbershop, customer,
                         "No momento não há serviços cadastrados. Fale com a barbearia diretamente.")
            return
        lines = [f"{i+1}️⃣ {s.name} - {_money(s.price)} ({s.duration_minutes}min)" for i, s in enumerate(services)]
        conversation.draft = {"service_ids": [s.id for s in services]}
        conversation.state = ConversationState.CHOOSING_SERVICE
        await _reply(db, barbershop, customer,
                     "Qual serviço você deseja?\n\n" + "\n".join(lines))

    elif choice in ("2", "ver serviços e preços", "serviços", "precos", "preços"):
        services = _active_services(db, barbershop.id)
        if not services:
            await _reply(db, barbershop, customer, "No momento não há serviços cadastrados.")
            return
        lines = [f"✂️ {s.name} - {_money(s.price)} ({s.duration_minutes}min)" for s in services]
        await _reply(db, barbershop, customer, "📋 Nossos serviços:\n\n" + "\n".join(lines))
        await _reply(db, barbershop, customer, _welcome_menu(barbershop))

    elif choice in ("3", "consultar meu agendamento", "meus agendamentos"):
        await _show_upcoming_appointments(db, barbershop, customer, conversation)

    elif choice in ("4", "endereço e horário de funcionamento", "endereço", "horario"):
        addr = barbershop.address or "Endereço não configurado no painel."
        await _reply(
            db, barbershop, customer,
            f"📍 {barbershop.name}\n{addr}\n📞 {barbershop.phone or '-'}\n\n"
            "Para ver os horários de funcionamento detalhados, digite 1 para agendar "
            "e consulte as datas disponíveis."
        )
        await _reply(db, barbershop, customer, _welcome_menu(barbershop))

    else:
        await _reply(db, barbershop, customer,
                     "Não entendi 🤔. Escolha uma das opções abaixo:\n\n" + _welcome_menu(barbershop))


async def _handle_choosing_service(db, barbershop, customer, conversation, choice, raw_text):
    service_ids = conversation.draft.get("service_ids", [])
    idx = _parse_index(choice)
    if idx is None or idx >= len(service_ids):
        await _reply(db, barbershop, customer, "Escolha um número válido da lista de serviços, ou digite 'menu'.")
        return

    service = db.get(Service, service_ids[idx])
    barbers = _active_barbers_for_service(db, barbershop.id, service)
    if not barbers:
        await _reply(db, barbershop, customer,
                     "Nenhum barbeiro disponível para este serviço no momento. Digite 'menu' para voltar.")
        return

    conversation.draft = {**conversation.draft, "service_id": service.id,
                           "barber_ids": [b.id for b in barbers]}
    conversation.state = ConversationState.CHOOSING_BARBER

    lines = [f"{i+1}️⃣ {b.name}" for i, b in enumerate(barbers)]
    lines.append(f"{len(barbers)+1}️⃣ Qualquer barbeiro")
    await _reply(db, barbershop, customer, "Com qual barbeiro?\n\n" + "\n".join(lines))


async def _handle_choosing_barber(db, barbershop, customer, conversation, choice, raw_text):
    barber_ids = conversation.draft.get("barber_ids", [])
    idx = _parse_index(choice)
    if idx is None or idx > len(barber_ids):
        await _reply(db, barbershop, customer, "Escolha um número válido, ou digite 'menu'.")
        return

    any_barber = idx == len(barber_ids)
    conversation.draft = {**conversation.draft,
                           "barber_id": None if any_barber else barber_ids[idx]}
    conversation.state = ConversationState.CHOOSING_DATE

    await _reply(
        db, barbershop, customer,
        "Para qual data? Envie no formato DD/MM (ex.: 20/09) ou digite 'hoje' / 'amanhã'."
    )


async def _handle_choosing_date(db, barbershop, customer, conversation, choice, raw_text):
    tz = _tz(barbershop)
    day = _parse_date(raw_text, tz)
    if day is None:
        await _reply(db, barbershop, customer,
                     "Não entendi a data. Envie no formato DD/MM (ex.: 20/09) ou 'hoje'/'amanhã'.")
        return

    service = db.get(Service, conversation.draft["service_id"])
    barber_id = conversation.draft.get("barber_id")
    barber_ids = conversation.draft.get("barber_ids", [])

    candidates = [db.get(Barber, barber_id)] if barber_id else [db.get(Barber, bid) for bid in barber_ids]

    options = []
    for barber in candidates:
        slots = scheduling.list_available_slots(db, barbershop.id, barber, service, day, barbershop.timezone)
        for slot in slots[:6]:
            options.append((barber.id, barber.name, slot))

    if not options:
        await _reply(db, barbershop, customer,
                     "Não há horários disponíveis nessa data 😕. Tente outra data ou digite 'menu'.")
        return

    conversation.draft = {**conversation.draft, "date": day.isoformat(),
                           "options": [
                               {"barber_id": o[0], "barber_name": o[1], "time": o[2].strftime("%H:%M")}
                               for o in options
                           ]}
    conversation.state = ConversationState.CHOOSING_TIME

    lines = [f"{i+1}️⃣ {o[2].strftime('%H:%M')} - {o[1]}" for i, o in enumerate(options)]
    await _reply(db, barbershop, customer, "Horários disponíveis:\n\n" + "\n".join(lines))


async def _handle_choosing_time(db, barbershop, customer, conversation, choice, raw_text):
    options = conversation.draft.get("options", [])
    idx = _parse_index(choice)
    if idx is None or idx >= len(options):
        await _reply(db, barbershop, customer, "Escolha um número válido da lista de horários, ou digite 'menu'.")
        return

    picked = options[idx]
    conversation.draft = {**conversation.draft, "picked_barber_id": picked["barber_id"],
                           "picked_time": picked["time"]}
    conversation.state = ConversationState.CONFIRMING

    service = db.get(Service, conversation.draft["service_id"])
    day = date.fromisoformat(conversation.draft["date"])
    summary = (
        "📋 RESUMO DO AGENDAMENTO\n\n"
        f"✂️ Serviço: {service.name}\n"
        f"👤 Barbeiro: {picked['barber_name']}\n"
        f"📅 Data: {day.strftime('%d/%m/%Y')}\n"
        f"🕐 Horário: {picked['time']}\n"
        f"💰 Valor: {_money(service.price)}\n\n"
        "1️⃣ Confirmar\n2️⃣ Alterar\n3️⃣ Cancelar"
    )
    await _reply(db, barbershop, customer, summary)


async def _handle_confirming(db, barbershop, customer, conversation, choice, raw_text):
    if choice in ("1", "confirmar"):
        try:
            appointment = _create_appointment_from_draft(db, barbershop, customer, conversation)
        except scheduling.SchedulingError as exc:
            conversation.state = ConversationState.MENU
            conversation.draft = {}
            await _reply(db, barbershop, customer,
                         f"⚠️ {exc}. Vamos recomeçar.\n\n" + _welcome_menu(barbershop))
            return

        conversation.state = ConversationState.MENU
        conversation.draft = {}
        await _reply(
            db, barbershop, customer,
            f"✅ Agendamento confirmado! Te esperamos em {appointment.starts_at.strftime('%d/%m/%Y às %H:%M')}. "
            "Até lá! 💈"
        )
    elif choice in ("2", "alterar"):
        conversation.state = ConversationState.CHOOSING_SERVICE
        services = _active_services(db, barbershop.id)
        conversation.draft = {"service_ids": [s.id for s in services]}
        lines = [f"{i+1}️⃣ {s.name} - {_money(s.price)} ({s.duration_minutes}min)" for i, s in enumerate(services)]
        await _reply(db, barbershop, customer, "Sem problemas! Qual serviço você deseja?\n\n" + "\n".join(lines))
    elif choice in ("3", "cancelar"):
        conversation.state = ConversationState.MENU
        conversation.draft = {}
        await _reply(db, barbershop, customer, "Agendamento não realizado. " + _welcome_menu(barbershop))
    else:
        await _reply(db, barbershop, customer, "Escolha 1 para confirmar, 2 para alterar ou 3 para cancelar.")


async def _handle_viewing_appointments(db, barbershop, customer, conversation, choice, raw_text):
    # Qualquer mensagem aqui volta pro menu (esta tela é só informativa)
    conversation.state = ConversationState.MENU
    await _reply(db, barbershop, customer, _welcome_menu(barbershop))


_STATE_HANDLERS = {
    ConversationState.START: _handle_start,
    ConversationState.MENU: _handle_menu,
    ConversationState.CHOOSING_SERVICE: _handle_choosing_service,
    ConversationState.CHOOSING_BARBER: _handle_choosing_barber,
    ConversationState.CHOOSING_DATE: _handle_choosing_date,
    ConversationState.CHOOSING_TIME: _handle_choosing_time,
    ConversationState.CONFIRMING: _handle_confirming,
    ConversationState.VIEWING_APPOINTMENTS: _handle_viewing_appointments,
}


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #

def _parse_index(choice: str) -> Optional[int]:
    try:
        return int(choice.strip()) - 1
    except (ValueError, AttributeError):
        return None


def _parse_date(raw_text: str, tz: ZoneInfo) -> Optional[date]:
    text = raw_text.strip().lower()
    today = datetime.now(tz).date()
    if text in ("hoje",):
        return today
    if text in ("amanhã", "amanha"):
        return today + timedelta(days=1)
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d/%m"):
        try:
            parsed = datetime.strptime(text, fmt)
            year = parsed.year if parsed.year != 1900 else today.year
            candidate = date(year, parsed.month, parsed.day)
            if candidate < today:
                candidate = date(year + 1, parsed.month, parsed.day)
            return candidate
        except ValueError:
            continue
    return None


async def _show_upcoming_appointments(db: Session, barbershop: Barbershop, customer: Customer,
                                       conversation: Conversation):
    tz = _tz(barbershop)
    now = datetime.now(tz)
    upcoming = (
        db.query(Appointment)
        .filter(
            Appointment.customer_id == customer.id,
            Appointment.status.in_((AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)),
            Appointment.starts_at >= now,
        )
        .order_by(Appointment.starts_at)
        .all()
    )
    conversation.state = ConversationState.VIEWING_APPOINTMENTS

    if not upcoming:
        await _reply(db, barbershop, customer,
                     "Você não tem agendamentos futuros. Digite 1 para agendar um horário.")
        return

    lines = []
    for appt in upcoming:
        lines.append(
            f"📅 {appt.starts_at.strftime('%d/%m/%Y %H:%M')} - {appt.service.name} com {appt.barber.name}"
        )
    await _reply(db, barbershop, customer, "🗓️ Seus próximos agendamentos:\n\n" + "\n".join(lines) +
                 "\n\nPara cancelar ou reagendar, entre em contato com a barbearia ou use o painel de "
                 "autoatendimento (em breve por aqui).")


def _create_appointment_from_draft(db: Session, barbershop: Barbershop, customer: Customer,
                                    conversation: Conversation) -> Appointment:
    draft = conversation.draft
    tz = _tz(barbershop)
    service = db.get(Service, draft["service_id"])
    barber = db.get(Barber, draft["picked_barber_id"])
    day = date.fromisoformat(draft["date"])
    hour, minute = map(int, draft["picked_time"].split(":"))
    starts_at = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)

    ends_at = scheduling.validate_new_appointment(db, barbershop.id, barber, service, starts_at)

    appointment = Appointment(
        barbershop_id=barbershop.id,
        customer_id=customer.id,
        barber_id=barber.id,
        service_id=service.id,
        starts_at=starts_at,
        ends_at=ends_at,
        duration_minutes=service.duration_minutes,
        price_at_booking=service.price,
        status=AppointmentStatus.CONFIRMED,
    )
    db.add(appointment)
    customer.visits_count = (customer.visits_count or 0) + 1
    customer.last_visit_at = starts_at
    db.flush()
    return appointment
