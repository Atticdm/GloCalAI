from __future__ import annotations

import asyncio
from typing import Any, Dict

from glocal_service_kit import publish_job_event, rabbitmq


async def handle_message(message: Dict[str, Any]) -> None:
    job_id = message.get("job_id")
    variant_id = message.get("variant_id")
    lang = message.get("lang")
    url = f"https://youtu.be/demo_{variant_id}" if variant_id else "https://youtu.be/demo"
    print(f"[yt-uploader] simulated upload for job={job_id} variant={variant_id} url={url}")
    if job_id and lang:
        await publish_job_event(job_id, "youtube", "done", lang, message=url)


async def main() -> None:
    await rabbitmq.declare_queue("yt-uploader", "youtube.upload")
    await rabbitmq.consume("yt-uploader", handle_message)


if __name__ == "__main__":
    asyncio.run(main())
