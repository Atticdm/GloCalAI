from __future__ import annotations

import asyncio
import json
import math
import shutil
import struct
import tempfile
import wave
from pathlib import Path
from typing import Any, Dict, List

from glocal_service_kit import database, job_stage_key, publish_job_event, rabbitmq, storage

SAMPLE_RATE = 44100


def sine_wave(frequency: float, duration: float) -> bytes:
    frame_count = int(duration * SAMPLE_RATE)
    buffer = bytearray()
    for n in range(frame_count):
        value = int(32767 * math.sin(2 * math.pi * frequency * n / SAMPLE_RATE))
        buffer.extend(struct.pack("<h", value))
    return bytes(buffer)


def pad_silence(duration: float) -> bytes:
    frame_count = int(duration * SAMPLE_RATE)
    return b"\x00\x00" * frame_count


async def synthesize(segments: List[Dict[str, Any]], target: Path) -> None:
    with wave.open(str(target), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        for index, segment in enumerate(segments):
            seg_duration = max(float(segment["end"]) - float(segment["start"]), 0.4)
            freq = 220.0 + index * 40
            wf.writeframes(sine_wave(freq, seg_duration))
            wf.writeframes(pad_silence(0.1))


async def handle_message(message: Dict[str, Any]) -> None:
    job_id = message["job_id"]
    variant_id = message["variant_id"]
    lang = message["lang"]
    base_prefix = message["base_prefix"]
    await database.connect()
    await publish_job_event(job_id, "tts", "processing", lang, progress=0.25)
    temp_dir = Path(tempfile.mkdtemp(prefix="tts-"))
    try:
        segments_path = temp_dir / "translate_segments.json"
        await storage.download_file(
            job_stage_key(job_id, lang, "translate", "segments.json"),
            segments_path,
        )
        segments: List[Dict[str, Any]] = json.loads(segments_path.read_text())
        audio_path = temp_dir / "track.wav"
        await synthesize(segments, audio_path)
        key = job_stage_key(job_id, lang, "tts", "track.wav")
        await storage.upload_file(audio_path, key, "audio/wav")
        await database.update_variant(
            variant_id,
            audio_url=f"s3://{storage.bucket}/{key}",
        )
        await publish_job_event(job_id, "tts", "processing", lang, progress=0.9)
        await rabbitmq.publish(
            "stage.tts.completed",
            {
                "job_id": job_id,
                "variant_id": variant_id,
                "lang": lang,
                "stage": "tts",
                "status": "completed",
                "base_prefix": base_prefix,
                "audio_key": key,
            },
        )
    except Exception as exc:  # pragma: no cover
        await publish_job_event(job_id, "tts", "error", lang, message=str(exc))
        await rabbitmq.publish(
            "stage.tts.failed",
            {
                "job_id": job_id,
                "variant_id": variant_id,
                "lang": lang,
                "stage": "tts",
                "status": "error",
                "error": str(exc),
            },
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def main() -> None:
    await database.connect()
    await rabbitmq.declare_queue("tts-agent", "stage.tts")
    await rabbitmq.consume("tts-agent", handle_message)


if __name__ == "__main__":
    asyncio.run(main())
