from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app import models

# Uygulama başlarken veritabanı tablolarını oluştur
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
    return {
        "status": "success", 
        "message": "Spatial NodeBase API - Database Connected!",
        "stage": 2
    }
