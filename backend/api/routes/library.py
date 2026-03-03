"""
library.py — Student library, OpenClaw chat, and user management.

Exports three routers:
  users_router   → mounted at /api/users
  library_router → mounted at /api/library
  chat_router    → mounted at /api/chat
"""

import logging
import os
import uuid
from typing import Optional

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.celery_app import celery_app
from core.database import (
    AsyncSessionLocal,
    ChatMessage,
    ChatSession,
    LibraryItem,
    ModuleProgress,
    User,
    get_db,
)
from services.rag_engine import get_rag_engine
from services.semantic_engine import get_semantic_engine
from services.worlds_engine import WORLDS, get_worlds_engine

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/amlkr-uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/tiff"}
ALLOWED_DOC_TYPES   = {"application/pdf", "application/epub+zip"}
ALLOWED_TEXT_TYPES  = {"text/plain", "text/markdown", "text/x-markdown"}
ALLOWED_DOCX_TYPES  = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}

users_router   = APIRouter()
library_router = APIRouter()
chat_router    = APIRouter()


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _save_upload(file: UploadFile, dest: str) -> str:
    async with aiofiles.open(dest, "wb") as f:
        await f.write(await file.read())
    return dest


def _user_to_dict(u: User) -> dict:
    return {
        "id":         str(u.id),
        "email":      u.email,
        "name":       u.name,
        "role":       u.role,
        "avatar_url": u.avatar_url,
        "metadata":   u.metadata_,
        "created_at": u.created_at.isoformat(),
    }


def _item_to_dict(item: LibraryItem) -> dict:
    return {
        "id":               str(item.id),
        "user_id":          str(item.user_id),
        "name":             item.name,
        "file_type":        item.file_type,
        "file_url":         item.file_url,
        "file_size_bytes":  item.file_size_bytes,
        "ingested":         item.ingested,
        "metadata":         item.metadata_,
        "created_at":       item.created_at.isoformat(),
    }


def _session_to_dict(s: ChatSession) -> dict:
    return {
        "id":         str(s.id),
        "user_id":    str(s.user_id),
        "title":      s.title,
        "context":    s.context,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


def _message_to_dict(m: ChatMessage) -> dict:
    return {
        "id":         str(m.id),
        "session_id": str(m.session_id),
        "role":       m.role,
        "content":    m.content,
        "created_at": m.created_at.isoformat(),
    }


# ─── Celery tasks ─────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="tasks.ingest_document")
def task_ingest_document(self, library_item_id: str, user_id: str, file_path: str, file_type: str):
    """
    Ingest a PDF or EPUB into ChromaDB.
    Updates library_items.ingested and chroma_doc_ids on completion.
    """
    import asyncio
    from sqlalchemy import update
    from core.database import AsyncSessionLocal, LibraryItem

    async def _run():
        rag = get_rag_engine()

        if file_type == "pdf":
            doc_ids = rag.ingest_pdf(file_path, user_id, library_item_id)
        elif file_type == "epub":
            doc_ids = rag.ingest_epub(file_path, user_id, library_item_id)
        elif file_type in ("txt", "md"):
            doc_ids = rag.ingest_txt(file_path, user_id, library_item_id)
        elif file_type == "docx":
            doc_ids = rag.ingest_docx(file_path, user_id, library_item_id)
        else:
            logger.warning(f"Unsupported file_type for ingestion: {file_type}")
            return

        chroma_collection = rag._collection_name(user_id)

        async with AsyncSessionLocal() as db:
            await db.execute(
                update(LibraryItem)
                .where(LibraryItem.id == uuid.UUID(library_item_id))
                .values(
                    ingested=True,
                    chroma_collection=chroma_collection,
                    chroma_doc_ids=doc_ids,
                )
            )
            await db.commit()

        logger.info(f"Ingested {len(doc_ids)} chunks for item {library_item_id}")

    asyncio.run(_run())


@celery_app.task(bind=True, name="tasks.ingest_project_document")
def task_ingest_project_document(
    self,
    doc_id: str,
    project_id: str,
    file_path: str,
    world_id: Optional[str] = None,
):
    """
    Ingest any supported document (PDF/EPUB/TXT/MD/DOCX) into a project or
    world ChromaDB collection.
    """
    import asyncio

    async def _run():
        rag = get_rag_engine()
        chunk_ids = rag.ingest_document(
            file_path=file_path,
            project_id=project_id,
            world_id=world_id,
            doc_id=doc_id,
        )
        logger.info(
            f"Project doc ingested: {len(chunk_ids)} chunks "
            f"(project={project_id}, world={world_id}, doc={doc_id})"
        )

    asyncio.run(_run())


# ─── Users ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: Optional[str] = None
    role: str = "student"          # student | instructor
    avatar_url: Optional[str] = None
    metadata: dict = {}


@users_router.post("/")
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db)):
    """POST /api/users/ — create a student or instructor profile."""
    if body.role not in ("student", "instructor"):
        raise HTTPException(400, "role must be 'student' or 'instructor'")

    user = User(
        name=body.name,
        email=body.email,
        role=body.role,
        avatar_url=body.avatar_url,
        metadata_=body.metadata,
    )
    db.add(user)
    await db.flush()
    return _user_to_dict(user)


@users_router.get("/{user_id}")
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """GET /api/users/{user_id}."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user_id")

    user = await db.get(User, uid)
    if not user:
        raise HTTPException(404, "User not found")
    return _user_to_dict(user)


@users_router.get("/")
async def list_users(
    role: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """GET /api/users/ — list all users, optionally filtered by role."""
    query = select(User).order_by(User.created_at.desc())
    if role:
        query = query.where(User.role == role)
    rows = (await db.execute(query)).scalars().all()
    return {"users": [_user_to_dict(u) for u in rows]}


# ─── Module progress ─────────────────────────────────────────────────────────

class ProgressUpdate(BaseModel):
    status: str          # not_started | in_progress | completed
    data: dict = {}
    project_id: Optional[str] = None


@users_router.get("/{user_id}/progress")
async def get_progress(user_id: str, db: AsyncSession = Depends(get_db)):
    """GET /api/users/{user_id}/progress — student module progress."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user_id")

    query = select(ModuleProgress).where(ModuleProgress.user_id == uid)
    rows = (await db.execute(query)).scalars().all()

    return {
        "user_id": user_id,
        "progress": [
            {
                "module_name": r.module_name,
                "status":      r.status,
                "data":        r.data,
                "updated_at":  r.updated_at.isoformat(),
            }
            for r in rows
        ],
    }


@users_router.put("/{user_id}/progress/{module_name}")
async def upsert_progress(
    user_id: str,
    module_name: str,
    body: ProgressUpdate,
    db: AsyncSession = Depends(get_db),
):
    """PUT /api/users/{user_id}/progress/{module_name} — upsert module progress."""
    valid_modules = ("modulo_1", "modulo_2", "modulo_3")
    if module_name not in valid_modules:
        raise HTTPException(400, f"module_name must be one of: {valid_modules}")

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user_id")

    query = select(ModuleProgress).where(
        ModuleProgress.user_id == uid,
        ModuleProgress.module_name == module_name,
    )
    existing = (await db.execute(query)).scalar_one_or_none()

    if existing:
        existing.status     = body.status
        existing.data       = body.data
        if body.project_id:
            existing.project_id = uuid.UUID(body.project_id)
    else:
        db.add(ModuleProgress(
            user_id=uid,
            module_name=module_name,
            status=body.status,
            data=body.data,
            project_id=uuid.UUID(body.project_id) if body.project_id else None,
        ))

    await db.flush()
    return {"user_id": user_id, "module_name": module_name, "status": body.status}


# ─── Library items ────────────────────────────────────────────────────────────

@library_router.post("/upload")
async def upload_library_item(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/library/upload — upload image, PDF, or EPUB to student library.

    Images are stored immediately (no ingestion step needed).
    PDFs and EPUBs trigger async ChromaDB ingestion via Celery.
    """
    content_type = file.content_type or ""

    name_lower = (file.filename or "").lower()
    if content_type in ALLOWED_IMAGE_TYPES:
        file_type = "image"
    elif content_type == "application/pdf":
        file_type = "pdf"
    elif content_type in ("application/epub+zip", "application/epub"):
        file_type = "epub"
    elif content_type in ALLOWED_TEXT_TYPES:
        file_type = "md" if name_lower.endswith(".md") else "txt"
    elif content_type in ALLOWED_DOCX_TYPES:
        file_type = "docx"
    else:
        # Infer from filename extension as fallback
        if name_lower.endswith(".pdf"):
            file_type = "pdf"
        elif name_lower.endswith(".epub"):
            file_type = "epub"
        elif name_lower.endswith(".md"):
            file_type = "md"
        elif name_lower.endswith(".txt"):
            file_type = "txt"
        elif name_lower.endswith(".docx"):
            file_type = "docx"
        elif any(name_lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
            file_type = "image"
        else:
            raise HTTPException(415, f"Unsupported file type: {content_type}")

    item_id   = str(uuid.uuid4())
    file_name = f"{item_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    await _save_upload(file, file_path)
    file_size = os.path.getsize(file_path)

    item = LibraryItem(
        id=uuid.UUID(item_id),
        user_id=uuid.UUID(user_id),
        name=file.filename or file_name,
        file_type=file_type,
        file_url=file_path,         # swap for R2 URL when storage is wired
        file_size_bytes=file_size,
        ingested=(file_type == "image"),  # images don't need text ingestion
    )
    db.add(item)
    await db.flush()

    # Trigger async ingestion for documents
    task_id = None
    if file_type in ("pdf", "epub", "txt", "md", "docx"):
        task = task_ingest_document.delay(item_id, user_id, file_path, file_type)
        task_id = task.id

    return {
        **_item_to_dict(item),
        "task_id": task_id,
        "message": "Ingestion queued." if task_id else "Image stored.",
    }


@library_router.get("/")
async def list_library_items(
    user_id: str,
    file_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """GET /api/library/?user_id=... — list student library items."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user_id")

    query = (
        select(LibraryItem)
        .where(LibraryItem.user_id == uid)
        .order_by(LibraryItem.created_at.desc())
    )
    if file_type:
        query = query.where(LibraryItem.file_type == file_type)

    rows = (await db.execute(query)).scalars().all()
    return {"items": [_item_to_dict(r) for r in rows], "total": len(rows)}


@library_router.get("/worlds")
async def list_worlds_early():
    """GET /api/library/worlds — list all theoretical worlds. (Declared before /{item_id} to avoid route shadowing.)"""
    return {"worlds": get_worlds_engine().list_worlds()}


@library_router.post("/worlds/{world_id}/ingest")
async def ingest_world_document(
    world_id: str,
    file: UploadFile = File(...),
    project_id: str = Form("_admin"),
):
    """
    POST /api/library/worlds/{world_id}/ingest — upload and ingest a text into a world collection.

    The file is stored temporarily, ingested into ChromaDB world_{world_id},
    then deleted. Returns chunk count.
    """
    from services.worlds_engine import WORLDS
    if world_id not in WORLDS:
        raise HTTPException(404, f"World '{world_id}' not found. Valid: {list(WORLDS.keys())}")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".pdf", ".txt", ".md", ".epub", ".docx"):
        raise HTTPException(400, "Supported formats: pdf, txt, md, epub, docx")

    tmp_path = os.path.join(UPLOAD_DIR, f"world_{world_id}_{uuid.uuid4()}{ext}")
    try:
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)

        rag = get_rag_engine()
        doc_id = os.path.splitext(file.filename or "doc")[0]
        chunk_ids = rag.ingest_document(
            file_path=tmp_path,
            project_id=project_id,
            world_id=world_id,
            doc_id=doc_id,
        )
        return {
            "world_id":   world_id,
            "filename":   file.filename,
            "chunks":     len(chunk_ids),
            "status":     "ingested",
        }
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@library_router.get("/worlds/{world_id}/documents")
async def list_world_documents(world_id: str):
    """GET /api/library/worlds/{world_id}/documents — list documents ingested into a world."""
    from services.worlds_engine import WORLDS
    if world_id not in WORLDS:
        raise HTTPException(404, f"World '{world_id}' not found.")
    rag = get_rag_engine()
    try:
        col = rag._get_or_create_named_collection(rag._world_collection_name(world_id))
        count = col.count()
        result = col.get(include=["metadatas"]) if count > 0 else {"metadatas": []}
        sources: dict[str, int] = {}
        for meta in result["metadatas"]:
            src = meta.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1
        return {
            "world_id":   world_id,
            "total_chunks": count,
            "documents":  [{"source": s, "chunks": n} for s, n in sources.items()],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@library_router.get("/{item_id}")
async def get_library_item(item_id: str, db: AsyncSession = Depends(get_db)):
    """GET /api/library/{item_id}."""
    try:
        iid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(400, "Invalid item_id")

    item = await db.get(LibraryItem, iid)
    if not item:
        raise HTTPException(404, "Library item not found")
    return _item_to_dict(item)


@library_router.delete("/{item_id}")
async def delete_library_item(
    item_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """DELETE /api/library/{item_id}?user_id=... — delete item and its ChromaDB vectors."""
    try:
        iid = uuid.UUID(item_id)
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid UUID")

    item = await db.get(LibraryItem, iid)
    if not item:
        raise HTTPException(404, "Library item not found")
    if item.user_id != uid:
        raise HTTPException(403, "Forbidden")

    # Remove from ChromaDB if previously ingested
    if item.ingested and item.file_type in ("pdf", "epub", "txt", "md", "docx"):
        rag = get_rag_engine()
        rag.delete_item(user_id, item_id)

    # Remove local file
    if os.path.exists(item.file_url):
        os.remove(item.file_url)

    await db.delete(item)
    return {"deleted": True, "item_id": item_id}


@library_router.post("/{item_id}/ingest")
async def reingest_item(
    item_id: str,
    user_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """POST /api/library/{item_id}/ingest — manually trigger / retry RAG ingestion."""
    try:
        iid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(400, "Invalid item_id")

    item = await db.get(LibraryItem, iid)
    if not item:
        raise HTTPException(404, "Library item not found")
    if item.file_type not in ("pdf", "epub", "txt", "md", "docx"):
        raise HTTPException(400, "Only PDF, EPUB, TXT, MD, and DOCX items can be ingested")

    task = task_ingest_document.delay(item_id, user_id, item.file_url, item.file_type)
    return {"item_id": item_id, "task_id": task.id, "status": "queued"}


@library_router.get("/stats/{user_id}")
async def library_stats(user_id: str, db: AsyncSession = Depends(get_db)):
    """GET /api/library/stats/{user_id} — library + ChromaDB stats for a student."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user_id")

    query = select(LibraryItem).where(LibraryItem.user_id == uid)
    rows  = (await db.execute(query)).scalars().all()

    rag   = get_rag_engine()
    chroma_stats = rag.collection_stats(user_id)

    return {
        "user_id":     user_id,
        "total_items": len(rows),
        "by_type": {
            "image": sum(1 for r in rows if r.file_type == "image"),
            "pdf":   sum(1 for r in rows if r.file_type == "pdf"),
            "epub":  sum(1 for r in rows if r.file_type == "epub"),
        },
        "ingested_docs": sum(1 for r in rows if r.ingested and r.file_type != "image"),
        "chroma":        chroma_stats,
    }


# ─── Project / World document ingestion ──────────────────────────────────────

@library_router.post("/ingest")
async def ingest_project_document(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    world_id: Optional[str] = Form(None),
):
    """
    POST /api/library/ingest — upload and ingest a document into a project
    (or world) ChromaDB collection.

    Supports: PDF, EPUB, TXT, MD, DOCX.
    Triggers Celery task — returns immediately with doc_id and task_id.
    """
    name_lower = (file.filename or "").lower()
    ext_map = {".pdf": "pdf", ".epub": "epub", ".txt": "txt", ".md": "md", ".docx": "docx"}
    ext = next((e for e in ext_map if name_lower.endswith(e)), None)
    if ext is None:
        raise HTTPException(
            415,
            f"Unsupported file type. Accepted: PDF, EPUB, TXT, MD, DOCX."
        )

    doc_id    = str(uuid.uuid4())
    file_name = f"proj_{doc_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    await _save_upload(file, file_path)

    task = task_ingest_project_document.delay(doc_id, project_id, file_path, world_id)
    return {
        "doc_id":     doc_id,
        "task_id":    task.id,
        "project_id": project_id,
        "world_id":   world_id,
        "filename":   file.filename,
        "status":     "queued",
    }


@library_router.get("/documents/{project_id}")
async def list_project_documents(project_id: str):
    """
    GET /api/library/documents/{project_id} — list all documents ingested
    into a project's ChromaDB collection, aggregated by source file.
    """
    rag  = get_rag_engine()
    docs = rag.list_documents(project_id)
    return {"project_id": project_id, "documents": docs, "total": len(docs)}


class LibraryQueryRequest(BaseModel):
    question: str
    project_id: Optional[str] = None
    world_id: Optional[str] = None
    n_results: int = 5


@library_router.post("/query")
async def query_library(body: LibraryQueryRequest):
    """
    POST /api/library/query — direct RAG query for testing.

    Pass project_id to search a project collection, world_id to search a world
    collection. Returns chunks with source/page citations.
    """
    if not body.project_id and not body.world_id:
        raise HTTPException(400, "Provide project_id or world_id")

    rag    = get_rag_engine()
    chunks = rag.query_with_citations(
        question=body.question,
        project_id=body.project_id,
        world_id=body.world_id,
        n_results=body.n_results,
    )
    return {
        "question":   body.question,
        "project_id": body.project_id,
        "world_id":   body.world_id,
        "results":    chunks,
        "total":      len(chunks),
    }


# ─── Chat (OpenClaw) ─────────────────────────────────────────────────────────

class ChatMessageRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None               # if None, a new session is created
    library_item_ids: Optional[list[str]] = None   # restrict RAG to these items
    world_id: Optional[str] = None                 # activates a theoretical world
    context: dict = {}                             # {project_id, visual_map_id, …}


@chat_router.post("/message")
async def send_message(body: ChatMessageRequest, db: AsyncSession = Depends(get_db)):
    """
    POST /api/chat/message — send a message to OpenClaw.

    Flow:
    1. Load or create a chat session.
    2. Query student's ChromaDB library for relevant context.
    3. Pass context + history to Qwen2.5:14b via SemanticEngine.openclaw_chat().
    4. Persist user and assistant messages.
    5. Return the assistant reply.
    """
    try:
        uid = uuid.UUID(body.user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user_id")

    # ── Get or create session ─────────────────────────────────────────────────
    session: Optional[ChatSession] = None
    if body.session_id:
        try:
            sid = uuid.UUID(body.session_id)
        except ValueError:
            raise HTTPException(400, "Invalid session_id")
        session = await db.get(ChatSession, sid)
        if not session:
            raise HTTPException(404, "Session not found")
    else:
        session = ChatSession(
            user_id=uid,
            title=body.message[:60] + ("…" if len(body.message) > 60 else ""),
            context=body.context,
        )
        db.add(session)
        await db.flush()

    # ── Load conversation history ─────────────────────────────────────────────
    history_query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
    )
    history_rows = (await db.execute(history_query)).scalars().all()
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    # ── RAG retrieval (student personal library) ──────────────────────────────
    rag_context: Optional[str] = None
    try:
        rag = get_rag_engine()
        rag_context = rag.build_rag_context(
            user_id=body.user_id,
            query_text=body.message,
            library_item_ids=body.library_item_ids,
            n_results=6,
        )
    except Exception as e:
        logger.warning(f"RAG retrieval failed (non-fatal): {e}")

    # ── World context (theoretical framework + world library citations) ────────
    world_context: Optional[str] = None
    if body.world_id:
        try:
            worlds = get_worlds_engine()
            world_context = worlds.build_world_context(
                world_id=body.world_id,
                question=body.message,
                rag_engine=get_rag_engine(),
                n_results=4,
            )
            if world_context:
                logger.info(f"World context injected: {worlds.format_world_header(body.world_id)}")
        except Exception as e:
            logger.warning(f"World context retrieval failed (non-fatal): {e}")

    # ── Generate reply ────────────────────────────────────────────────────────
    semantic = get_semantic_engine()
    reply = semantic.openclaw_chat(
        message=body.message,
        history=history,
        rag_context=rag_context,
        world_context=world_context,
    )

    # ── Persist messages ──────────────────────────────────────────────────────
    db.add(ChatMessage(session_id=session.id, role="user",      content=body.message))
    db.add(ChatMessage(session_id=session.id, role="assistant", content=reply))
    await db.flush()

    return {
        "session_id":   str(session.id),
        "reply":        reply,
        "rag_used":     rag_context is not None,
        "world_id":     body.world_id,
        "world_active": world_context is not None,
    }


@chat_router.get("/sessions")
async def list_sessions(user_id: str, db: AsyncSession = Depends(get_db)):
    """GET /api/chat/sessions?user_id=... — list chat sessions for a student."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(400, "Invalid user_id")

    query = (
        select(ChatSession)
        .where(ChatSession.user_id == uid)
        .order_by(ChatSession.updated_at.desc())
    )
    rows = (await db.execute(query)).scalars().all()
    return {"sessions": [_session_to_dict(r) for r in rows]}


@chat_router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, db: AsyncSession = Depends(get_db)):
    """GET /api/chat/sessions/{session_id}/messages — full message history."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(400, "Invalid session_id")

    session = await db.get(ChatSession, sid)
    if not session:
        raise HTTPException(404, "Session not found")

    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == sid)
        .order_by(ChatMessage.created_at.asc())
    )
    rows = (await db.execute(query)).scalars().all()
    return {
        "session": _session_to_dict(session),
        "messages": [_message_to_dict(m) for m in rows],
    }


@chat_router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """DELETE /api/chat/sessions/{session_id} — delete session and all its messages."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(400, "Invalid session_id")

    session = await db.get(ChatSession, sid)
    if not session:
        raise HTTPException(404, "Session not found")

    await db.delete(session)
    return {"deleted": True, "session_id": session_id}
