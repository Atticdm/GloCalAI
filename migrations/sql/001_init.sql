CREATE TABLE IF NOT EXISTS app_user (
    id VARCHAR(36) PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin','editor','viewer')),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project (
    id VARCHAR(36) PRIMARY KEY,
    owner_id VARCHAR(36) NOT NULL REFERENCES app_user(id),
    name TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS asset (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES project(id),
    type TEXT NOT NULL CHECK (type IN ('video','image','text')),
    s3_url TEXT NOT NULL,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS voice_profile (
    id VARCHAR(36) PRIMARY KEY,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_params JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS brand_glossary (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES project(id),
    term TEXT NOT NULL,
    target_map JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS localization_job (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL REFERENCES project(id),
    status TEXT NOT NULL CHECK (status IN ('queued','processing','done','error','partial')),
    source_asset_id VARCHAR(36) NOT NULL REFERENCES asset(id),
    languages TEXT[] NOT NULL,
    voice_profile_id VARCHAR(36) REFERENCES voice_profile(id),
    options JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by VARCHAR(36) NOT NULL REFERENCES app_user(id),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS localized_variant (
    id VARCHAR(36) PRIMARY KEY,
    job_id VARCHAR(36) NOT NULL REFERENCES localization_job(id),
    lang TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued','processing','done','error')),
    video_url TEXT,
    audio_url TEXT,
    subs_url TEXT,
    preview_url TEXT,
    report JSONB,
    error_message TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_variant_job_lang UNIQUE (job_id, lang)
);
