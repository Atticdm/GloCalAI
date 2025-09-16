from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.deps.auth import get_user_from_request
from app.models.entities import AppUser, LocalizationJob, LocalizedVariant
from app.services.storage import storage_service

router = APIRouter()


def _ensure_owner(variant: LocalizedVariant, user: AppUser) -> None:
    job = variant.job
    if job is None or job.project.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _key_from_url(url: str) -> str:
    if url.startswith("s3://"):
        return url.split("/", 3)[-1]
    parsed = urlparse(url)
    path = parsed.path.lstrip("/")
    if path.startswith("glocal-media/"):
        return path.split("/", 1)[-1]
    return path


@router.get("/{variant_id}/preview")
async def preview_variant(
    variant_id: str,
    db: AsyncSession = Depends(get_db),
    user: AppUser = Depends(get_user_from_request),
):
    result = await db.execute(
        select(LocalizedVariant)
        .where(LocalizedVariant.id == variant_id)
        .options(selectinload(LocalizedVariant.job).selectinload(LocalizationJob.project))
    )
    variant = result.scalar_one_or_none()
    if variant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
    if variant.job is None or variant.job.project.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if not variant.preview_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview not ready")
    key = _key_from_url(variant.preview_url)
    url = storage_service.presign_get_object(key, expires=600)
    return RedirectResponse(url)


@router.get("/{variant_id}/download")
async def download_variant(
    variant_id: str,
    db: AsyncSession = Depends(get_db),
    user: AppUser = Depends(get_user_from_request),
):
    result = await db.execute(
        select(LocalizedVariant)
        .where(LocalizedVariant.id == variant_id)
        .options(selectinload(LocalizedVariant.job).selectinload(LocalizationJob.project))
    )
    variant = result.scalar_one_or_none()
    if variant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
    if variant.job is None or variant.job.project.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    response_data: dict[str, str | None] = {"mp4": None, "srt": None}
    if variant.video_url:
        response_data["mp4"] = storage_service.presign_get_object(
            _key_from_url(variant.video_url),
            expires=600,
        )
    if variant.subs_url:
        response_data["srt"] = storage_service.presign_get_object(
            _key_from_url(variant.subs_url),
            expires=600,
        )
    return JSONResponse(response_data)
