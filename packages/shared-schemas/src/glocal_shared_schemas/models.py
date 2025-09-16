from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthToken(BaseModel):
    token: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)


class Project(ProjectCreate):
    id: str
    owner_id: str
    created_at: datetime


class ProjectSummary(BaseModel):
    id: str
    name: str
    created_at: datetime


class AssetType(str, Enum):
    video = "video"
    image = "image"
    text = "text"


class UploadAssetUrlRequest(BaseModel):
    projectId: str
    type: AssetType
    filename: str
    mime: str


class UploadAssetUrlResponse(BaseModel):
    asset_id: str
    upload_url: HttpUrl
    object_key: str
    fields: Dict[str, Any] = Field(default_factory=dict)


class UploadAssetComplete(BaseModel):
    projectId: str
    type: AssetType
    s3_url: HttpUrl
    meta: Dict[str, Any]


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    done = "done"
    error = "error"
    partial = "partial"


class LocalizationStage(str, Enum):
    asr = "asr"
    translate = "translate"
    tts = "tts"
    mix = "mix"
    subs = "subs"
    textinframe = "textinframe"
    qc = "qc"
    pack = "pack"


class JobOption(BaseModel):
    subs: bool = True
    dub: bool = True
    replace_text_in_frame: bool = False
    upload_to_youtube: bool = False


class JobCreate(BaseModel):
    projectId: str
    sourceAssetId: str
    languages: List[str]
    voiceProfileId: Optional[str]
    options: JobOption


class LocalizationVariant(BaseModel):
    id: str
    job_id: str
    lang: str
    status: str
    video_url: Optional[str]
    audio_url: Optional[str]
    subs_url: Optional[str]
    preview_url: Optional[str]
    report: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


class LocalizationJob(BaseModel):
    id: str
    project_id: str
    status: JobStatus
    source_asset_id: str
    languages: List[str]
    voice_profile_id: Optional[str]
    options: Dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str]
    variants: List[LocalizationVariant] = Field(default_factory=list)


class JobProgressEvent(BaseModel):
    job_id: str
    stage: LocalizationStage
    lang: Optional[str]
    status: str
    progress: float = 0.0
    message: Optional[str]
    timestamp: datetime


class SSEMessage(BaseModel):
    event: str
    data: Dict[str, Any]


class VariantDownloadLinks(BaseModel):
    mp4: HttpUrl
    srt: Optional[HttpUrl]


class VoiceProfile(BaseModel):
    id: str
    name: str
    provider: str
    provider_params: Dict[str, Any]


__all__ = [name for name in globals() if not name.startswith("_")]
