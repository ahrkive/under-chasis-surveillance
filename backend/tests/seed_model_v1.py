"""
Seed Model Version 1 Record into Database
==========================================
"""

import sys
sys.path.insert(0, ".")
import asyncio
from datetime import datetime
from sqlalchemy import select
from app.database import get_session_factory, create_tables
from app.inspections.models import ModelVersion


async def seed_v1():
    await create_tables()
    factory = get_session_factory()
    async with factory() as db:
        res = await db.execute(select(ModelVersion).where(ModelVersion.version == 1))
        existing = res.scalar_one_or_none()
        if not existing:
            mv = ModelVersion(
                version=1,
                file_path="./models/v001_mobilenetv3.pth",
                training_image_count=3000,
                validation_accuracy=0.990,
                status="active",
                trained_at=datetime.utcnow(),
            )
            db.add(mv)
            await db.commit()
            print("[OK] Model Version 1 (ResNet50 99.0% Val Acc, 3,000 images) registered in Database!")
        else:
            existing.status = "active"
            existing.validation_accuracy = 0.990
            existing.training_image_count = 3000
            await db.commit()
            print("[OK] Model Version 1 updated with 3,000 training images!")


if __name__ == "__main__":
    asyncio.run(seed_v1())
