from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

from glocal_service_kit import database, job_stage_key, publish_job_event, rabbitmq, storage


async def run_ffmpeg(command: list[str]) -> None:
    await asyncio.to_thread(
        subprocess.run,
        command,
        check=True,
    )


async def handle_message(message: Dict[str, Any]) -> None:
    job_id = message["job_id"]
    variant_id = message["variant_id"]
    lang = message["lang"]
    base_prefix = message["base_prefix"]
    expect_tts = message.get("expect_tts", True)
    await database.connect()
    await publish_job_event(job_id, "mix", "processing", lang, progress=0.1)
    temp_dir = Path(tempfile.mkdtemp(prefix="mix-"))
    try:
        source_path = temp_dir / "source.mp4"
        await storage.download_file(message["source"]["key"], source_path)
        tts_key = job_stage_key(job_id, lang, "tts", "track.wav")
        tts_path = temp_dir / "track.wav"
        has_tts = expect_tts
        if expect_tts:
            await storage.download_file(tts_key, tts_path)
        else:
            has_tts = False
        output_mp4 = temp_dir / "out.mp4"
        if has_tts and tts_path.exists():
            await run_ffmpeg(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(source_path),
                    "-i",
                    str(tts_path),
                    "-map",
                    "0:v",
                    "-map",
                    "1:a",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "21",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-shortest",
                    str(output_mp4),
                ]
            )
        else:
            await run_ffmpeg(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(source_path),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    str(output_mp4),
                ]
            )
        hls_dir = temp_dir / "hls"
        hls_dir.mkdir(exist_ok=True)
        await run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(output_mp4),
                "-codec:v",
                "libx264",
                "-codec:a",
                "aac",
                "-start_number",
                "0",
                "-hls_time",
                "2",
                "-hls_list_size",
                "0",
                "-hls_segment_filename",
                str(hls_dir / "segment_%03d.ts"),
                str(hls_dir / "index.m3u8"),
            ]
        )
        video_key = job_stage_key(job_id, lang, "mix", "out.mp4")
        preview_key = job_stage_key(job_id, lang, "mix", "hls", "index.m3u8")
        await storage.upload_file(output_mp4, video_key, "video/mp4")
        for segment in hls_dir.glob("*"):
            content_type = "application/x-mpegURL" if segment.suffix == ".m3u8" else "video/mp2t"
            await storage.upload_file(
                segment,
                job_stage_key(job_id, lang, "mix", "hls", segment.name),
                content_type,
            )
        await database.update_variant(
            variant_id,
            video_url=f"s3://{storage.bucket}/{video_key}",
            preview_url=f"s3://{storage.bucket}/{preview_key}",
        )
        await publish_job_event(job_id, "mix", "processing", lang, progress=0.9)
        await rabbitmq.publish(
            "stage.mix.completed",
            {
                "job_id": job_id,
                "variant_id": variant_id,
                "lang": lang,
                "stage": "mix",
                "status": "completed",
                "base_prefix": base_prefix,
                "video_key": video_key,
                "preview_key": preview_key,
            },
        )
    except Exception as exc:  # pragma: no cover
        await publish_job_event(job_id, "mix", "error", lang, message=str(exc))
        await rabbitmq.publish(
            "stage.mix.failed",
            {
                "job_id": job_id,
                "variant_id": variant_id,
                "lang": lang,
                "stage": "mix",
                "status": "error",
                "error": str(exc),
            },
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def main() -> None:
    await database.connect()
    await rabbitmq.declare_queue("mix-agent", "stage.mix")
    await rabbitmq.consume("mix-agent", handle_message)


if __name__ == "__main__":
    asyncio.run(main())
