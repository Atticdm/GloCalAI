from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps.auth import get_current_user
from app.models.entities import AppUser, LocalizationJob, LocalizedVariant, Project

router = APIRouter()


@router.post("/upload")
async def upload_youtube(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: AppUser = Depends(get_current_user),
) -> dict[str, str]:
    variant_id = payload.get("variantId")
    if not variant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="variantId required")
    result = await db.execute(
        select(LocalizedVariant)
        .where(LocalizedVariant.id == variant_id)
        .join(LocalizationJob)
        .join(Project)
        .where(Project.owner_id == user.id)
    )
    variant = result.scalar_one_or_none()
    if variant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
    youtube_url = f"https://youtu.be/demo_{variant.id}"
    print(f"[youtube] upload request variant={variant.id} payload={json.dumps(payload)}")
    return {"youtube_url": youtube_url}
