from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.database import engine, Base, get_db
from app import models
from app.auth import generate_api_key, hash_api_key, get_current_tenant
from app.schemas import TenantCreate, TenantResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Spatial NodeBase API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "success", "message": "Spatial NodeBase API - Database Connected!", "stage": 3}

# --- TENANT (KİRACI) YÖNETİMİ ---

@app.post("/tenants", response_model=TenantResponse)
def create_tenant(tenant: TenantCreate, db: Session = Depends(get_db)):
    raw_key = generate_api_key()
    hashed_key = hash_api_key(raw_key)
    
    new_tenant = models.Tenant(name=tenant.name, api_key_hash=hashed_key)
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)
    
    # Ham API Key sadece bu seferlik geri döndürülür, bir daha asla görülemez!
    return {"id": new_tenant.id, "name": new_tenant.name, "api_key": raw_key}

# --- GÜVENLİK TESTİ (Sadece geçerli API Key ile girilebilir) ---

@app.get("/me")
def get_tenant_info(current_tenant: models.Tenant = Depends(get_current_tenant)):
    return {
        "tenant_id": current_tenant.id, 
        "name": current_tenant.name, 
        "status": "Kimlik dogrulandi. İzolasyon basarili."
    }
