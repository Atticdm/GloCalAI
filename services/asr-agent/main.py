from __future__ import annotations

import asyncio
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from glocal_service_kit import database, job_stage_key, publish_job_event, rabbitmq, storage

SEGMENT_TEXT = [
    "Welcome to Glocal Ads AI demo.",
    "We localize your creative assets in minutes.",
    "Launch campaigns with authentic multilingual voiceovers.",
]


async def probe_duration(path: Path) -> float:
    result = await asyncio.to_thread(
        subprocess.run,
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 8.0


def build_segments(duration: float) -> List[Dict[str, Any]]:
    count = len(SEGMENT_TEXT)
    chunk = max(duration / count, 1.5)
    segments: List[Dict[str, Any]] = []
    cursor = 0.0
    for idx, text in enumerate(SEGMENT_TEXT):
        start = cursor
        end = min(duration, start + chunk)
        segments.append(
            {
                "id": idx,
                "start": round(start, 3),
                "end": round(end, 3),
                "text": text,
            }
        )
        cursor = end
    return segments


def segments_to_srt(segments: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for idx, seg in enumerate(segments, start=1):
        start = seg["start"]
        end = seg["end"]
        lines.append(str(idx))
        lines.append(f"{format_ts(start)} --> {format_ts(end)}")
        lines.append(seg["text"])
        lines.append("")
    return "\n".join(lines)


def format_ts(value: float) -> str:
    hours, remainder = divmod(value, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - math.floor(seconds)) * 1000)
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{milliseconds:03d}"


async def handle_message(message: Dict[str, Any]) -> None:
    job_id = message["job_id"]
    variant_id = message["variant_id"]
    lang = message["lang"]
    source_key = message["source"]["key"]
    base_prefix = message["base_prefix"]
    await database.connect()
    await publish_job_event(job_id, "asr", "processing", lang, progress=0.2)
    temp_dir = Path(tempfile.mkdtemp(prefix="asr-"))
    try:
        source_path = temp_dir / "source.mp4"
        await storage.download_file(source_key, source_path)
        duration = await probe_duration(source_path)
        segments = build_segments(duration)
        segments_json = json.dumps(segments, indent=2)
        await storage.upload_bytes(
            segments_json.encode("utf-8"),
            job_stage_key(job_id, lang, "asr", "segments.json"),
            "application/json",
        )
        await storage.upload_bytes(
            segments_to_srt(segments).encode("utf-8"),
            job_stage_key(job_id, lang, "asr", "transcript.srt"),
            "application/x-subrip",
        )
        await publish_job_event(job_id, "asr", "processing", lang, progress=0.8)
        await rabbitmq.publish(
            "stage.asr.completed",
            {
                "job_id": job_id,
                "variant_id": variant_id,
                "lang": lang,
                "stage": "asr",
                "status": "completed",
                "base_prefix": base_prefix,
            },
        )
    except Exception as exc:  # pragma: no cover - runtime failure path
        await publish_job_event(job_id, "asr", "error", lang, message=str(exc))
        await rabbitmq.publish(
            "stage.asr.failed",
            {
                "job_id": job_id,
                "variant_id": variant_id,
                "lang": lang,
                "stage": "asr",
                "status": "error",
                "error": str(exc),
            },
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def main() -> None:
    await database.connect()
    await rabbitmq.declare_queue("asr-agent", "stage.asr")
    await rabbitmq.consume("asr-agent", handle_message)


if __name__ == "__main__":
    asyncio.run(main())
