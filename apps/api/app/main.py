from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_assets,
    routes_auth,
    routes_jobs,
    routes_projects,
    routes_variants,
    routes_voice,
    routes_youtube,
)
from app.core.config import settings
from app.db.session import async_session_factory
from app.services import rabbitmq
from app.services.init_data import ensure_initial_data
from app.services.redis import get_redis
from app.services.storage import storage_service

app = FastAPI(title="Glocal Ads AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_auth.router, prefix="/auth", tags=["auth"])
app.include_router(routes_projects.router, prefix="/projects", tags=["projects"])
app.include_router(routes_assets.router, prefix="/assets", tags=["assets"])
app.include_router(routes_jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(routes_variants.router, prefix="/variants", tags=["variants"])
app.include_router(routes_voice.router, prefix="/voice-profiles", tags=["voice"])
app.include_router(routes_youtube.router, prefix="/youtube", tags=["youtube"])


@app.on_event("startup")
async def on_startup() -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, storage_service.ensure_bucket)
    await get_redis().ping()
    async with async_session_factory() as session:
        await ensure_initial_data(session)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    redis = get_redis()
    await redis.close()
    await rabbitmq.close_connection()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
