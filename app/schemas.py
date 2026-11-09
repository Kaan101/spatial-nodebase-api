from pydantic import BaseModel
from uuid import UUID
from typing import Optional

class TenantCreate(BaseModel):
    name: str

class TenantResponse(BaseModel):
    id: UUID
    name: str
    api_key: Optional[str] = None # SADECE oluşturulurken bir kereliğine gösterilir

    class Config:
        from_attributes = True
