"""
ORM Models — Inspection System Database Schema
================================================
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Guard(Base):
    """Security guard who makes inspection decisions."""
    __tablename__ = "guards"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="guard")  # admin | guard
    created_at = Column(DateTime, server_default=func.now())

    inspections = relationship("Inspection", back_populates="guard")


class Inspection(Base):
    """A single undercarriage inspection record."""
    __tablename__ = "inspections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    guard_id = Column(String(36), ForeignKey("guards.id"), nullable=True)
    bot_id = Column(String(50), nullable=False, default="bot-001")

    # Image paths
    image_local_path = Column(String(500), nullable=True)
    image_cloud_url = Column(String(1000), nullable=True)

    # Decision
    decision = Column(String(20), nullable=False, default="pending")  # pending | approved | rejected

    # AI model output
    model_confidence = Column(Float, nullable=True)
    model_prediction = Column(String(20), nullable=True)  # ok | suspicious
    model_version = Column(Integer, ForeignKey("model_versions.version"), nullable=True)

    # Vehicle identification & Phase 2 ALPR
    vehicle_id = Column(String(50), nullable=True)
    license_plate = Column(String(30), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    threat_level = Column(String(20), nullable=False, default="normal")  # normal | warning | critical

    # Metadata
    metadata_json = Column(JSON, nullable=True)

    # Timestamps
    captured_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    guard = relationship("Guard", back_populates="inspections")
    model_ver = relationship("ModelVersion", back_populates="inspections")


class Vehicle(Base):
    """Tracks registered vehicles and their baseline undercarriage scans."""
    __tablename__ = "vehicles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    license_plate = Column(String(30), unique=True, nullable=False, index=True)
    owner_name = Column(String(100), nullable=True)
    baseline_inspection_id = Column(String(36), ForeignKey("inspections.id"), nullable=True)
    total_inspections = Column(Integer, nullable=False, default=1)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)


class EdgeBot(Base):
    """Tracks connected mobile edge inspection bots across lanes."""
    __tablename__ = "edge_bots"

    id = Column(String(50), primary_key=True)  # e.g. bot-north-gate
    name = Column(String(100), nullable=False)
    lane = Column(String(50), nullable=False, default="Lane 1")
    status = Column(String(20), nullable=False, default="online")  # online | offline | maintenance
    battery_level = Column(Integer, nullable=False, default=100)
    firmware_version = Column(String(20), nullable=False, default="v1.0")
    last_ping_at = Column(DateTime, default=datetime.utcnow)


class ModelVersion(Base):
    """Tracks each version of the trained CV model."""
    __tablename__ = "model_versions"

    version = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String(500), nullable=False)
    training_image_count = Column(Integer, nullable=False, default=0)
    validation_accuracy = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default="training")  # active | archived | training
    trained_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    inspections = relationship("Inspection", back_populates="model_ver")
    training_logs = relationship("TrainingLog", back_populates="model_ver")


class TrainingLog(Base):
    """Log entry for each training run."""
    __tablename__ = "training_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    model_version = Column(Integer, ForeignKey("model_versions.version"), nullable=False)
    new_images_count = Column(Integer, nullable=False, default=0)
    total_images_count = Column(Integer, nullable=False, default=0)
    loss = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default="running")  # success | failed | running
    log_output = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    model_ver = relationship("ModelVersion", back_populates="training_logs")
