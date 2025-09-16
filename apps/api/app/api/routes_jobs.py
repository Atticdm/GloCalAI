from __future__ import annotations

import asyncio
import contextlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from glocal_shared_schemas import JobCreate, JobOption, LocalizationVariant
from glocal_shared_schemas import LocalizationJob as JobSchema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.db.session import get_db
from app.deps.auth import get_current_user, get_user_from_request
from app.models.entities import (
    AppUser,
    Asset,
    LocalizationJob,
    LocalizedVariant,
    Project,
    VoiceProfile,
)
from app.services.rabbitmq import publish_event
from app.services.redis import subscribe

router = APIRouter()


async def _job_to_schema(job: LocalizationJob) -> JobSchema:
    return JobSchema(
        id=job.id,
        project_id=job.project_id,
        status=job.status,
        source_asset_id=job.source_asset_id,
        languages=list(job.languages or []),
        voice_profile_id=job.voice_profile_id,
        options=job.options,
        created_by=job.created_by,
        created_at=job.created_at,
        updated_at=job.updated_at,
        error_message=job.error_message,
        variants=[
            LocalizationVariant(
                id=variant.id,
                job_id=variant.job_id,
                lang=variant.lang,
                status=variant.status,
                video_url=variant.video_url,
                audio_url=variant.audio_url,
                subs_url=variant.subs_url,
                preview_url=variant.preview_url,
                report=variant.report,
                error_message=variant.error_message,
                created_at=variant.created_at,
                updated_at=variant.updated_at,
            )
            for variant in job.variants
        ],
    )


@router.post("", response_model=JobSchema, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    user: AppUser = Depends(get_current_user),
) -> JobSchema:
    project = await db.scalar(
        select(Project).where(
            Project.id == payload.projectId,
            Project.owner_id == user.id,
        )
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    asset = await db.scalar(
        select(Asset).where(
            Asset.id == payload.sourceAssetId,
            Asset.project_id == project.id,
        )
    )
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    if payload.voiceProfileId:
        profile = await db.scalar(
            select(VoiceProfile).where(VoiceProfile.id == payload.voiceProfileId)
        )
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Voice profile not found",
            )

    job_id = str(uuid.uuid4())
    job = LocalizationJob(
        id=job_id,
        project_id=project.id,
        status="queued",
        source_asset_id=asset.id,
        languages=payload.languages,
        voice_profile_id=payload.voiceProfileId,
        options=(
            payload.options.model_dump()
            if isinstance(payload.options, JobOption)
            else payload.options
        ),
        created_by=user.id,
    )
    db.add(job)
    for lang in payload.languages:
        variant = LocalizedVariant(
            id=str(uuid.uuid4()),
            job_id=job_id,
            lang=lang,
            status="queued",
        )
        db.add(variant)
    await db.commit()

    result = await db.execute(
        select(LocalizationJob)
        .options(selectinload(LocalizationJob.variants))
        .where(LocalizationJob.id == job_id)
    )
    job = result.scalar_one()

    await publish_event(
        "job.created",
        {
            "job_id": job.id,
            "project_id": project.id,
            "languages": payload.languages,
            "voice_profile_id": payload.voiceProfileId,
            "options": job.options,
            "source_asset": {
                "id": asset.id,
                "s3_url": asset.s3_url,
                "type": asset.type,
            },
        },
    )
    return await _job_to_schema(job)


@router.get("/{job_id}", response_model=JobSchema)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: AppUser = Depends(get_current_user),
) -> JobSchema:
    result = await db.execute(
        select(LocalizationJob)
        .options(selectinload(LocalizationJob.variants))
        .where(LocalizationJob.id == job_id)
        .join(Project)
        .where(Project.owner_id == user.id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return await _job_to_schema(job)


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: str,
    request: Request,
    _: AppUser = Depends(get_user_from_request),
) -> EventSourceResponse:
    channel = f"job:{job_id}"

    async def merged_generator():
        queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
        timeout_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        async def reader():
            async for message in subscribe(channel):
                await queue.put(("update", message))
            await queue.put(("close", ""))

        reader_task = asyncio.create_task(reader())
        try:
            last_keep_alive = datetime.now(timezone.utc)
            while True:
                if await request.is_disconnected():
                    break
                if datetime.now(timezone.utc) > timeout_at:
                    await queue.put(("close", ""))
                try:
                    event, payload = await asyncio.wait_for(queue.get(), timeout=1.0)
                    if event == "close":
                        break
                    if event == "update":
                        yield {"event": "update", "data": payload}
                    last_keep_alive = datetime.now(timezone.utc)
                except asyncio.TimeoutError:
                    now = datetime.now(timezone.utc)
                    if (now - last_keep_alive).total_seconds() >= 15:
                        last_keep_alive = now
                        yield {"event": "keep-alive", "data": json.dumps({"ts": now.isoformat()})}
        finally:
            reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reader_task

    return EventSourceResponse(merged_generator())
