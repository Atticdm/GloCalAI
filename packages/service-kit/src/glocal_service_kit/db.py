from __future__ import annotations

import json

import asyncpg

from glocal_service_kit.config import get_settings


class Database:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None
        self.settings = get_settings()

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.settings.postgres_dsn)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def fetch_asset(self, asset_id: str) -> dict | None:
        await self.connect()
        assert self._pool
        row = await self._pool.fetchrow("SELECT * FROM asset WHERE id = $1", asset_id)
        return dict(row) if row else None

    async def fetch_voice_profile(self, profile_id: str) -> dict | None:
        await self.connect()
        assert self._pool
        row = await self._pool.fetchrow("SELECT * FROM voice_profile WHERE id = $1", profile_id)
        return dict(row) if row else None

    async def fetch_variant(self, variant_id: str) -> dict | None:
        await self.connect()
        assert self._pool
        row = await self._pool.fetchrow("SELECT * FROM localized_variant WHERE id = $1", variant_id)
        return dict(row) if row else None

    async def fetch_job(self, job_id: str) -> dict | None:
        await self.connect()
        assert self._pool
        row = await self._pool.fetchrow(
            """
            SELECT j.*, p.owner_id
            FROM localization_job j
            JOIN project p ON p.id = j.project_id
            WHERE j.id = $1
            """,
            job_id,
        )
        if row is None:
            return None
        variants = await self._pool.fetch(
            "SELECT * FROM localized_variant WHERE job_id = $1 ORDER BY lang", job_id
        )
        return {
            **dict(row),
            "variants": [dict(v) for v in variants],
        }

    async def update_job_status(self, job_id: str, status: str, error: str | None = None) -> None:
        await self.connect()
        assert self._pool
        await self._pool.execute(
            """
            UPDATE localization_job
            SET status = $2, error_message = $3, updated_at = NOW()
            WHERE id = $1
            """,
            job_id,
            status,
            error,
        )

    async def update_variant(
        self,
        variant_id: str,
        *,
        status: str | None = None,
        video_url: str | None = None,
        audio_url: str | None = None,
        subs_url: str | None = None,
        preview_url: str | None = None,
        report: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        await self.connect()
        assert self._pool
        json_report = json.dumps(report) if report is not None else None
        await self._pool.execute(
            """
            UPDATE localized_variant
            SET
                status = COALESCE($2, status),
                video_url = COALESCE($3, video_url),
                audio_url = COALESCE($4, audio_url),
                subs_url = COALESCE($5, subs_url),
                preview_url = COALESCE($6, preview_url),
                report = COALESCE($7::jsonb, report),
                error_message = COALESCE($8, error_message),
                updated_at = NOW()
            WHERE id = $1
            """,
            variant_id,
            status,
            video_url,
            audio_url,
            subs_url,
            preview_url,
            json_report,
            error_message,
        )

    async def update_variant_by_job_and_lang(
        self,
        job_id: str,
        lang: str,
        **kwargs,
    ) -> dict | None:
        await self.connect()
        assert self._pool
        row = await self._pool.fetchrow(
            "SELECT id FROM localized_variant WHERE job_id = $1 AND lang = $2", job_id, lang
        )
        if row is None:
            return None
        await self.update_variant(row["id"], **kwargs)
        return {"id": row["id"]}


database = Database()
