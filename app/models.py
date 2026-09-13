from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from .database import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    api_key_hash = Column(String, nullable=False) # 4. Madde: Sadece hash saklanacak
    settings = Column(JSON, default={}) # 3. Madde: Parametrik ayarlar burada duracak
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TrackingNode(Base):
    __tablename__ = "tracking_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True) # İzolasyon anahtarı
    
    code = Column(String, index=True)
    label = Column(String)
    definition = Column(String) # 5. Madde: İleride şifrelenmiş halde yazılacak
    transaction_id = Column(String, index=True)
    unit = Column(String)
    
    firm = Column(String)
    branch = Column(String)
    
    latitude = Column(Float)
    longitude = Column(Float)
    country = Column(String)
    region = Column(String)
    city = Column(String)
    address = Column(String) # 5. Madde: İleride şifrelenmiş halde yazılacak
    postalcode = Column(String)
    regcode = Column(String) # 5. Madde: Hassas
    
    event_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())