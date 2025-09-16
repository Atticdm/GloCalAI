from __future__ import annotations

import asyncio
import json
import math
import shutil
import struct
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any, Dict

from glocal_service_kit import database, job_stage_key, publish_job_event, rabbitmq, storage


async def probe_media(path: Path) -> Dict[str, float]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,bit_rate",
        "-of",
        "json",
        str(path),
    ]
    result = await asyncio.to_thread(
        subprocess.run,
        cmd,
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0.0))
    bitrate = float(fmt.get("bit_rate", 0.0))
    return {"duration": duration, "bitrate": bitrate}


def analyze_audio(path: Path) -> Dict[str, float]:
    if not path.exists():
        return {"average_loudness": -30.0, "silence_seconds": 0.0}
    with wave.open(str(path), "rb") as wf:
        frame_count = wf.getnframes()
        sample_rate = wf.getframerate()
        raw = wf.readframes(frame_count)
        samples = struct.iter_unpack("<h", raw)
        total = 0
        silence = 0
        threshold = 500
        for sample in samples:
            value = abs(sample[0])
            total += value**2
            if value < threshold:
                silence += 1
        if frame_count == 0:
            return {"average_loudness": -30.0, "silence_seconds": 0.0}
        rms = math.sqrt(total / frame_count) / 32767.0
        loudness = 20 * math.log10(rms + 1e-6)
        silence_seconds = silence / sample_rate
        return {
            "average_loudness": round(loudness, 2),
            "silence_seconds": round(silence_seconds, 2),
        }


async def handle_message(message: Dict[str, Any]) -> None:
    job_id = message["job_id"]
    variant_id = message["variant_id"]
    lang = message["lang"]
    await database.connect()
    await publish_job_event(job_id, "qc", "processing", lang, progress=0.2)
    temp_dir = Path(tempfile.mkdtemp(prefix="qc-"))
    try:
        variant = await database.fetch_variant(variant_id)
        if variant is None:
            raise RuntimeError("Variant not found")
        video_key = job_stage_key(job_id, lang, "textinframe", "out.mp4")
        if not await storage.object_exists(video_key):
            video_key = job_stage_key(job_id, lang, "mix", "out.mp4")
        video_path = temp_dir / "final.mp4"
        await storage.download_file(video_key, video_path)
        metrics = await probe_media(video_path)
        audio_path = temp_dir / "audio.wav"
        audio_key = job_stage_key(job_id, lang, "tts", "track.wav")
        if variant.get("audio_url"):
            await storage.download_file(audio_key, audio_path)
        audio_metrics = analyze_audio(audio_path)
        report = {
            "duration": round(metrics["duration"], 2),
            "bitrate_kbps": round(metrics["bitrate"] / 1000.0, 2) if metrics["bitrate"] else 0.0,
            **audio_metrics,
            "has_subtitles": bool(variant.get("subs_url")),
            "lang": lang,
        }
        report_key = job_stage_key(job_id, lang, "qc", "report.json")
        await storage.upload_bytes(
            json.dumps(report, indent=2).encode("utf-8"),
            report_key,
            "application/json",
        )
        await database.update_variant(variant_id, report=report)
        await publish_job_event(job_id, "qc", "processing", lang, progress=0.95)
        await rabbitmq.publish(
            "stage.qc.completed",
            {
                "job_id": job_id,
                "variant_id": variant_id,
                "lang": lang,
                "stage": "qc",
                "status": "completed",
                "report_key": report_key,
            },
        )
    except Exception as exc:  # pragma: no cover
        await publish_job_event(job_id, "qc", "error", lang, message=str(exc))
        await rabbitmq.publish(
            "stage.qc.failed",
            {
                "job_id": job_id,
                "variant_id": variant_id,
                "lang": lang,
                "stage": "qc",
                "status": "error",
                "error": str(exc),
            },
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def main() -> None:
    await database.connect()
    await rabbitmq.declare_queue("qc-agent", "stage.qc")
    await rabbitmq.consume("qc-agent", handle_message)


if __name__ == "__main__":
    asyncio.run(main())
