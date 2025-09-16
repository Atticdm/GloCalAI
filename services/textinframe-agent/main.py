from __future__ import annotations

import asyncio
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

from glocal_service_kit import database, job_stage_key, publish_job_event, rabbitmq, storage

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


async def run_ffmpeg(cmd: list[str]) -> None:
    await asyncio.to_thread(subprocess.run, cmd, check=True)


async def handle_message(message: Dict[str, Any]) -> None:
    job_id = message["job_id"]
    variant_id = message["variant_id"]
    lang = message["lang"]
    await database.connect()
    await publish_job_event(job_id, "textinframe", "processing", lang, progress=0.15)
    temp_dir = Path(tempfile.mkdtemp(prefix="textinframe-"))
    try:
        mix_key = job_stage_key(job_id, lang, "mix", "out.mp4")
        mix_path = temp_dir / "mix.mp4"
        await storage.download_file(mix_key, mix_path)
        overlay_path = temp_dir / "overlay.mp4"
        text_value = f"[Localized TEXT {lang}]"
        drawtext = (
            f"drawtext=fontfile={FONT_PATH}:text='{text_value}':"
            "fontcolor=white:fontsize=48:x=40:y=40:box=1:boxcolor=black@0.45"
        )
        await run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(mix_path),
                "-vf",
                drawtext,
                "-c:a",
                "copy",
                str(overlay_path),
            ]
        )
        hls_dir = temp_dir / "hls"
        hls_dir.mkdir(exist_ok=True)
        await run_ffmpeg(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(overlay_path),
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
        video_key = job_stage_key(job_id, lang, "textinframe", "out.mp4")
        preview_key = job_stage_key(job_id, lang, "textinframe", "hls", "index.m3u8")
        await storage.upload_file(overlay_path, video_key, "video/mp4")
        for segment in hls_dir.glob("*"):
            content_type = "application/x-mpegURL" if segment.suffix == ".m3u8" else "video/mp2t"
            await storage.upload_file(
                segment,
                job_stage_key(job_id, lang, "textinframe", "hls", segment.name),
                content_type,
            )
        await database.update_variant(
            variant_id,
            video_url=f"s3://{storage.bucket}/{video_key}",
            preview_url=f"s3://{storage.bucket}/{preview_key}",
        )
        await publish_job_event(job_id, "textinframe", "processing", lang, progress=0.85)
        await rabbitmq.publish(
            "stage.textinframe.completed",
            {
                "job_id": job_id,
                "variant_id": variant_id,
                "lang": lang,
                "stage": "textinframe",
                "status": "completed",
                "video_key": video_key,
                "preview_key": preview_key,
                "beta": True,
            },
        )
    except Exception as exc:  # pragma: no cover
        await publish_job_event(job_id, "textinframe", "error", lang, message=str(exc))
        await rabbitmq.publish(
            "stage.textinframe.failed",
            {
                "job_id": job_id,
                "variant_id": variant_id,
                "lang": lang,
                "stage": "textinframe",
                "status": "error",
                "error": str(exc),
            },
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def main() -> None:
    await database.connect()
    await rabbitmq.declare_queue("textinframe-agent", "stage.textinframe")
    await rabbitmq.consume("textinframe-agent", handle_message)


if __name__ == "__main__":
    asyncio.run(main())
