from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from glocal_shared_schemas import UploadAssetComplete, UploadAssetUrlRequest, UploadAssetUrlResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps.auth import get_current_user
from app.models.entities import AppUser, Asset, Project
from app.services.storage import storage_service

router = APIRouter()


def _sanitize_filename(filename: str) -> str:
    path = Path(filename)
    cleaned = path.name.replace(" ", "_")
    if not cleaned:
        return "upload.bin"
    return cleaned


@router.post("/upload-url", response_model=UploadAssetUrlResponse)
async def create_upload_url(
    payload: UploadAssetUrlRequest,
    db: AsyncSession = Depends(get_db),
    user: AppUser = Depends(get_current_user),
) -> UploadAssetUrlResponse:
    project = await db.scalar(
        select(Project).where(
            Project.id == payload.projectId,
            Project.owner_id == user.id,
        )
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    asset_id = str(uuid.uuid4())
    filename = _sanitize_filename(payload.filename)
    object_key = f"raw/{payload.projectId}/{asset_id}/{filename}"
    presigned = storage_service.presign_put_object(object_key, payload.mime)
    return UploadAssetUrlResponse(asset_id=asset_id, **presigned)


@router.post("/complete", status_code=status.HTTP_201_CREATED)
async def complete_upload(
    payload: UploadAssetComplete,
    db: AsyncSession = Depends(get_db),
    user: AppUser = Depends(get_current_user),
) -> dict[str, str]:
    project = await db.scalar(
        select(Project).where(
            Project.id == payload.projectId,
            Project.owner_id == user.id,
        )
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    parsed = urlparse(payload.s3_url)
    full_path = parsed.path.lstrip("/")
    try:
        bucket, object_path = full_path.split("/", 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid S3 URL",
        ) from exc
    path_parts = object_path.split("/")
    if len(path_parts) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid S3 key")
    asset_id = path_parts[2]
    asset = Asset(
        id=asset_id,
        project_id=payload.projectId,
        type=payload.type.value if hasattr(payload.type, "value") else str(payload.type),
        s3_url=f"s3://{bucket}/{object_path}",
        meta=payload.meta,
    )
    db.add(asset)
    await db.commit()
    return {"id": asset.id}
