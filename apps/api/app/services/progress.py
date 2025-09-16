from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from app.services.redis import publish


async def publish_progress(
    job_id: str,
    stage: str,
    status: str,
    lang: Optional[str] = None,
    progress: float = 0.0,
    message: str | None = None,
) -> None:
    payload = {
        "job_id": job_id,
        "stage": stage,
        "lang": lang,
        "status": status,
        "progress": progress,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await publish(f"job:{job_id}", json.dumps(payload))
