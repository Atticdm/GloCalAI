from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from glocal_service_kit import (
    database,
    parse_s3_url,
    publish_job_event,
    rabbitmq,
)

PIPELINE: List[str] = [
    "asr",
    "translate",
    "tts",
    "mix",
    "subs",
    "textinframe",
    "qc",
]


@dataclass
class JobContext:
    job_id: str
    project_id: str
    source_asset: Dict[str, Any]
    options: Dict[str, Any]
    voice_profile: Optional[Dict[str, Any]]


class Orchestrator:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        await database.connect()
        await rabbitmq.declare_queue("orchestrator.jobs", "job.created")
        await rabbitmq.declare_queue("orchestrator.events", "stage.*.completed")
        await rabbitmq.declare_queue("orchestrator.events", "stage.*.failed")
        consumers = [
            asyncio.create_task(rabbitmq.consume("orchestrator.jobs", self.handle_job_created)),
            asyncio.create_task(rabbitmq.consume("orchestrator.events", self.handle_stage_event)),
        ]
        await asyncio.gather(*consumers)

    async def handle_job_created(self, message: Dict[str, Any]) -> None:
        job_id = message["job_id"]
        job = await database.fetch_job(job_id)
        if job is None:
            return
        await database.update_job_status(job_id, "processing")
        asset = await database.fetch_asset(job["source_asset_id"])
        if asset is None:
            await database.update_job_status(job_id, "error", error="Source asset missing")
            return
        _, source_key = parse_s3_url(asset["s3_url"])
        voice_profile = None
        if job.get("voice_profile_id"):
            voice_profile = await database.fetch_voice_profile(job["voice_profile_id"])
        context = JobContext(
            job_id=job_id,
            project_id=job["project_id"],
            source_asset={"key": source_key, "type": asset["type"]},
            options=job.get("options") or {},
            voice_profile=voice_profile,
        )
        for variant in job["variants"]:
            await database.update_variant(variant["id"], status="processing")
            await publish_job_event(job_id, "asr", "queued", variant["lang"])
            await self.enqueue_stage("asr", context, variant)

    async def handle_stage_event(self, message: Dict[str, Any]) -> None:
        job_id = message.get("job_id")
        variant_id = message.get("variant_id")
        lang = message.get("lang")
        stage = message.get("stage")
        status = message.get("status")
        if not (job_id and variant_id and lang and stage and status):
            return
        if status == "error":
            error_message = message.get("error", "Stage failed")
            await database.update_variant(variant_id, status="error", error_message=error_message)
            await publish_job_event(job_id, stage, "error", lang, message=error_message)
            await database.update_job_status(job_id, "error", error=error_message)
            return
        await publish_job_event(job_id, stage, "done", lang, progress=1.0)
        next_stage = await self.get_next_stage(job_id, stage, lang)
        if next_stage is None:
            await database.update_variant(variant_id, status="done")
            await publish_job_event(job_id, "pack", "done", lang, progress=1.0)
            await self.check_job_completion(job_id)
        else:
            await publish_job_event(job_id, next_stage, "queued", lang)
            await self.enqueue_stage(
                next_stage,
                await self.build_context(job_id),
                await database.fetch_variant(variant_id),
            )

    async def build_context(self, job_id: str) -> JobContext:
        job = await database.fetch_job(job_id)
        if job is None:
            raise RuntimeError(f"Job {job_id} not found")
        asset = await database.fetch_asset(job["source_asset_id"])
        if asset is None:
            raise RuntimeError("Missing asset for job")
        _, source_key = parse_s3_url(asset["s3_url"])
        voice_profile = None
        if job.get("voice_profile_id"):
            voice_profile = await database.fetch_voice_profile(job["voice_profile_id"])
        return JobContext(
            job_id=job_id,
            project_id=job["project_id"],
            source_asset={"key": source_key, "type": asset["type"]},
            options=job.get("options") or {},
            voice_profile=voice_profile,
        )

    async def enqueue_stage(
        self,
        stage: str,
        context: JobContext,
        variant: Dict[str, Any] | None,
    ) -> None:
        if variant is None:
            return
        payload = {
            "job_id": context.job_id,
            "project_id": context.project_id,
            "variant_id": variant["id"],
            "lang": variant["lang"],
            "stage": stage,
            "source": context.source_asset,
            "options": context.options,
            "base_prefix": f"jobs/{context.job_id}/{variant['lang']}",
            "expect_tts": context.options.get("dub", True),
            "voice_profile": context.voice_profile,
        }
        await rabbitmq.publish(f"stage.{stage}", payload)

    async def get_next_stage(self, job_id: str, current_stage: str, lang: str) -> Optional[str]:
        job = await database.fetch_job(job_id)
        if job is None:
            return None
        options = job.get("options") or {}
        if current_stage not in PIPELINE:
            return None
        idx = PIPELINE.index(current_stage)
        for stage in PIPELINE[idx + 1 :]:
            if self.should_skip(stage, options):
                await publish_job_event(job_id, stage, "skipped", lang, progress=1.0)
                continue
            return stage
        return None

    def should_skip(self, stage: str, options: Dict[str, Any]) -> bool:
        if stage == "subs" and not options.get("subs", True):
            return True
        if stage == "textinframe" and not options.get("replace_text_in_frame", False):
            return True
        if stage == "tts" and not options.get("dub", True):
            return True
        return False

    async def check_job_completion(self, job_id: str) -> None:
        job = await database.fetch_job(job_id)
        if job is None:
            return
        statuses = {variant["status"] for variant in job["variants"]}
        if statuses.issubset({"done"}):
            await database.update_job_status(job_id, "done")
            await publish_job_event(job_id, "job", "done", None, progress=1.0)
            options = job.get("options") or {}
            if options.get("upload_to_youtube"):
                for variant in job["variants"]:
                    await rabbitmq.publish(
                        "youtube.upload",
                        {
                            "job_id": job_id,
                            "variant_id": variant["id"],
                            "lang": variant["lang"],
                            "video_url": variant.get("video_url"),
                            "subs_url": variant.get("subs_url"),
                        },
                    )
        elif any(status == "error" for status in statuses):
            await database.update_job_status(job_id, "partial")


async def main() -> None:
    orchestrator = Orchestrator()
    await orchestrator.start()


if __name__ == "__main__":
    asyncio.run(main())
