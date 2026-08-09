"""
Creator / Admin Control Panel REST Router
==========================================
Provides minute-detail telemetry, system metrics, model version management,
training logs, and guard management endpoints for system creators.
"""

import os
import logging
from typing import Optional

import io
import zipfile
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.auth.service import hash_password
from app.config import get_settings
from app.database import get_db
from app.inspections.models import Guard, Inspection, ModelVersion, TrainingLog
from app.inspections.schemas import GuardCreate, GuardResponse, ModelVersionResponse
from app.inference.service import get_inference_service
from app.inspections.ws import get_connected_guard_count, get_active_guards_list

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Creator / Admin Control"])


@router.get("/stats")
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    admin: Guard = Depends(require_admin),
):
    """Detailed telemetry & metrics for creators."""
    settings = get_settings()
    inference = get_inference_service()

    # Inspection Counts
    total_resp = await db.execute(select(func.count(Inspection.id)))
    total_inspections = total_resp.scalar() or 0

    approved_resp = await db.execute(
        select(func.count(Inspection.id)).where(Inspection.decision == "approved")
    )
    approved_count = approved_resp.scalar() or 0

    rejected_resp = await db.execute(
        select(func.count(Inspection.id)).where(Inspection.decision == "rejected")
    )
    rejected_count = rejected_resp.scalar() or 0

    pending_resp = await db.execute(
        select(func.count(Inspection.id)).where(Inspection.decision == "pending")
    )
    pending_count = pending_resp.scalar() or 0

    # User Counts
    guards_resp = await db.execute(select(func.count(Guard.id)))
    total_users = guards_resp.scalar() or 0

    # Active Model Info
    active_ver = inference.model_version
    active_model_db = await db.execute(
        select(ModelVersion).where(ModelVersion.version == active_ver)
    )
    active_model_obj = active_model_db.scalar_one_or_none()

    # Calculate storage size
    storage_size_bytes = 0
    if os.path.exists(settings.storage_local_path):
        for root, _, files in os.walk(settings.storage_local_path):
            for f in files:
                storage_size_bytes += os.path.getsize(os.path.join(root, f))

    active_guards = get_active_guards_list()

    return {
        "system": {
            "environment": settings.app_env,
            "device": settings.inference_device,
            "storage_provider": settings.storage_provider,
            "storage_size_mb": round(storage_size_bytes / (1024 * 1024), 2),
            "connected_guard_clients": len(active_guards),
            "active_guards": active_guards,
        },
        "inspections": {
            "total": total_inspections,
            "approved": approved_count,
            "rejected": rejected_count,
            "pending": pending_count,
        },
        "ai_model": {
            "active_version": active_ver,
            "is_loaded": inference.is_loaded,
            "architecture": "ResNet50",
            "validation_accuracy": active_model_obj.validation_accuracy if active_model_obj else None,
            "training_images": active_model_obj.training_image_count if active_model_obj else 0,
        },
        "users": {
            "total_accounts": total_users,
        },
    }


@router.get("/models")
async def list_model_versions(
    db: AsyncSession = Depends(get_db),
    admin: Guard = Depends(require_admin),
):
    """List all AI model versions with validation metrics."""
    result = await db.execute(select(ModelVersion).order_by(desc(ModelVersion.version)))
    models = result.scalars().all()
    return [ModelVersionResponse.model_validate(m) for m in models]


@router.post("/models/{version}/activate")
async def activate_model_version(
    version: int,
    db: AsyncSession = Depends(get_db),
    admin: Guard = Depends(require_admin),
):
    """Creators can manually switch/hot-swap the active AI model version."""
    result = await db.execute(
        select(ModelVersion).where(ModelVersion.version == version)
    )
    target_model = result.scalar_one_or_none()
    if not target_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model version {version} not found.",
        )

    # Deactivate current active model
    active_result = await db.execute(
        select(ModelVersion).where(ModelVersion.status == "active")
    )
    current_active = active_result.scalars().all()
    for m in current_active:
        m.status = "archived"

    target_model.status = "active"
    await db.commit()

    # Hot-swap live inference engine
    inference = get_inference_service()
    await inference.hot_swap(version)

    return {
        "status": "success",
        "message": f"Hot-swapped live model to version {version}",
        "active_version": version,
    }


@router.get("/training-logs")
async def list_training_logs(
    db: AsyncSession = Depends(get_db),
    admin: Guard = Depends(require_admin),
):
    """Creators can view historical AI training run logs and loss curves."""
    result = await db.execute(select(TrainingLog).order_by(desc(TrainingLog.started_at)))
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "model_version": log.model_version,
            "new_images_count": log.new_images_count,
            "total_images_count": log.total_images_count,
            "loss": log.loss,
            "accuracy": log.accuracy,
            "status": log.status,
            "started_at": log.started_at,
            "completed_at": log.completed_at,
            "log_output": log.log_output,
        }
        for log in logs
    ]


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: Guard = Depends(require_admin),
):
    """List all registered system users (Guard and Creator accounts)."""
    result = await db.execute(select(Guard).order_by(Guard.created_at.desc()))
    users = result.scalars().all()
    return [GuardResponse.model_validate(u) for u in users]


@router.post("/users", response_model=GuardResponse, status_code=201)
async def create_user(
    request: GuardCreate,
    db: AsyncSession = Depends(get_db),
    admin: Guard = Depends(require_admin),
):
    """Creators can provision new Guard or Admin accounts."""
    result = await db.execute(
        select(Guard).where(Guard.username == request.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{request.username}' is already taken.",
        )

    guard = Guard(
        username=request.username,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        role=request.role,
    )
    db.add(guard)
    await db.commit()
    await db.refresh(guard)

    logger.info("Admin %s created user %s (%s)", admin.username, guard.username, guard.role)
    return GuardResponse.model_validate(guard)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: Guard = Depends(require_admin),
):
    """Creators can delete guard accounts (cannot delete active self)."""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own active admin account.",
        )

    result = await db.execute(select(Guard).where(Guard.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    await db.delete(user)
    await db.commit()
    logger.info("Admin %s deleted user %s (%s)", admin.username, user.username, user_id)
    return {"status": "success", "message": f"Account '{user.username}' deleted successfully."}


@router.post("/test-model")
async def test_model_image(
    file: UploadFile = File(...),
    admin: Guard = Depends(require_admin),
):
    """Creators can upload any image to test live ResNet50 model predictions & confidence scores."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a valid image format (JPEG, PNG, WEBP, etc.)",
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    inference = get_inference_service()
    if not inference.is_loaded:
        await inference.load_model()

    # Run inference
    result = await inference.predict(contents)
    prediction = result["prediction"]
    confidence = result["confidence"]

    # Calculate detailed class probabilities
    conf_val = float(confidence) if confidence is not None else 0.5
    other_val = round(1.0 - conf_val, 4)

    if prediction == "ok":
        probabilities = {"ok": round(conf_val, 4), "suspicious": other_val}
    else:
        probabilities = {"ok": other_val, "suspicious": round(conf_val, 4)}

    return {
        "filename": file.filename,
        "prediction": prediction,
        "confidence": round(conf_val, 4),
        "confidence_percentage": round(conf_val * 100, 1),
        "probabilities": probabilities,
        "model_version": inference.model_version,
        "architecture": "ResNet50",
        "input_shape": [1, 3, 256, 256],
        "image_size_bytes": len(contents),
    }


@router.post("/save-to-dataset")
async def save_image_to_dataset(
    label: str = "approved",
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: Guard = Depends(require_admin),
):
    """
    Creators can manually save tested images into the training dataset
    as 'approved' (normal/OK) or 'rejected' (suspicious/anomaly).
    """
    import uuid
    from datetime import datetime

    if label not in ["approved", "rejected", "ok", "suspicious"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Label must be 'approved'/'ok' or 'rejected'/'suspicious'",
        )

    normalized_label = "approved" if label in ["approved", "ok"] else "rejected"
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty.",
        )

    settings = get_settings()
    insp_id = str(uuid.uuid4())

    # Save to local storage folder
    folder = os.path.join(settings.storage_local_path, normalized_label, "creator_sandbox")
    os.makedirs(folder, exist_ok=True)
    filename = f"{insp_id}.jpg"
    file_path = os.path.join(folder, filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    # Run inference to store predicted confidence
    inference = get_inference_service()
    if not inference.is_loaded:
        await inference.load_model()
    pred_res = await inference.predict(contents)

    # Record in database
    now = datetime.utcnow()
    inspection = Inspection(
        id=insp_id,
        guard_id=admin.id,
        bot_id="creator_sandbox",
        image_local_path=file_path,
        decision=normalized_label,
        model_prediction=pred_res.get("prediction"),
        model_confidence=pred_res.get("confidence"),
        model_version=inference.model_version,
        captured_at=now,
        decided_at=now,
    )
    db.add(inspection)
    await db.commit()

    # Get updated total approved count
    approved_count_res = await db.execute(
        select(func.count(Inspection.id)).where(Inspection.decision == "approved")
    )
    total_approved = approved_count_res.scalar() or 0

    logger.info(
        "Creator %s saved image %s to dataset as '%s'",
        admin.username, insp_id, normalized_label
    )

    return {
        "status": "success",
        "message": f"Image successfully saved to dataset as {normalized_label.upper()}!",
        "inspection_id": insp_id,
        "decision": normalized_label,
        "image_path": file_path,
        "total_approved_images": total_approved,
    }


@router.get("/dataset-gallery")
async def list_dataset_gallery(
    decision: Optional[str] = "all",
    source: Optional[str] = "all",
    page: int = 1,
    page_size: int = 40,
    db: AsyncSession = Depends(get_db),
    admin: Guard = Depends(require_admin),
):
    """
    Creators can browse every saved image in the dataset (Approved & Rejected,
    from Edge Bots or Creator Sandbox uploads).
    """
    query = select(Inspection)

    if decision and decision.lower() != "all":
        norm_dec = "approved" if decision.lower() in ["approved", "ok"] else "rejected"
        query = query.where(Inspection.decision == norm_dec)

    if source and source.lower() != "all":
        if source.lower() == "sandbox":
            query = query.where(Inspection.bot_id == "creator_sandbox")
        elif source.lower() == "bot":
            query = query.where(Inspection.bot_id != "creator_sandbox")

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_resp = await db.execute(count_query)
    total = total_resp.scalar() or 0

    # Execute paginated query
    query = query.order_by(desc(Inspection.captured_at)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    inspections = result.scalars().all()

    items = []
    for insp in inspections:
        items.append({
            "id": insp.id,
            "bot_id": insp.bot_id,
            "guard_id": insp.guard_id,
            "decision": insp.decision,
            "model_prediction": insp.model_prediction,
            "model_confidence": insp.model_confidence,
            "model_version": insp.model_version,
            "captured_at": insp.captured_at.isoformat() if insp.captured_at else None,
            "image_url": f"/api/admin/dataset-images/{insp.id}/file",
            "is_sandbox": (insp.bot_id == "creator_sandbox"),
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.get("/dataset-images/{inspection_id}/file")
async def serve_dataset_image_file(
    inspection_id: str,
    token: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Serve raw dataset JPEG image file to Creator dashboard and Guard station.
    Accepts token via query parameter or direct request for browser <img> rendering.
    """
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()

    if not inspection or not inspection.image_local_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image for inspection {inspection_id} not found.",
        )

    file_path = inspection.image_local_path
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File on disk at '{file_path}' missing.",
        )

    return FileResponse(file_path, media_type="image/jpeg")


@router.get("/fleet")
async def list_fleet_bots(
    db: AsyncSession = Depends(get_db),
    admin: Guard = Depends(require_admin),
):
    """
    Creators can monitor all connected Edge Bots, battery levels, lane assignments, and health pings.
    """
    from app.inspections.models import EdgeBot

    result = await db.execute(select(EdgeBot))
    bots = result.scalars().all()

    # Seed default fleet if empty
    if not bots:
        default_bots = [
            EdgeBot(id="bot-north-gate", name="North Gate Inspection Crawler", lane="Lane 1", status="online", battery_level=94, firmware_version="v1.4.2"),
            EdgeBot(id="bot-south-gate", name="South Gate High-Speed Scanner", lane="Lane 2", status="online", battery_level=88, firmware_version="v1.4.2"),
            EdgeBot(id="bot-vip-lane", name="VIP Express Inspection Unit", lane="Lane 3", status="idle", battery_level=100, firmware_version="v1.4.2"),
        ]
        for b in default_bots:
            db.add(b)
        await db.commit()

        result = await db.execute(select(EdgeBot))
        bots = result.scalars().all()

    items = []
    for b in bots:
        items.append({
            "id": b.id,
            "name": b.name,
            "lane": b.lane,
            "status": b.status,
            "battery_level": b.battery_level,
            "firmware_version": b.firmware_version,
            "last_ping_at": b.last_ping_at.isoformat() if b.last_ping_at else None,
        })

    return {
        "total_bots": len(items),
        "online_bots": len([x for x in items if x["status"] == "online"]),
        "fleet": items,
    }


@router.get("/export-dataset-zip")
async def export_dataset_zip(
    decision: Optional[str] = "all",
    token: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Export all stored dataset images as a downloadable ZIP archive.
    Organizes images into /approved/ and /rejected/ folders inside the zip file.
    """
    query = select(Inspection).where(Inspection.image_local_path.isnot(None))
    if decision and decision.lower() != "all":
        norm_dec = "approved" if decision.lower() in ["approved", "ok"] else "rejected"
        query = query.where(Inspection.decision == norm_dec)

    result = await db.execute(query)
    inspections = result.scalars().all()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        added_names = set()
        for insp in inspections:
            file_path = insp.image_local_path
            if file_path and os.path.exists(file_path):
                folder = insp.decision or "uncategorized"
                plate = insp.license_plate or "UNTAGGED"
                ext = os.path.splitext(file_path)[1] or ".jpg"
                arc_name = f"{folder}/{plate}_{insp.id[:8]}{ext}"

                counter = 1
                while arc_name in added_names:
                    arc_name = f"{folder}/{plate}_{insp.id[:8]}_{counter}{ext}"
                    counter += 1
                added_names.add(arc_name)

                zip_file.write(file_path, arcname=arc_name)

    zip_buffer.seek(0)
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="undercarriage_dataset_archive.zip"'}
    )
