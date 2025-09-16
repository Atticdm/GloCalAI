from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from glocal_service_kit import database, job_stage_key, publish_job_event, rabbitmq, storage


def transform_text(text: str, lang: str, index: int) -> str:
    styled = text.upper() if index % 2 == 0 else text.lower()
    return f"{styled} [{lang}]"


async def handle_message(message: Dict[str, Any]) -> None:
    job_id = message["job_id"]
    variant_id = message["variant_id"]
    lang = message["lang"]
    base_prefix = message["base_prefix"]
    await database.connect()
    await publish_job_event(job_id, "translate", "processing", lang, progress=0.2)
    temp_dir = Path(tempfile.mkdtemp(prefix="translate-"))
    try:
        segments_path = temp_dir / "segments.json"
        await storage.download_file(
            job_stage_key(job_id, lang, "asr", "segments.json"),
            segments_path,
        )
        data: List[Dict[str, Any]] = json.loads(segments_path.read_text())
        translated: List[Dict[str, Any]] = []
        for idx, segment in enumerate(data):
            translated.append(
                {
                    **segment,
                    "text": transform_text(segment["text"], lang, idx),
                    "lang": lang,
                }
            )
        translated_json = json.dumps(translated, indent=2)
        await storage.upload_bytes(
            translated_json.encode("utf-8"),
            job_stage_key(job_id, lang, "translate", "segments.json"),
            "application/json",
        )
        await publish_job_event(job_id, "translate", "processing", lang, progress=0.85)
        await rabbitmq.publish(
            "stage.translate.completed",
            {
                "job_id": job_id,
                "variant_id": variant_id,
                "lang": lang,
                "stage": "translate",
                "status": "completed",
                "base_prefix": base_prefix,
            },
        )
    except Exception as exc:  # pragma: no cover
        await publish_job_event(job_id, "translate", "error", lang, message=str(exc))
        await rabbitmq.publish(
            "stage.translate.failed",
            {
                "job_id": job_id,
                "variant_id": variant_id,
                "lang": lang,
                "stage": "translate",
                "status": "error",
                "error": str(exc),
            },
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def main() -> None:
    await database.connect()
    await rabbitmq.declare_queue("translate-agent", "stage.translate")
    await rabbitmq.consume("translate-agent", handle_message)


if __name__ == "__main__":
    asyncio.run(main())
