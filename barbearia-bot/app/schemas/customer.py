from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: Optional[str]
    phone: str
    last_visit_at: Optional[datetime]
    visits_count: int
    is_blocked: bool


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    is_blocked: Optional[bool] = None
