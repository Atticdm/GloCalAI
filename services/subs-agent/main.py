from __future__ import annotations

import json
import math
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from glocal_service_kit import database, job_stage_key, publish_job_event, rabbitmq, storage


def format_ts(seconds: float, sep: str = ",") -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, sec = divmod(remainder, 60)
    millis = int((sec - math.floor(sec)) * 1000)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(sec):02d}{sep}{millis:03d}"


def to_srt(segments: List[Dict[str, Any]]) -> str:
    blocks: List[str] = []
    for idx, seg in enumerate(segments, start=1):
        blocks.append(str(idx))
        blocks.append(f"{format_ts(float(seg['start']))} --> {format_ts(float(seg['end']))}")
        blocks.append(seg["text"])
        blocks.append("")
    return "\n".join(blocks)


def to_vtt(segments: List[Dict[str, Any]]) -> str:
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = format_ts(float(seg["start"]), ".")
        end = format_ts(float(seg["end"]), ".")
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")
    return "\n".join(lines)


async def handle_message(message: Dict[str, Any]) -> None:
    job_id = message["job_id"]
    variant_id = message["variant_id"]
    lang = message["lang"]
    base_prefix = message["base_prefix"]
    await database.connect()
    await publish_job_event(job_id, "subs", "processing", lang, progress=0.2)
    temp_dir = Path(tempfile.mkdtemp(prefix="subs-"))
    try:
        segments_path = temp_dir / "translate_segments.json"
        await storage.download_file(
            job_stage_key(job_id, lang, "translate", "segments.json"),
            segments_path,
        )
        segments: List[Dict[str, Any]] = json.loads(segments_path.read_text())
        srt_content = to_srt(segments)
        vtt_content = to_vtt(segments)
        srt_key = job_stage_key(job_id, lang, "subs", "subtitles.srt")
        vtt_key = job_stage_key(job_id, lang, "subs", "subtitles.vtt")
        await storage.upload_bytes(
            srt_content.encode("utf-8"),
            srt_key,
            "application/x-subrip",
        )
        await storage.upload_bytes(
            vtt_content.encode("utf-8"),
            vtt_key,
            "text/vtt",
        )
        await database.update_variant(variant_id, subs_url=f"s3://{storage.bucket}/{srt_key}")
        await publish_job_event(job_id, "subs", "processing", lang, progress=0.9)
        await rabbitmq.publish(
            "stage.subs.completed",
            {
                "job_id": job_id,
                "variant_id": variant_id,
                "lang": lang,
                "stage": "subs",
                "status": "completed",
                "base_prefix": base_prefix,
            },
        )
    except Exception as exc:  # pragma: no cover
        await publish_job_event(job_id, "subs", "error", lang, message=str(exc))
        await rabbitmq.publish(
            "stage.subs.failed",
            {
                "job_id": job_id,
                "variant_id": variant_id,
                "lang": lang,
                "stage": "subs",
                "status": "error",
                "error": str(exc),
            },
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def main() -> None:
    await database.connect()
    await rabbitmq.declare_queue("subs-agent", "stage.subs")
    await rabbitmq.consume("subs-agent", handle_message)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
