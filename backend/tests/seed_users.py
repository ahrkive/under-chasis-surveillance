"""
User Seeding Script
====================
Ensures both 'creator' and 'guard' accounts are created in the database.
"""

import sys
sys.path.insert(0, ".")
import asyncio
from sqlalchemy import select
from app.database import get_session_factory, create_tables
from app.inspections.models import Guard
from app.auth.service import hash_password


async def seed():
    await create_tables()
    factory = get_session_factory()
    async with factory() as db:
        for username, password, full_name, role in [
            ("creator", "creator123", "Lead System Creator", "admin"),
            ("guard", "guard123", "Security Guard Alpha", "guard"),
            ("admin", "admin123", "System Administrator", "admin"),
        ]:
            res = await db.execute(select(Guard).where(Guard.username == username))
            existing = res.scalar_one_or_none()
            if not existing:
                user = Guard(
                    username=username,
                    password_hash=hash_password(password),
                    full_name=full_name,
                    role=role,
                )
                db.add(user)
                print(f"[OK] Seeded account: {username} ({role})")
        await db.commit()
    print("[OK] Seeding finished!")


if __name__ == "__main__":
    asyncio.run(seed())
