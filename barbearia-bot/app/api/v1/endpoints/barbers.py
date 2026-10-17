from datetime import time as time_cls

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_current_barbershop, get_current_user, get_db
from app.models.barber import Barber
from app.models.barbershop import Barbershop
from app.models.business_hours import BarberHours
from app.models.service import Service
from app.models.user import User
from app.schemas.barber import BarberCreate, BarberOut, BarberUpdate

router = APIRouter()


def _parse_hhmm(value: str) -> time_cls:
    hour, minute = map(int, value.split(":"))
    return time_cls(hour, minute)


@router.get("", response_model=list[BarberOut])
def list_barbers(
    include_inactive: bool = False,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Barber).filter(Barber.barbershop_id == barbershop.id)
    if not include_inactive:
        query = query.filter(Barber.is_active.is_(True))
    return query.order_by(Barber.name).all()


@router.post("", response_model=BarberOut, status_code=status.HTTP_201_CREATED)
def create_barber(
    payload: BarberCreate,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    barber = Barber(
        barbershop_id=barbershop.id,
        name=payload.name,
        photo_url=payload.photo_url,
        bio=payload.bio,
        is_active=payload.is_active,
    )
    if payload.service_ids:
        barber.services = db.query(Service).filter(
            Service.id.in_(payload.service_ids), Service.barbershop_id == barbershop.id
        ).all()
    db.add(barber)
    db.flush()

    for wh in payload.working_hours:
        db.add(BarberHours(
            barber_id=barber.id, weekday=wh.weekday, is_off=wh.is_off,
            starts_at=_parse_hhmm(wh.starts_at) if wh.starts_at else None,
            ends_at=_parse_hhmm(wh.ends_at) if wh.ends_at else None,
        ))

    db.commit()
    db.refresh(barber)
    return barber


@router.put("/{barber_id}", response_model=BarberOut)
def update_barber(
    barber_id: str,
    payload: BarberUpdate,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    barber = db.query(Barber).filter(
        Barber.id == barber_id, Barber.barbershop_id == barbershop.id
    ).first()
    if not barber:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Barbeiro não encontrado.")

    data = payload.model_dump(exclude_unset=True)
    for field in ("name", "photo_url", "bio", "is_active"):
        if field in data:
            setattr(barber, field, data[field])

    if payload.service_ids is not None:
        barber.services = db.query(Service).filter(
            Service.id.in_(payload.service_ids), Service.barbershop_id == barbershop.id
        ).all()

    if payload.working_hours is not None:
        db.query(BarberHours).filter(BarberHours.barber_id == barber.id).delete()
        for wh in payload.working_hours:
            db.add(BarberHours(
                barber_id=barber.id, weekday=wh.weekday, is_off=wh.is_off,
                starts_at=_parse_hhmm(wh.starts_at) if wh.starts_at else None,
                ends_at=_parse_hhmm(wh.ends_at) if wh.ends_at else None,
            ))

    db.commit()
    db.refresh(barber)
    return barber


@router.delete("/{barber_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_barber(
    barber_id: str,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    barber = db.query(Barber).filter(
        Barber.id == barber_id, Barber.barbershop_id == barbershop.id
    ).first()
    if not barber:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Barbeiro não encontrado.")
    barber.is_active = False
    db.commit()
