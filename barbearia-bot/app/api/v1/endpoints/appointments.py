from datetime import date as date_cls, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.deps import get_current_barbershop, get_current_user, get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.barber import Barber
from app.models.barbershop import Barbershop
from app.models.service import Service
from app.models.user import User
from app.schemas.appointment import AppointmentCreate, AppointmentOut, AppointmentUpdate, AvailabilitySlot
from app.services import scheduling

router = APIRouter()


@router.get("", response_model=list[AppointmentOut])
def list_appointments(
    date_from: date_cls | None = None,
    date_to: date_cls | None = None,
    barber_id: str | None = None,
    status_filter: AppointmentStatus | None = Query(None, alias="status"),
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Appointment).filter(Appointment.barbershop_id == barbershop.id)
    if date_from:
        query = query.filter(Appointment.starts_at >= datetime.combine(date_from, datetime.min.time(),
                                                                         tzinfo=ZoneInfo(barbershop.timezone)))
    if date_to:
        query = query.filter(Appointment.starts_at <= datetime.combine(date_to, datetime.max.time(),
                                                                         tzinfo=ZoneInfo(barbershop.timezone)))
    if barber_id:
        query = query.filter(Appointment.barber_id == barber_id)
    if status_filter:
        query = query.filter(Appointment.status == status_filter)
    return query.order_by(Appointment.starts_at).all()


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    barber = db.query(Barber).filter(Barber.id == payload.barber_id,
                                      Barber.barbershop_id == barbershop.id).first()
    service = db.query(Service).filter(Service.id == payload.service_id,
                                        Service.barbershop_id == barbershop.id).first()
    if not barber or not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Barbeiro ou serviço não encontrado.")

    starts_at = payload.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=ZoneInfo(barbershop.timezone))

    try:
        ends_at = scheduling.validate_new_appointment(db, barbershop.id, barber, service, starts_at)
    except scheduling.SchedulingError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    appointment = Appointment(
        barbershop_id=barbershop.id,
        customer_id=payload.customer_id,
        barber_id=barber.id,
        service_id=service.id,
        starts_at=starts_at,
        ends_at=ends_at,
        duration_minutes=service.duration_minutes,
        price_at_booking=service.price,
        status=AppointmentStatus.CONFIRMED,
        notes=payload.notes,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.put("/{appointment_id}", response_model=AppointmentOut)
def update_appointment(
    appointment_id: str,
    payload: AppointmentUpdate,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id, Appointment.barbershop_id == barbershop.id
    ).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agendamento não encontrado.")

    data = payload.model_dump(exclude_unset=True)

    reschedule_fields = {"barber_id", "service_id", "starts_at"}
    if reschedule_fields & data.keys():
        barber = db.get(Barber, data.get("barber_id", appointment.barber_id))
        service = db.get(Service, data.get("service_id", appointment.service_id))
        starts_at = data.get("starts_at", appointment.starts_at)
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=ZoneInfo(barbershop.timezone))
        try:
            ends_at = scheduling.validate_new_appointment(
                db, barbershop.id, barber, service, starts_at, ignore_appointment_id=appointment.id
            )
        except scheduling.SchedulingError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
        appointment.barber_id = barber.id
        appointment.service_id = service.id
        appointment.starts_at = starts_at
        appointment.ends_at = ends_at
        appointment.duration_minutes = service.duration_minutes
        appointment.price_at_booking = service.price

    for field in ("status", "notes", "cancelled_reason"):
        if field in data:
            setattr(appointment, field, data[field])

    db.commit()
    db.refresh(appointment)
    return appointment


@router.delete("/{appointment_id}", response_model=AppointmentOut)
def cancel_appointment(
    appointment_id: str,
    reason: str | None = None,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id, Appointment.barbershop_id == barbershop.id
    ).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agendamento não encontrado.")

    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancelled_reason = reason
    db.commit()
    db.refresh(appointment)
    return appointment


@router.get("/availability/slots", response_model=list[AvailabilitySlot])
def get_availability(
    service_id: str,
    date: date_cls,
    barber_id: str | None = None,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = db.query(Service).filter(Service.id == service_id,
                                        Service.barbershop_id == barbershop.id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado.")

    barbers = (
        [b for b in service.barbers if b.is_active]
        if not barber_id
        else [db.query(Barber).filter(Barber.id == barber_id,
                                       Barber.barbershop_id == barbershop.id).first()]
    )
    barbers = [b for b in barbers if b]

    results: list[AvailabilitySlot] = []
    for barber in barbers:
        for slot in scheduling.list_available_slots(db, barbershop.id, barber, service, date, barbershop.timezone):
            results.append(AvailabilitySlot(barber_id=barber.id, barber_name=barber.name,
                                              start_time=slot.strftime("%H:%M")))
    return results
