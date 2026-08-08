"""
Inspection REST Router
=======================
"""

from typing import Optional
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.inspections.models import Guard, Inspection
from app.inspections.schemas import (
    InspectionDecision,
    InspectionResponse,
    InspectionListResponse,
)
from app.inspections.service import InspectionService
from app.inspections.ws import broadcast_to_guards

router = APIRouter(prefix="/api/inspections", tags=["Inspections"])


@router.get("", response_model=InspectionListResponse)
async def list_inspections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    decision: str = Query(None, pattern="^(pending|approved|rejected)$"),
    bot_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Guard = Depends(get_current_user),
):
    """List inspections with pagination and optional filters."""
    return await InspectionService.list_inspections(
        db=db,
        page=page,
        page_size=page_size,
        decision_filter=decision,
        bot_id=bot_id,
    )


@router.get("/{inspection_id}", response_model=InspectionResponse)
async def get_inspection(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Guard = Depends(get_current_user),
):
    """Get a single inspection by ID."""
    inspection = await InspectionService.get_inspection(db, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return InspectionResponse.model_validate(inspection)


@router.get("/{inspection_id}/image")
async def get_inspection_image(
    inspection_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Guard = Depends(get_current_user),
):
    """Get the raw JPEG image for an inspection."""
    inspection = await InspectionService.get_inspection(db, inspection_id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    if not inspection.image_local_path:
        raise HTTPException(status_code=404, detail="Image not available.")

    try:
        async with aiofiles.open(inspection.image_local_path, "rb") as f:
            image_data = await f.read()
        return Response(content=image_data, media_type="image/jpeg")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image file not found.")


@router.post("/{inspection_id}/decision", response_model=InspectionResponse)
async def submit_decision(
    inspection_id: str,
    decision: InspectionDecision,
    db: AsyncSession = Depends(get_db),
    current_user: Guard = Depends(get_current_user),
):
    """Submit a guard's decision (approve/reject) for an inspection."""
    try:
        inspection = await InspectionService.submit_decision(
            db=db,
            inspection_id=inspection_id,
            guard=current_user,
            decision=decision,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Broadcast decision to all guard UIs
    await broadcast_to_guards({
        "type": "decision_ack",
        "inspection_id": inspection_id,
        "decision": decision.decision,
        "message": f"Inspection {decision.decision} by {current_user.full_name}",
    })

    return InspectionResponse.model_validate(inspection)


@router.get("/vehicle/{license_plate}/history")
async def get_vehicle_history(
    license_plate: str,
    db: AsyncSession = Depends(get_db),
    current_user: Guard = Depends(get_current_user),
):
    """
    Fetch historical undercarriage scans for a specific vehicle license plate.
    Used by Guard UI for baseline diff comparison.
    """
    clean_plate = license_plate.strip().upper()
    result = await db.execute(
        select(Inspection)
        .where(Inspection.license_plate.ilike(f"%{clean_plate}%"))
        .order_by(Inspection.captured_at.desc())
        .limit(10)
    )
    inspections = result.scalars().all()

    items = []
    for insp in inspections:
        items.append({
            "id": insp.id,
            "license_plate": insp.license_plate or clean_plate,
            "decision": insp.decision,
            "model_prediction": insp.model_prediction,
            "model_confidence": insp.model_confidence,
            "threat_level": insp.threat_level or "normal",
            "notes": insp.notes,
            "captured_at": insp.captured_at.isoformat() if insp.captured_at else None,
            "image_url": f"/api/admin/dataset-images/{insp.id}/file",
        })

    return {
        "license_plate": clean_plate,
        "total_scans": len(items),
        "history": items,
        "baseline": items[-1] if items else None,
    }


@router.post("/{inspection_id}/annotate")
async def annotate_inspection(
    inspection_id: str,
    notes: Optional[str] = None,
    license_plate: Optional[str] = None,
    threat_level: Optional[str] = "normal",
    db: AsyncSession = Depends(get_db),
    current_user: Guard = Depends(get_current_user),
):
    """
    Guard can annotate inspection record with notes, license plate tag, and threat level.
    """
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    if notes is not None:
        inspection.notes = notes
    if license_plate:
        inspection.license_plate = license_plate.strip().upper()
    if threat_level:
        inspection.threat_level = threat_level

    await db.commit()
    await db.refresh(inspection)

    return {
        "status": "success",
        "inspection_id": inspection.id,
        "license_plate": inspection.license_plate,
        "threat_level": inspection.threat_level,
        "notes": inspection.notes,
    }


@router.get("/export/csv")
async def export_audit_csv(
    db: AsyncSession = Depends(get_db),
    current_user: Guard = Depends(get_current_user),
):
    """
    Export security inspection audit trail as a downloadable CSV report.
    """
    import io
    import csv

    result = await db.execute(select(Inspection).order_by(Inspection.captured_at.desc()))
    inspections = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Inspection ID", "Captured At", "Guard ID", "Bot ID", "License Plate",
        "Decision", "Model Prediction", "Confidence %", "Threat Level", "Notes"
    ])

    for insp in inspections:
        conf_pct = round((insp.model_confidence or 0.0) * 100, 1) if insp.model_confidence else "N/A"
        writer.writerow([
            insp.id,
            insp.captured_at.strftime("%Y-%m-%d %H:%M:%S") if insp.captured_at else "",
            insp.guard_id or "N/A",
            insp.bot_id,
            insp.license_plate or "UNTAGGED",
            insp.decision.upper(),
            insp.model_prediction or "N/A",
            conf_pct,
            (insp.threat_level or "normal").upper(),
            insp.notes or ""
        ])

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="undercarriage_audit_log.csv"'}
    )
