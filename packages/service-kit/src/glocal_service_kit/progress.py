from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from redis.asyncio import Redis

from glocal_service_kit.config import get_settings

_settings = get_settings()
_redis: Redis | None = None
_lock = asyncio.Lock()


async def _get_redis() -> Redis:
    global _redis
    if _redis is None:
        async with _lock:
            if _redis is None:
                _redis = Redis.from_url(_settings.redis_url, decode_responses=True)
    assert _redis
    return _redis


async def publish_job_event(
    job_id: str,
    stage: str,
    status: str,
    lang: str | None = None,
    progress: float = 0.0,
    message: str | None = None,
) -> None:
    redis = await _get_redis()
    payload = {
        "job_id": job_id,
        "stage": stage,
        "status": status,
        "lang": lang,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await redis.publish(f"job:{job_id}", json.dumps(payload))
