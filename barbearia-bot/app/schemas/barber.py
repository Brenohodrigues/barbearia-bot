from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.service import ServiceOut


class BarberHoursIn(BaseModel):
    weekday: int = Field(..., ge=0, le=6)
    is_off: bool = False
    starts_at: Optional[str] = None  # "HH:MM"
    ends_at: Optional[str] = None


class BarberBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    photo_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500)
    is_active: bool = True


class BarberCreate(BarberBase):
    service_ids: List[str] = []
    working_hours: List[BarberHoursIn] = []


class BarberUpdate(BaseModel):
    name: Optional[str] = None
    photo_url: Optional[str] = None
    bio: Optional[str] = None
    is_active: Optional[bool] = None
    service_ids: Optional[List[str]] = None
    working_hours: Optional[List[BarberHoursIn]] = None


class BarberOut(BarberBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    services: List[ServiceOut] = []
