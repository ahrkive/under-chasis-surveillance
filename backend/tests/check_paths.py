import sys
sys.path.insert(0, ".")
import asyncio
from app.database import get_session_factory
from app.inspections.models import Inspection
from sqlalchemy import select

async def main():
    factory = get_session_factory()
    async with factory() as db:
        res = await db.execute(select(Inspection))
        for row in res.scalars().all():
            print(f"ID: {row.id} | Decision: {row.decision} | Path: {row.image_local_path}")

if __name__ == "__main__":
    asyncio.run(main())
