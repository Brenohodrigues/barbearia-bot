from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_current_barbershop, get_current_user, get_db
from app.models.barbershop import Barbershop
from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer import CustomerOut, CustomerUpdate

router = APIRouter()


@router.get("", response_model=list[CustomerOut])
def list_customers(
    search: str | None = None,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Customer).filter(Customer.barbershop_id == barbershop.id)
    if search:
        like = f"%{search}%"
        query = query.filter((Customer.name.ilike(like)) | (Customer.phone.ilike(like)))
    return query.order_by(Customer.name).all()


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: str,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id, Customer.barbershop_id == barbershop.id
    ).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    return customer


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: str,
    payload: CustomerUpdate,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id, Customer.barbershop_id == barbershop.id
    ).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: str,
    barbershop: Barbershop = Depends(get_current_barbershop),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Exclusão de dados a pedido do titular (LGPD). Remove o cadastro e
    mensagens; os agendamentos passados são mantidos anonimizados para fins
    contábeis/fiscais, com o vínculo ao cliente removido."""
    customer = db.query(Customer).filter(
        Customer.id == customer_id, Customer.barbershop_id == barbershop.id
    ).first()
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    db.delete(customer)
    db.commit()
