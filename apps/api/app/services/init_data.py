from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AppUser, Project, VoiceProfile
from app.utils.security import hash_password


async def ensure_initial_data(db: AsyncSession) -> None:
    admin_email = "admin@glocal.ai"
    result = await db.execute(select(AppUser).where(AppUser.email == admin_email))
    admin = result.scalar_one_or_none()
    if admin is None:
        admin = AppUser(
            id=str(uuid.uuid4()),
            email=admin_email,
            password_hash=hash_password("admin12345"),
            role="admin",
        )
        db.add(admin)
        await db.flush()

    profile_result = await db.execute(select(VoiceProfile))
    profiles = profile_result.scalars().all()
    if not profiles:
        female = VoiceProfile(
            id=str(uuid.uuid4()),
            name="Female 25-35",
            provider="xtts",
            provider_params={"gender": "female", "age_range": "25-35", "style": "bright"},
        )
        male = VoiceProfile(
            id=str(uuid.uuid4()),
            name="Male 25-35",
            provider="xtts",
            provider_params={"gender": "male", "age_range": "25-35", "style": "bright"},
        )
        db.add_all([female, male])

    project_result = await db.execute(select(Project).where(Project.name == "Demo Project"))
    project = project_result.scalar_one_or_none()
    if project is None:
        db.add(
            Project(
                id=str(uuid.uuid4()),
                owner_id=admin.id,
                name="Demo Project",
            )
        )

    await db.commit()
