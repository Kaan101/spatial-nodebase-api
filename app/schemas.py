from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime

class TenantCreate(BaseModel):
    name: str

class TenantResponse(BaseModel):
    id: UUID
    name: str
    api_key: Optional[str] = None

    class Config:
        from_attributes = True

class TrackingNodeCreate(BaseModel):
    code: str
    label: Optional[str] = None
    definition: Optional[str] = None
    transaction_id: str
    unit: Optional[str] = None
    firm: Optional[str] = None
    branch: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    postalcode: Optional[str] = None
    regcode: Optional[str] = None
    event_date: datetime

class TrackingNodeResponse(TrackingNodeCreate):
    id: UUID
    tenant_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
