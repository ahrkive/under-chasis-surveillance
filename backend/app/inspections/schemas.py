"""
Pydantic Schemas — Request/Response Models
===========================================
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Auth Schemas ─────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class GuardCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="guard", pattern="^(admin|guard)$")


class GuardResponse(BaseModel):
    id: str
    username: str
    full_name: str
    role: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Inspection Schemas ───────────────────────────────────────────────────

class InspectionDecision(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")
    vehicle_id: Optional[str] = Field(None, max_length=50)
    license_plate: Optional[str] = Field(None, max_length=30)
    notes: Optional[str] = Field(None, max_length=500)
    threat_level: Optional[str] = Field("normal", pattern="^(normal|warning|critical)$")


class InspectionResponse(BaseModel):
    id: str
    bot_id: str
    decision: str
    model_confidence: Optional[float] = None
    model_prediction: Optional[str] = None
    model_version: Optional[int] = None
    vehicle_id: Optional[str] = None
    license_plate: Optional[str] = None
    notes: Optional[str] = None
    threat_level: Optional[str] = "normal"
    image_cloud_url: Optional[str] = None
    image_url: Optional[str] = None
    captured_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    guard: Optional[GuardResponse] = None

    class Config:
        from_attributes = True


class VehicleResponse(BaseModel):
    id: str
    license_plate: str
    owner_name: Optional[str] = None
    baseline_inspection_id: Optional[str] = None
    total_inspections: int
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EdgeBotResponse(BaseModel):
    id: str
    name: str
    lane: str
    status: str
    battery_level: int
    firmware_version: str
    last_ping_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InspectionListResponse(BaseModel):
    inspections: list[InspectionResponse]
    total: int
    page: int
    page_size: int


# ── WebSocket Message Schemas ────────────────────────────────────────────

class ImageHeader(BaseModel):
    """Header sent by the Pi before the binary image frame."""
    bot_id: str
    timestamp: float
    sequence: int
    sha256: str
    size: int
    filename: str
    license_plate: Optional[str] = None


class GuardPushMessage(BaseModel):
    """Message pushed to the guard UI via WebSocket."""
    type: str  # new_image | decision_ack | status
    inspection_id: Optional[str] = None
    image_data_b64: Optional[str] = None  # Base64 for WS push to browser
    model_prediction: Optional[str] = None
    model_confidence: Optional[float] = None
    model_version: Optional[int] = None
    license_plate: Optional[str] = None
    decision: Optional[str] = None
    message: Optional[str] = None


# ── Model Schemas ────────────────────────────────────────────────────────

class ModelVersionResponse(BaseModel):
    version: int
    training_image_count: int
    validation_accuracy: Optional[float] = None
    status: str
    trained_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
