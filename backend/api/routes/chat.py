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
    world_id: Optional[str] = None   # activates a theoretical world


@router.post("/")
async def chat(body: ChatRequest):
    """
    POST /api/chat — stateless chat with the visual collaborator.

    Accepts { message, history, context, world_id } and returns { response }.
    context: full job result from the last analysis.
    world_id: if provided, injects world vocabulary + library citations.
    """
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
        except Exception as e:
            logger.warning(f"World context failed (non-fatal): {e}")

    semantic = get_semantic_engine()
    response = semantic.openclaw_chat(
        message=body.message,
        history=body.history,
        analysis_context=body.context,
        world_context=world_context,
    )
    return {
        "response":     response,
        "world_id":     body.world_id,
        "world_active": world_context is not None,
    }
