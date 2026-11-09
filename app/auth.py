import secrets
import hashlib
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from .database import get_db
from .models import Tenant

# Gelen isteklerde header'da "X-API-Key" aranacak
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def generate_api_key():
    # sn_ (Spatial Node) prefix'i ile 32 byte'lık güvenli bir token üretir
    return f"sn_{secrets.token_urlsafe(32)}"

def hash_api_key(api_key: str) -> str:
    # Key'i SHA-256 ile geri döndürülemez şekilde hashler
    return hashlib.sha256(api_key.encode()).hexdigest()

def get_current_tenant(api_key: str = Security(api_key_header), db: Session = Depends(get_db)):
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API Key eksik (X-API-Key header gerekli)")
    
    hashed_key = hash_api_key(api_key)
    tenant = db.query(Tenant).filter(Tenant.api_key_hash == hashed_key).first()
    
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gecersiz API Key")
    
    return tenant
