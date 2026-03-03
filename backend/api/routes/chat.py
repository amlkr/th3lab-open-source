import logging
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from services.semantic_engine import get_semantic_engine
from services.worlds_engine import get_worlds_engine
from services.rag_engine import get_rag_engine

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    history: list = []
    context: Optional[dict[str, Any]] = None
    world_id: Optional[str] = None    # activates a theoretical world
    project_id: Optional[str] = None  # scopes project RAG collection


@router.post("/")
async def chat(body: ChatRequest):
    """
    POST /api/chat — stateless chat with the visual collaborator.

    Accepts { message, history, context, world_id, project_id } and returns { response }.
    context:    full job result from the last analysis.
    world_id:   if provided, injects world vocabulary + library citations.
    project_id: if provided, queries the project's RAG collection for relevant chunks.
    """
    rag = get_rag_engine()

    # ── 1. World context (tone + world library citations) ────────────────────
    world_context: Optional[str] = None
    if body.world_id:
        try:
            worlds = get_worlds_engine()
            world_context = worlds.build_world_context(
                world_id=body.world_id,
                question=body.message,
                rag_engine=rag,
                n_results=4,
            )
        except Exception as e:
            logger.warning(f"World context failed (non-fatal): {e}")

    # ── 2. Project RAG context (chunks from the project's ingested docs) ─────
    rag_context: Optional[str] = None
    project_id = body.project_id or (body.context or {}).get("project_id")
    if project_id:
        try:
            chunks = rag.query_with_citations(
                question=body.message,
                project_id=str(project_id),
                n_results=4,
            )
            if chunks:
                lines = ["Contexto teórico relevante:"]
                for c in chunks:
                    citation = c["source"]
                    if c.get("page"):
                        citation += f", p. {c['page']}"
                    lines.append(f"\n[{citation}]:\n{c['text']}")
                rag_context = "\n".join(lines)
        except Exception as e:
            logger.warning(f"Project RAG query failed (non-fatal): {e}")

    # ── 3. Generate response ─────────────────────────────────────────────────
    semantic = get_semantic_engine()
    response = semantic.openclaw_chat(
        message=body.message,
        history=body.history,
        analysis_context=body.context,
        world_context=world_context,
        rag_context=rag_context,
    )

    return {
        "response":     response,
        "world_id":     body.world_id,
        "world_active": world_context is not None,
        "rag_chunks":   bool(rag_context),
    }
