"""
Inspection Business Logic Service
===================================
Handles inspection lifecycle: create, decide, query.
"""

import base64
import hashlib
import logging
from datetime import datetime
from typing import Optional

import aiofiles
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.inspections.models import Inspection, Guard
from app.inspections.schemas import InspectionDecision, InspectionResponse, InspectionListResponse
from app.storage.base import get_storage

logger = logging.getLogger(__name__)


class InspectionService:
    """Business logic for inspection CRUD and decision workflow."""

    @staticmethod
    async def create_inspection(
        db: AsyncSession,
        image_data: bytes,
        bot_id: str,
        timestamp: float,
        sha256: str,
        filename: str,
        model_prediction: Optional[str] = None,
        model_confidence: Optional[float] = None,
        model_version: Optional[int] = None,
    ) -> Inspection:
        """
        Create a new pending inspection from an incoming image.
        Saves the image locally for immediate access.
        """
        settings = get_settings()

        # Verify SHA-256 integrity
        computed_hash = hashlib.sha256(image_data).hexdigest()
        if computed_hash != sha256:
            logger.warning(
                "SHA-256 mismatch for %s: expected=%s, got=%s",
                filename, sha256, computed_hash,
            )
            # Continue anyway — log but don't reject

        # Save image locally
        local_path = f"{settings.storage_local_path}/pending/{filename}"
        import os
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        async with aiofiles.open(local_path, "wb") as f:
            await f.write(image_data)

        # Create DB record
        inspection = Inspection(
            bot_id=bot_id,
            image_local_path=local_path,
            decision="pending",
            model_prediction=model_prediction,
            model_confidence=model_confidence,
            model_version=model_version,
            captured_at=datetime.utcfromtimestamp(timestamp),
        )
        db.add(inspection)
        await db.commit()
        await db.refresh(inspection)

        logger.info("Created inspection %s from bot %s", inspection.id, bot_id)
        return inspection

    @staticmethod
    async def submit_decision(
        db: AsyncSession,
        inspection_id: str,
        guard: Guard,
        decision: InspectionDecision,
    ) -> Inspection:
        """
        Submit a guard's decision for an inspection.
        If approved, uploads the image to cloud storage.
        """
        result = await db.execute(
            select(Inspection).where(Inspection.id == inspection_id)
        )
        inspection = result.scalar_one_or_none()

        if not inspection:
            raise ValueError(f"Inspection {inspection_id} not found.")

        if inspection.decision != "pending":
            raise ValueError(
                f"Inspection {inspection_id} already decided: {inspection.decision}"
            )

        # Update decision
        inspection.decision = decision.decision
        inspection.guard_id = guard.id
        inspection.decided_at = datetime.utcnow()
        if decision.vehicle_id:
            inspection.vehicle_id = decision.vehicle_id
        if decision.notes:
            inspection.metadata_json = {
                **(inspection.metadata_json or {}),
                "notes": decision.notes,
            }

        # If approved, upload to cloud storage
        if decision.decision == "approved" and inspection.image_local_path:
            try:
                storage = get_storage()
                async with aiofiles.open(inspection.image_local_path, "rb") as f:
                    image_data = await f.read()

                cloud_key = f"approved/{inspection.bot_id}/{inspection.id}.jpg"
                cloud_url = await storage.upload(cloud_key, image_data, "image/jpeg")
                inspection.image_cloud_url = cloud_url
                logger.info("Uploaded approved image to cloud: %s", cloud_url)

            except Exception as e:
                logger.error("Cloud upload failed for %s: %s", inspection_id, e)
                # Don't fail the decision — image is still local

        await db.commit()
        await db.refresh(inspection)

        logger.info(
            "Inspection %s decided: %s by guard %s",
            inspection_id, decision.decision, guard.username,
        )
        return inspection

    @staticmethod
    async def get_inspection(
        db: AsyncSession, inspection_id: str
    ) -> Optional[Inspection]:
        """Get a single inspection by ID."""
        result = await db.execute(
            select(Inspection)
            .options(selectinload(Inspection.guard))
            .where(Inspection.id == inspection_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_inspections(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        decision_filter: Optional[str] = None,
        bot_id: Optional[str] = None,
    ) -> InspectionListResponse:
        """List inspections with pagination and optional filtering."""
        query = select(Inspection).options(selectinload(Inspection.guard))

        if decision_filter:
            query = query.where(Inspection.decision == decision_filter)
        if bot_id:
            query = query.where(Inspection.bot_id == bot_id)

        # Count total
        count_query = select(func.count(Inspection.id))
        if decision_filter:
            count_query = count_query.where(Inspection.decision == decision_filter)
        if bot_id:
            count_query = count_query.where(Inspection.bot_id == bot_id)
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Paginate
        query = query.order_by(desc(Inspection.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        inspections = result.scalars().all()

        return InspectionListResponse(
            inspections=[InspectionResponse.model_validate(i) for i in inspections],
            total=total,
            page=page,
            page_size=page_size,
        )

    @staticmethod
    async def get_image_base64(inspection: Inspection) -> Optional[str]:
        """Load an inspection's image and return as base64 string."""
        if not inspection.image_local_path:
            return None
        try:
            async with aiofiles.open(inspection.image_local_path, "rb") as f:
                data = await f.read()
            return base64.b64encode(data).decode("utf-8")
        except FileNotFoundError:
            logger.warning("Image file not found: %s", inspection.image_local_path)
            return None
