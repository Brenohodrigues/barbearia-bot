from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_current_barbershop, get_current_user, get_db
from app.models.barbershop import Barbershop
from app.models.service import Service
from app.models.user import User
from app.schemas.service import ServiceCreate, ServiceOut, ServiceUpdate

router = APIRouter()


@router.get("", response_model=list[ServiceOut])
def list_services(
    include_inactive: bool = False,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Service).filter(Service.barbershop_id == barbershop.id)
    if not include_inactive:
        query = query.filter(Service.is_active.is_(True))
    return query.order_by(Service.name).all()


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(
    payload: ServiceCreate,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = Service(barbershop_id=barbershop.id, **payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.put("/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: str,
    payload: ServiceUpdate,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    service = db.query(Service).filter(
        Service.id == service_id, Service.barbershop_id == barbershop.id
    ).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_service(
    service_id: str,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Não remove fisicamente (preserva histórico de agendamentos) - apenas desativa."""
    service = db.query(Service).filter(
        Service.id == service_id, Service.barbershop_id == barbershop.id
    ).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Serviço não encontrado.")
    service.is_active = False
    db.commit()
