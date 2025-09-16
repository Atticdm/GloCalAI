from __future__ import annotations

from pathlib import Path


def job_stage_key(job_id: str, lang: str, *parts: str) -> str:
    return str(Path("jobs") / job_id / lang / Path(*parts))


def job_stage_local(job_id: str, lang: str, *parts: str, base: Path) -> Path:
    return base / job_id / lang / Path(*parts)
