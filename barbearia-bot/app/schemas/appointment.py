from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.appointment import AppointmentStatus


class AppointmentCreate(BaseModel):
    customer_id: str
    barber_id: str
    service_id: str
    starts_at: datetime
    notes: Optional[str] = Field(None, max_length=500)


class AppointmentUpdate(BaseModel):
    barber_id: Optional[str] = None
    service_id: Optional[str] = None
    starts_at: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None
    cancelled_reason: Optional[str] = None


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    customer_id: str
    barber_id: str
    service_id: str
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    price_at_booking: float
    status: AppointmentStatus
    notes: Optional[str]
    cancelled_reason: Optional[str]


class AvailabilityQuery(BaseModel):
    service_id: str
    date: str  # "YYYY-MM-DD"
    barber_id: Optional[str] = None


class AvailabilitySlot(BaseModel):
    barber_id: str
    barber_name: str
    start_time: str  # "HH:MM"
