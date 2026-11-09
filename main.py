from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from app.database import engine, Base, get_db
from app import models
from app.auth import generate_api_key, hash_api_key, get_current_tenant
from app.schemas import TenantCreate, TenantResponse, TrackingNodeCreate, TrackingNodeResponse

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
    return {"status": "success", "message": "Spatial NodeBase API - Database Connected!", "stage": 4}

@app.post("/tenants", response_model=TenantResponse, tags=["Tenants"])
def create_tenant(tenant: TenantCreate, db: Session = Depends(get_db)):
    raw_key = generate_api_key()
    hashed_key = hash_api_key(raw_key)
    new_tenant = models.Tenant(name=tenant.name, api_key_hash=hashed_key)
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)
    return {"id": new_tenant.id, "name": new_tenant.name, "api_key": raw_key}

@app.get("/me", tags=["Security"])
def get_tenant_info(current_tenant: models.Tenant = Depends(get_current_tenant)):
    return {"tenant_id": current_tenant.id, "name": current_tenant.name, "status": "Kimlik dogrulandi."}

@app.post("/nodes", response_model=TrackingNodeResponse, tags=["Tracking Nodes"])
def create_node(node: TrackingNodeCreate, db: Session = Depends(get_db), current_tenant: models.Tenant = Depends(get_current_tenant)):
    new_node = models.TrackingNode(**node.model_dump(), tenant_id=current_tenant.id)
    db.add(new_node)
    db.commit()
    db.refresh(new_node)
    return new_node

@app.get("/nodes", response_model=List[TrackingNodeResponse], tags=["Tracking Nodes"])
def get_nodes(db: Session = Depends(get_db), current_tenant: models.Tenant = Depends(get_current_tenant), limit: int = 100):
    nodes = db.query(models.TrackingNode).filter(models.TrackingNode.tenant_id == current_tenant.id).limit(limit).all()
    return nodes
