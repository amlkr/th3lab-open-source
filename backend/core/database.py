import os
import uuid
from datetime import datetime
from typing import AsyncGenerator, Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://amlkr:amlkr_secret@localhost:5432/amlkr_db",
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# ─── Users ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="student")   # instructor | student
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ─── Projects ────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    module: Mapped[str] = mapped_column(String(50), nullable=False)    # th3lab | visual_cult
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ─── Analysis jobs ────────────────────────────────────────────────────────────

class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255))
    input_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    result: Mapped[Optional[dict]] = mapped_column(JSONB)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ─── Shots ───────────────────────────────────────────────────────────────────

class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    shot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    shot_scale: Mapped[Optional[str]] = mapped_column(String(10))         # ECS | CS | MS | FS | LS
    scale_confidence: Mapped[Optional[float]] = mapped_column(Float)
    camera_movement: Mapped[Optional[str]] = mapped_column(String(50))
    brightness: Mapped[Optional[float]] = mapped_column(Float)
    saturation: Mapped[Optional[float]] = mapped_column(Float)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ─── Visual maps ─────────────────────────────────────────────────────────────

class VisualMap(Base):
    __tablename__ = "visual_maps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    image_urls: Mapped[list] = mapped_column(JSONB, default=list)
    clip_embeddings: Mapped[Optional[list]] = mapped_column(JSONB)
    centroid: Mapped[Optional[list]] = mapped_column(JSONB)
    coherence_score: Mapped[Optional[float]] = mapped_column(Float)
    outlier_indices: Mapped[list] = mapped_column(JSONB, default=list)
    semantic_analysis: Mapped[Optional[dict]] = mapped_column(JSONB)
    report: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ─── Mirror scores ────────────────────────────────────────────────────────────

class MirrorScore(Base):
    __tablename__ = "mirror_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    visual_map_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    series_image_urls: Mapped[list] = mapped_column(JSONB, default=list)
    mirror_score: Mapped[float] = mapped_column(Float, nullable=False)
    per_image_scores: Mapped[list] = mapped_column(JSONB, default=list)
    report: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ─── Library items ────────────────────────────────────────────────────────────

class LibraryItem(Base):
    __tablename__ = "library_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)   # image | pdf | epub
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    chroma_collection: Mapped[Optional[str]] = mapped_column(String(255))
    chroma_doc_ids: Mapped[list] = mapped_column(JSONB, default=list)
    ingested: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ─── Chat sessions ────────────────────────────────────────────────────────────

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ─── Chat messages ────────────────────────────────────────────────────────────

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)   # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ─── Module progress ─────────────────────────────────────────────────────────

class ModuleProgress(Base):
    __tablename__ = "module_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    module_name: Mapped[str] = mapped_column(String(100), nullable=False)   # modulo_1 | modulo_2 | modulo_3
    status: Mapped[str] = mapped_column(String(50), default="not_started")
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ─── Session dependency ───────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
