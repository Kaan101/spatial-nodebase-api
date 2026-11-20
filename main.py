import hashlib
import os
import secrets
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# 1. .env dosyasını DATABASE_URL ve engine oluşturulmadan ÖNCE yükle
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ[key.strip()] = val.strip().strip('"').strip("'")

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, create_engine, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import flag_modified

# ==============================================================================
# 2. VERİTABANI VE ORTAM AYARLARI
# ==============================================================================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:yhmp123@127.0.0.1:5433/youhavemi_pro",
)
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "sn_admin_master_2026")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000"},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==============================================================================
# 3. VERİTABANI MODELLERİ (SQLAlchemy)
# ==============================================================================
class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    api_key_hash = Column(String, unique=True, index=True, nullable=False)
    settings = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def get_code(self) -> str:
        if isinstance(self.settings, dict) and self.settings.get("code"):
            return str(self.settings["code"])
        return str(self.id)[:8].upper()

    def get_is_active(self) -> bool:
        if isinstance(self.settings, dict) and "is_active" in self.settings:
            return bool(self.settings["is_active"])
        return True


class TrackingNode(Base):
    __tablename__ = "tracking_nodes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True, nullable=False)
    code = Column(String, index=True, nullable=False)
    label = Column(String, nullable=True)
    definition = Column(String, nullable=True)
    transaction_id = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    firm_code = Column(String, nullable=True)
    firm = Column(String, nullable=True)
    branch = Column(String, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    country = Column(String, nullable=True)
    region = Column(String, nullable=True)
    city = Column(String, nullable=True)
    address = Column(String, nullable=True)
    postalcode = Column(String, nullable=True)
    event_date = Column(DateTime, default=datetime.utcnow)


class FormFieldDefinition(Base):
    __tablename__ = "form_field_definitions"

    id = Column(Integer, primary_key=True, index=True)
    field_key = Column(String, unique=True, index=True, nullable=False)
    label = Column(String, nullable=False)
    field_type = Column(String, nullable=False, default="text")
    placeholder = Column(String, nullable=True, default="")
    default_value = Column(String, nullable=True, default="")
    options_json = Column(JSON, nullable=True)
    required = Column(Integer, nullable=False, default=0)
    sort_order = Column(Integer, nullable=False, default=100)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


# ==============================================================================
# 4. FASTAPI UYGULAMASI VE CORS
# ==============================================================================
app = FastAPI(
    title="Spatial NodeBase API",
    version="1.0.0",
    description="B2B Multi-Tenant Lojistik ve Konum İzleme Platformu Backend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# 5. PYDANTIC ŞEMALARI VE GÜVENLİK YARDIMCILARI
# ==============================================================================
class RegisterFirmRequest(BaseModel):
    firmName: str


class NodeCreateRequest(BaseModel):
    code: str
    label: Optional[str] = ""
    definition: Optional[str] = ""
    transaction_id: Optional[str] = ""
    unit: Optional[str] = ""
    firm_code: Optional[str] = ""
    firm: Optional[str] = ""
    branch: Optional[str] = ""
    latitude: float
    longitude: float
    country: Optional[str] = "Türkiye"
    region: Optional[str] = ""
    city: Optional[str] = ""
    address: Optional[str] = ""
    postalcode: Optional[str] = ""
    event_date: Optional[datetime] = None


class SystemSettingsSchema(BaseModel):
    polling_interval_ms: int
    default_country: str
    geocoding_provider: str
    allow_public_registration: bool


class FormFieldCreateRequest(BaseModel):
    field_key: str
    label: str
    field_type: str = "text"
    placeholder: Optional[str] = ""
    default_value: Optional[str] = ""
    options: Optional[list[str]] = None
    required: bool = False
    sort_order: Optional[int] = None


class FormFieldUpdateRequest(BaseModel):
    field_key: Optional[str] = None
    label: Optional[str] = None
    field_type: Optional[str] = None
    placeholder: Optional[str] = None
    default_value: Optional[str] = None
    options: Optional[list[str]] = None
    required: Optional[bool] = None
    sort_order: Optional[int] = None


class TenantFormConfigRequest(BaseModel):
    field_keys: list[str]


DEFAULT_FORM_FIELDS = [
    {"field_key": "code", "label": "Araç / Cihaz Kodu", "field_type": "text", "placeholder": "Araç/Cihaz Kodu *", "required": True, "sort_order": 10},
    {"field_key": "label", "label": "Etiket", "field_type": "text", "placeholder": "Serbest Metin / Etiket (label)", "required": False, "sort_order": 20},
    {"field_key": "definition", "label": "Detaylı Tanım", "field_type": "textarea", "placeholder": "Detaylı Tanım (definition)", "required": False, "sort_order": 30},
    {"field_key": "transaction_id", "label": "İşlem ID", "field_type": "text", "placeholder": "İşlem veya Sinyal Takip ID", "required": False, "sort_order": 40},
    {"field_key": "unit", "label": "Birim", "field_type": "text", "placeholder": "Birim Bilgisi (unit)", "required": False, "sort_order": 50},
    {"field_key": "branch", "label": "Şube", "field_type": "text", "placeholder": "Şube veya Departman (branch)", "required": False, "sort_order": 60},
    {"field_key": "latitude", "label": "Enlem (Latitude)", "field_type": "number", "placeholder": "Enlem (Latitude) *", "required": True, "sort_order": 70},
    {"field_key": "longitude", "label": "Boylam (Longitude)", "field_type": "number", "placeholder": "Boylam (Longitude) *", "required": True, "sort_order": 80},
    {"field_key": "country", "label": "Ülke", "field_type": "text", "placeholder": "Ülke Bilgisi (country)", "default_value": "Türkiye", "required": False, "sort_order": 90},
    {"field_key": "region", "label": "Bölge", "field_type": "text", "placeholder": "Bölge Bilgisi (region)", "required": False, "sort_order": 100},
    {"field_key": "city", "label": "Şehir", "field_type": "text", "placeholder": "Şehir Bilgisi (city)", "required": False, "sort_order": 110},
    {"field_key": "address", "label": "Açık Adres", "field_type": "text", "placeholder": "Açık Adres (address)", "required": False, "sort_order": 120},
    {"field_key": "postalcode", "label": "Posta Kodu", "field_type": "text", "placeholder": "Posta Kodu (postalcode)", "required": False, "sort_order": 130},
]


def seed_default_form_fields(db: Session):
    if db.query(func.count(FormFieldDefinition.id)).scalar() == 0:
        for item in DEFAULT_FORM_FIELDS:
            db.add(
                FormFieldDefinition(
                    field_key=item["field_key"],
                    label=item["label"],
                    field_type=item["field_type"],
                    placeholder=item.get("placeholder", ""),
                    default_value=item.get("default_value", ""),
                    options_json=item.get("options"),
                    required=1 if item.get("required") else 0,
                    sort_order=item.get("sort_order", 100),
                )
            )
        db.commit()


def serialize_form_field(row: FormFieldDefinition) -> dict:
    return {
        "id": row.id,
        "field_key": row.field_key,
        "label": row.label,
        "field_type": row.field_type,
        "placeholder": row.placeholder or "",
        "default_value": row.default_value or "",
        "options": row.options_json if isinstance(row.options_json, list) else [],
        "required": bool(row.required),
        "sort_order": row.sort_order,
    }


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_current_tenant(x_api_key: str = Header(...), db: Session = Depends(get_db)) -> Tenant:
    hashed = hash_api_key(x_api_key)
    tenant = db.query(Tenant).filter(Tenant.api_key_hash == hashed).first()
    if not tenant:
        raise HTTPException(status_code=401, detail="Geçersiz API Key.")
    if not tenant.get_is_active():
        raise HTTPException(status_code=403, detail="Firma API erişimi askıya alınmış.")
    return tenant


def verify_admin(x_admin_secret: str = Header(...)):
    if x_admin_secret != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Yetkisiz erişim: Geçersiz Admin Anahtarı.")
    return True


# ==============================================================================
# 6. KİRACI (TENANT) VE KONUM (NODE) UÇ NOKTALARI
# ==============================================================================
@app.post("/register-firm")
def register_firm(payload: RegisterFirmRequest, db: Session = Depends(get_db)):
    clean_name = payload.firmName.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Firma adı boş olamaz.")

    prefix = "".join(ch for ch in clean_name.upper() if ch.isalnum())[:3] or "FRM"
    suffix = secrets.token_hex(2).upper()
    firm_code = f"{prefix}-{suffix}"

    raw_api_key = f"sn_{secrets.token_urlsafe(24)}"
    key_hash = hash_api_key(raw_api_key)

    new_tenant = Tenant(
        name=clean_name,
        api_key_hash=key_hash,
        settings={"code": firm_code, "is_active": True},
    )
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)

    return {
        "firmName": new_tenant.name,
        "firmCode": new_tenant.get_code(),
        "apiKey": raw_api_key,
    }


@app.get("/me")
def get_me(current_tenant: Tenant = Depends(get_current_tenant)):
    return {
        "name": current_tenant.name,
        "code": current_tenant.get_code(),
    }


@app.get("/me/form-fields")
def get_my_form_fields(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    seed_default_form_fields(db)
    rows = (
        db.query(FormFieldDefinition)
        .order_by(FormFieldDefinition.sort_order.asc(), FormFieldDefinition.id.asc())
        .all()
    )
    serialized = [serialize_form_field(r) for r in rows]
    valid_map = {item["field_key"]: item for item in serialized}

    settings_dict = current_tenant.settings if isinstance(current_tenant.settings, dict) else {}
    if "form_field_keys" in settings_dict and isinstance(settings_dict["form_field_keys"], list):
        ordered_selected = []
        for k in settings_dict["form_field_keys"]:
            if k in valid_map:
                ordered_selected.append(valid_map[k])
        return ordered_selected

    return serialized


@app.get("/nodes")
def list_nodes(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    nodes = (
        db.query(TrackingNode)
        .filter(TrackingNode.tenant_id == current_tenant.id)
        .order_by(TrackingNode.event_date.desc())
        .all()
    )
    return nodes


@app.post("/nodes")
def create_node(
    payload: NodeCreateRequest,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    node = TrackingNode(
        tenant_id=current_tenant.id,
        code=payload.code,
        label=payload.label,
        definition=payload.definition,
        transaction_id=payload.transaction_id,
        unit=payload.unit,
        firm_code=payload.firm_code or current_tenant.get_code(),
        firm=payload.firm or current_tenant.name,
        branch=payload.branch,
        latitude=payload.latitude,
        longitude=payload.longitude,
        country=payload.country,
        region=payload.region,
        city=payload.city,
        address=payload.address,
        postalcode=payload.postalcode,
        event_date=payload.event_date or datetime.utcnow(),
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


# ==============================================================================
# 7. ADMIN YÖNETİM UÇ NOKTALARI
# ==============================================================================
@app.get("/api/v1/admin/overview", dependencies=[Depends(verify_admin)])
def get_admin_overview(db: Session = Depends(get_db)):
    try:
        total_tenants = db.query(func.count(Tenant.id)).scalar() or 0
        total_nodes = db.query(func.count(TrackingNode.id)).scalar() or 0
        unique_vehicles = db.query(func.count(func.distinct(TrackingNode.code))).scalar() or 0
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Overview sorgu hatası: {str(e)}")

    return {
        "system_status": "Operational",
        "api_version": "1.0.0",
        "database_engine": "PostgreSQL (Multi-Tenant Isolated)",
        "security_protocol": "SHA-256 API Key + Zero-Trust Tenant Isolation",
        "metrics": {
            "total_tenants": total_tenants,
            "total_nodes": total_nodes,
            "unique_vehicles": unique_vehicles,
        },
    }


@app.get("/api/v1/admin/tenants", dependencies=[Depends(verify_admin)])
def get_all_tenants(db: Session = Depends(get_db)):
    try:
        tenants = db.query(Tenant).all()
        result = []
        for t in tenants:
            node_count = db.query(func.count(TrackingNode.id)).filter(TrackingNode.tenant_id == t.id).scalar() or 0
            result.append({
                "id": str(t.id),
                "name": t.name,
                "code": t.get_code(),
                "api_key_hash_preview": f"sha256:{(t.api_key_hash or '')[:12]}...",
                "is_active": t.get_is_active(),
                "node_count": node_count,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tenants sorgu hatası: {str(e)}")


@app.patch("/api/v1/admin/tenants/{tenant_id}/toggle-status", dependencies=[Depends(verify_admin)])
def toggle_tenant_status(tenant_id: str, db: Session = Depends(get_db)):
    try:
        parsed_id = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz Tenant ID formatı.")

    tenant = db.query(Tenant).filter(Tenant.id == parsed_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Firma bulunamadı.")

    current_settings = dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
    next_status = not tenant.get_is_active()
    current_settings["is_active"] = next_status
    tenant.settings = current_settings
    flag_modified(tenant, "settings")
    db.commit()
    return {"id": str(tenant.id), "is_active": next_status}


@app.get("/api/v1/admin/tenants/{tenant_id}/form-fields", dependencies=[Depends(verify_admin)])
def get_admin_tenant_form_fields(tenant_id: str, db: Session = Depends(get_db)):
    seed_default_form_fields(db)
    try:
        parsed_id = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz Tenant ID formatı.")

    tenant = db.query(Tenant).filter(Tenant.id == parsed_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Firma bulunamadı.")

    all_fields = (
        db.query(FormFieldDefinition)
        .order_by(FormFieldDefinition.sort_order.asc(), FormFieldDefinition.id.asc())
        .all()
    )
    all_keys = [f.field_key for f in all_fields]

    settings_dict = tenant.settings if isinstance(tenant.settings, dict) else {}
    if "form_field_keys" in settings_dict and isinstance(settings_dict["form_field_keys"], list):
        selected_keys = [k for k in settings_dict["form_field_keys"] if k in all_keys]
    else:
        selected_keys = all_keys

    return {
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "tenant_code": tenant.get_code(),
        "selected_field_keys": selected_keys,
    }


@app.put("/api/v1/admin/tenants/{tenant_id}/form-fields", dependencies=[Depends(verify_admin)])
def update_admin_tenant_form_fields(
    tenant_id: str,
    payload: TenantFormConfigRequest,
    db: Session = Depends(get_db),
):
    seed_default_form_fields(db)
    try:
        parsed_id = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz Tenant ID formatı.")

    tenant = db.query(Tenant).filter(Tenant.id == parsed_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Firma bulunamadı.")

    all_fields = db.query(FormFieldDefinition).all()
    valid_keys = {f.field_key for f in all_fields}

    cleaned_keys = []
    for k in payload.field_keys or []:
        key_str = str(k).strip()
        if key_str in valid_keys and key_str not in cleaned_keys:
            cleaned_keys.append(key_str)

    current_settings = dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
    current_settings["form_field_keys"] = cleaned_keys
    tenant.settings = current_settings
    flag_modified(tenant, "settings")
    db.commit()

    return {
        "status": "success",
        "tenant_id": str(tenant.id),
        "selected_field_keys": cleaned_keys,
    }


@app.get("/api/v1/admin/form-fields", dependencies=[Depends(verify_admin)])
def list_admin_form_fields(db: Session = Depends(get_db)):
    seed_default_form_fields(db)
    rows = (
        db.query(FormFieldDefinition)
        .order_by(FormFieldDefinition.sort_order.asc(), FormFieldDefinition.id.asc())
        .all()
    )
    return [serialize_form_field(r) for r in rows]


@app.post("/api/v1/admin/form-fields", dependencies=[Depends(verify_admin)])
def create_admin_form_field(payload: FormFieldCreateRequest, db: Session = Depends(get_db)):
    seed_default_form_fields(db)
    clean_key = payload.field_key.strip().lower().replace(" ", "_")
    clean_label = payload.label.strip()
    if not clean_key or not clean_label:
        raise HTTPException(status_code=400, detail="Alan anahtarı (field_key) ve etiketi (label) zorunludur.")

    existing = db.query(FormFieldDefinition).filter(FormFieldDefinition.field_key == clean_key).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"'{clean_key}' anahtarı zaten katalogda mevcut.")

    next_order = payload.sort_order
    if next_order is None:
        max_order = db.query(func.max(FormFieldDefinition.sort_order)).scalar() or 0
        next_order = max_order + 10

    row = FormFieldDefinition(
        field_key=clean_key,
        label=clean_label,
        field_type=payload.field_type.strip() or "text",
        placeholder=(payload.placeholder or "").strip(),
        default_value=(payload.default_value or "").strip(),
        options_json=[opt.strip() for opt in (payload.options or []) if opt.strip()],
        required=1 if payload.required else 0,
        sort_order=next_order,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_form_field(row)


@app.put("/api/v1/admin/form-fields/{field_id}", dependencies=[Depends(verify_admin)])
def update_admin_form_field(
    field_id: int,
    payload: FormFieldUpdateRequest,
    db: Session = Depends(get_db),
):
    row = db.query(FormFieldDefinition).filter(FormFieldDefinition.id == field_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Form alanı bulunamadı.")

    if payload.field_key is not None:
        clean_key = payload.field_key.strip().lower().replace(" ", "_")
        if not clean_key:
            raise HTTPException(status_code=400, detail="Alan anahtarı (field_key) boş olamaz.")
        conflict = (
            db.query(FormFieldDefinition)
            .filter(FormFieldDefinition.field_key == clean_key, FormFieldDefinition.id != field_id)
            .first()
        )
        if conflict:
            raise HTTPException(status_code=409, detail=f"'{clean_key}' anahtarı başka bir alanda kullanılıyor.")
        row.field_key = clean_key

    if payload.label is not None:
        clean_label = payload.label.strip()
        if not clean_label:
            raise HTTPException(status_code=400, detail="Görünen etiket (label) boş olamaz.")
        row.label = clean_label

    if payload.field_type is not None:
        row.field_type = payload.field_type.strip() or "text"

    if payload.placeholder is not None:
        row.placeholder = payload.placeholder.strip()

    if payload.default_value is not None:
        row.default_value = payload.default_value.strip()

    if payload.options is not None:
        row.options_json = [opt.strip() for opt in payload.options if opt.strip()]

    if payload.required is not None:
        row.required = 1 if payload.required else 0

    if payload.sort_order is not None:
        row.sort_order = payload.sort_order

    db.commit()
    db.refresh(row)
    return serialize_form_field(row)


@app.delete("/api/v1/admin/form-fields/{field_id}", dependencies=[Depends(verify_admin)])
def delete_admin_form_field(field_id: int, db: Session = Depends(get_db)):
    row = db.query(FormFieldDefinition).filter(FormFieldDefinition.id == field_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Form alanı bulunamadı.")
    db.delete(row)
    db.commit()
    return {"status": "deleted", "id": field_id}


@app.delete("/api/v1/admin/tenants/{tenant_id}", dependencies=[Depends(verify_admin)])
def delete_tenant(tenant_id: str, db: Session = Depends(get_db)):
    try:
        parsed_id = uuid.UUID(tenant_id.strip())
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz Tenant ID formatı.")

    tenant = db.query(Tenant).filter(Tenant.id == parsed_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Firma bulunamadı.")

    firm_name = tenant.name
    db.query(TrackingNode).filter(TrackingNode.tenant_id == parsed_id).delete(synchronize_session=False)
    db.query(Tenant).filter(Tenant.id == parsed_id).delete(synchronize_session=False)
    db.commit()

    return {"status": "deleted", "id": str(parsed_id), "name": firm_name}


class TenantUpdateRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None


@app.post("/api/v1/admin/tenants/{tenant_id}/update", dependencies=[Depends(verify_admin)])
def update_tenant_post(
    tenant_id: str,
    payload: TenantUpdateRequest,
    db: Session = Depends(get_db),
):
    try:
        parsed_id = uuid.UUID(tenant_id.strip())
    except ValueError:
        raise HTTPException(status_code=400, detail="Geçersiz Tenant ID formatı.")

    tenant = db.query(Tenant).filter(Tenant.id == parsed_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Firma bulunamadı.")

    current_settings = dict(tenant.settings) if isinstance(tenant.settings, dict) else {}
    update_values: Dict[str, Any] = {}

    if payload.name is not None:
        clean_name = payload.name.strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Firma adı boş olamaz.")
        update_values["name"] = clean_name

    if payload.code is not None:
        clean_code = payload.code.strip().upper()
        if not clean_code:
            raise HTTPException(status_code=400, detail="Firma kodu boş olamaz.")
        current_settings["code"] = clean_code
    elif "code" not in current_settings:
        current_settings["code"] = tenant.get_code()

    if "is_active" not in current_settings:
        current_settings["is_active"] = tenant.get_is_active()

    update_values["settings"] = current_settings
    db.query(Tenant).filter(Tenant.id == parsed_id).update(update_values, synchronize_session=False)
    db.commit()

    updated_tenant = db.query(Tenant).filter(Tenant.id == parsed_id).first()
    node_count = db.query(func.count(TrackingNode.id)).filter(TrackingNode.tenant_id == parsed_id).scalar() or 0

    return {
        "id": str(updated_tenant.id),
        "name": updated_tenant.name,
        "code": updated_tenant.get_code(),
        "api_key_hash_preview": f"sha256:{(updated_tenant.api_key_hash or '')[:12]}...",
        "is_active": updated_tenant.get_is_active(),
        "node_count": node_count,
        "created_at": updated_tenant.created_at.isoformat() if updated_tenant.created_at else None,
    }


@app.get("/api/v1/admin/settings", dependencies=[Depends(verify_admin)])
def get_system_settings(db: Session = Depends(get_db)):
    return {
        "polling_interval_ms": 3000,
        "default_country": "Türkiye",
        "geocoding_provider": "Nominatim Proxy (/api/v1/reverse-geocode)",
        "allow_public_registration": True,
    }


@app.put("/api/v1/admin/settings", dependencies=[Depends(verify_admin)])
def update_system_settings(settings: SystemSettingsSchema, db: Session = Depends(get_db)):
    return {"status": "success", "message": "Sistem ayarları güncellendi.", "settings": settings}