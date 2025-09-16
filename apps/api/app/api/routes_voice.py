from __future__ import annotations

from fastapi import APIRouter, Depends
from glocal_shared_schemas import VoiceProfile as VoiceProfileSchema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps.auth import get_current_user
from app.models.entities import AppUser, VoiceProfile

router = APIRouter()


@router.get("", response_model=list[VoiceProfileSchema])
async def list_voice_profiles(
    db: AsyncSession = Depends(get_db), user: AppUser = Depends(get_current_user)
) -> list[VoiceProfileSchema]:
    result = await db.execute(select(VoiceProfile))
    profiles = result.scalars().all()
    return [
        VoiceProfileSchema(
            id=profile.id,
            name=profile.name,
            provider=profile.provider,
            provider_params=profile.provider_params,
        )
        for profile in profiles
    ]
