from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="editor")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    projects: Mapped[List["Project"]] = relationship(back_populates="owner")

    __table_args__ = (
        CheckConstraint("role in ('admin','editor','viewer')", name="app_user_role_check"),
    )


class Project(Base):
    __tablename__ = "project"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("app_user.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    owner: Mapped[AppUser] = relationship(back_populates="projects")
    assets: Mapped[List["Asset"]] = relationship(back_populates="project")
    jobs: Mapped[List["LocalizationJob"]] = relationship(back_populates="project")


class Asset(Base):
    __tablename__ = "asset"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("project.id"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    s3_url: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    project: Mapped[Project] = relationship(back_populates="assets")
    jobs: Mapped[List["LocalizationJob"]] = relationship(back_populates="source_asset")

    __table_args__ = (CheckConstraint("type in ('video','image','text')", name="asset_type_check"),)


class VoiceProfile(Base):
    __tablename__ = "voice_profile"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class BrandGlossary(Base):
    __tablename__ = "brand_glossary"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project.id"), nullable=False)
    term: Mapped[str] = mapped_column(String(255), nullable=False)
    target_map: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    project: Mapped[Project] = relationship(backref="glossaries")


class LocalizationJob(Base):
    __tablename__ = "localization_job"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("project.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    source_asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("asset.id"), nullable=False)
    languages: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)
    voice_profile_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("voice_profile.id"),
        nullable=True,
    )
    options: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("app_user.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project: Mapped[Project] = relationship(back_populates="jobs")
    source_asset: Mapped[Asset] = relationship(back_populates="jobs")
    variants: Mapped[List["LocalizedVariant"]] = relationship(back_populates="job")

    __table_args__ = (
        CheckConstraint(
            "status in ('queued','processing','done','error','partial')",
            name="job_status_check",
        ),
    )


class LocalizedVariant(Base):
    __tablename__ = "localized_variant"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("localization_job.id"),
        nullable=False,
    )
    lang: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    video_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subs_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preview_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    report: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    job: Mapped[LocalizationJob] = relationship(back_populates="variants")

    __table_args__ = (
        CheckConstraint(
            "status in ('queued','processing','done','error')",
            name="variant_status_check",
        ),
        UniqueConstraint("job_id", "lang", name="uq_variant_job_lang"),
    )
