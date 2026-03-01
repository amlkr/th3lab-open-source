-- ─────────────────────────────────────────────────────────────────────────────
-- AMLKR Dashboard — complete database schema
-- ─────────────────────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Users ───────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE,
    name        VARCHAR(255) NOT NULL,
    role        VARCHAR(20)  NOT NULL DEFAULT 'student' CHECK (role IN ('instructor', 'student')),
    avatar_url  TEXT,
    metadata    JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── Projects ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS projects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id    UUID REFERENCES users(id) ON DELETE SET NULL,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    module      VARCHAR(50)  NOT NULL CHECK (module IN ('th3lab', 'visual_cult')),
    metadata    JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── Analysis jobs ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS analysis_jobs (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id     UUID REFERENCES projects(id) ON DELETE SET NULL,
    user_id        UUID REFERENCES users(id)    ON DELETE SET NULL,
    job_type       VARCHAR(100) NOT NULL,
    status         VARCHAR(50)  NOT NULL DEFAULT 'pending',
    celery_task_id VARCHAR(255),
    input_data     JSONB        NOT NULL DEFAULT '{}',
    result         JSONB,
    error_message  TEXT,
    progress       INTEGER      NOT NULL DEFAULT 0,
    created_at     TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at     TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── Shots (th3lab video analysis) ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS shots (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id           UUID NOT NULL REFERENCES analysis_jobs(id) ON DELETE CASCADE,
    shot_number      INTEGER          NOT NULL,
    start_time       DOUBLE PRECISION NOT NULL,
    end_time         DOUBLE PRECISION NOT NULL,
    duration         DOUBLE PRECISION NOT NULL,
    shot_scale       VARCHAR(10),          -- ECS | CS | MS | FS | LS
    scale_confidence DOUBLE PRECISION,
    camera_movement  VARCHAR(50),
    brightness       DOUBLE PRECISION,
    saturation       DOUBLE PRECISION,
    thumbnail_url    TEXT,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── Visual maps (Módulo 1 — Mapa Visual Interno) ────────────────────────────

CREATE TABLE IF NOT EXISTS visual_maps (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id       UUID NOT NULL REFERENCES projects(id)  ON DELETE CASCADE,
    user_id          UUID          REFERENCES users(id)     ON DELETE SET NULL,
    image_urls       JSONB         NOT NULL DEFAULT '[]',
    clip_embeddings  JSONB,               -- list of 768-dim float arrays
    centroid         JSONB,               -- normalized mean embedding
    coherence_score  DOUBLE PRECISION,
    outlier_indices  JSONB         NOT NULL DEFAULT '[]',
    semantic_analysis JSONB,
    report           TEXT,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── Mirror scores (Módulo 3 — Modo Espejo) ──────────────────────────────────

CREATE TABLE IF NOT EXISTS mirror_scores (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id        UUID NOT NULL REFERENCES projects(id)    ON DELETE CASCADE,
    user_id           UUID          REFERENCES users(id)       ON DELETE SET NULL,
    visual_map_id     UUID NOT NULL REFERENCES visual_maps(id) ON DELETE CASCADE,
    series_image_urls JSONB NOT NULL DEFAULT '[]',
    mirror_score      DOUBLE PRECISION NOT NULL,
    per_image_scores  JSONB NOT NULL DEFAULT '[]',
    report            TEXT,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── Student library ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS library_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    file_type           VARCHAR(50)  NOT NULL CHECK (file_type IN ('image', 'pdf', 'epub')),
    file_url            TEXT         NOT NULL,
    file_size_bytes     BIGINT,
    chroma_collection   VARCHAR(255),       -- ChromaDB collection name
    chroma_doc_ids      JSONB NOT NULL DEFAULT '[]',
    ingested            BOOLEAN      NOT NULL DEFAULT FALSE,
    metadata            JSONB        NOT NULL DEFAULT '{}',
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── Chat sessions (OpenClaw) ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS chat_sessions (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      VARCHAR(255),
    context    JSONB NOT NULL DEFAULT '{}',  -- {project_id, visual_map_id, library_item_ids}
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── Chat messages ────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS chat_messages (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role       VARCHAR(20)  NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content    TEXT         NOT NULL,
    metadata   JSONB        NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── Module progress (VISUAL CULT student journey) ───────────────────────────

CREATE TABLE IF NOT EXISTS module_progress (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    project_id   UUID          REFERENCES projects(id) ON DELETE SET NULL,
    module_name  VARCHAR(100)  NOT NULL,   -- modulo_1 | modulo_2 | modulo_3
    status       VARCHAR(50)   NOT NULL DEFAULT 'not_started',
    data         JSONB         NOT NULL DEFAULT '{}',
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (user_id, module_name)
);

-- ─── Indexes ─────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_projects_owner       ON projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_jobs_project         ON analysis_jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_jobs_user            ON analysis_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status          ON analysis_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_celery          ON analysis_jobs(celery_task_id);
CREATE INDEX IF NOT EXISTS idx_shots_job            ON shots(job_id);
CREATE INDEX IF NOT EXISTS idx_visual_maps_project  ON visual_maps(project_id);
CREATE INDEX IF NOT EXISTS idx_visual_maps_user     ON visual_maps(user_id);
CREATE INDEX IF NOT EXISTS idx_mirror_project       ON mirror_scores(project_id);
CREATE INDEX IF NOT EXISTS idx_library_user         ON library_items(user_id);
CREATE INDEX IF NOT EXISTS idx_library_type         ON library_items(file_type);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user   ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_progress_user        ON module_progress(user_id);

-- ─── updated_at trigger ──────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_jobs_updated_at
    BEFORE UPDATE ON analysis_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_visual_maps_updated_at
    BEFORE UPDATE ON visual_maps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_chat_sessions_updated_at
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_progress_updated_at
    BEFORE UPDATE ON module_progress
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
