from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class FirmCreate(BaseModel):
    firmName: str

class FirmOut(BaseModel):
    firmName: str
    firmCode: str
    apiKey: str

class TrackingNodeCreate(BaseModel):
    code: str
    label: Optional[str] = None
    definition: Optional[str] = None
    transaction_id: Optional[str] = None
    unit: Optional[str] = None
    firm: Optional[str] = None
    branch: Optional[str] = None
    latitude: float
    longitude: float
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    postalcode: Optional[str] = None
    regcode: Optional[str] = None
    event_date: Optional[datetime] = None

class TrackingNodeOut(TrackingNodeCreate):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    firm_code: Optional[str] = None

    class Config:
        from_attributes = True # Pydantic v2 için. v1 kullanıyorsanız orm_mode = True yapın