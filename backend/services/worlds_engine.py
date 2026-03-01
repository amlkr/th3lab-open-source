"""
worlds_engine.py — Imaginarios (Worlds) configuration and RAG context builder.

Each world is a curated theoretical universe that shapes how OpenClaw interprets
images. Worlds have their own ChromaDB collections populated by the instructor
with canonical texts (Tarkovsky, Birri, Pasolini, etc.).

When a student works within a world, the agent:
  1. Adopts the world's vocabulary and tone
  2. Retrieves relevant passages from the world's library
  3. Cites those texts in the cinematographic response
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─── World definitions ────────────────────────────────────────────────────────

WORLDS: dict[str, dict] = {
    "cine_lentitud": {
        "name": "Cine de la Lentitud",
        "description": "Tarkovsky, Béla Tarr, Pedro Costa",
        "coherence_threshold": 0.85,
        "dominant_vocabulary": ["tiempo", "espera", "densidad", "permanencia"],
        "preferred_scales": ["LS", "ELS"],
        "agent_tone": "contemplativo",
        "library": ["tarkovsky_esculpir_tiempo", "bazin_ontologia"],
        "system_note": (
            "Operás desde la poética del tiempo largo. "
            "La imagen vale por su duración, su resistencia al corte, su capacidad de acumular densidad. "
            "Evitás juicios rápidos. Preferís la espera sobre la acción, el peso sobre el movimiento."
        ),
    },
    "imagen_cuerpo_politico": {
        "name": "Imagen del Cuerpo Político",
        "description": "Birri, Solanas, cine latinoamericano",
        "coherence_threshold": 0.75,
        "dominant_vocabulary": ["urgencia", "pueblo", "territorio", "resistencia"],
        "preferred_scales": ["MS", "CS"],
        "agent_tone": "urgente",
        "library": ["birri_manifiesto", "getino_solanas_hora_hornos"],
        "system_note": (
            "Operás desde la urgencia de lo real latinoamericano. "
            "La imagen tiene posición moral. El cuerpo es político. "
            "El territorio habla. Nombrás lo que las imágenes eligen no mostrar."
        ),
    },
    "visualidad_ritual": {
        "name": "Visualidad del Ritual",
        "description": "Pasolini, Herzog, imagen sagrada",
        "coherence_threshold": 0.80,
        "dominant_vocabulary": ["sagrado", "cuerpo", "rito", "trance"],
        "preferred_scales": ["CS", "ECU"],
        "agent_tone": "ceremonial",
        "library": ["pasolini_empirismo_hereje"],
        "system_note": (
            "Operás desde la dimensión sagrada de la imagen. "
            "El cuerpo es ritual, la cámara es testigo de algo que precede al lenguaje. "
            "Buscás el momento en que la imagen deja de ser representación y se vuelve presencia."
        ),
    },
}


# ─── WorldsEngine ─────────────────────────────────────────────────────────────

class WorldsEngine:
    """
    Configuration layer for the three Imaginarios (Worlds).

    Does not manage ChromaDB directly — delegates retrieval to RAGEngine
    so both share the same PersistentClient and embedding function.
    """

    def list_worlds(self) -> list[dict]:
        """Return all worlds as a sorted list (world_id included in each dict)."""
        return [
            {"world_id": wid, **cfg}
            for wid, cfg in sorted(WORLDS.items(), key=lambda x: x[1]["name"])
        ]

    def get_world(self, world_id: str) -> Optional[dict]:
        """Return a single world config, or None if not found."""
        cfg = WORLDS.get(world_id)
        if cfg is None:
            return None
        return {"world_id": world_id, **cfg}

    def build_world_context(
        self,
        world_id: str,
        question: str,
        rag_engine,
        n_results: int = 4,
    ) -> Optional[str]:
        """
        Build a context string for OpenClaw combining:
          - World identity (tone, vocabulary, preferred scales)
          - Relevant passages retrieved from the world's ChromaDB collection

        Returns None if the world doesn't exist.
        Returns a string even if no documents are ingested yet (world params only).
        """
        world = WORLDS.get(world_id)
        if world is None:
            logger.warning(f"Unknown world_id: {world_id}")
            return None

        parts: list[str] = [
            f"## Mundo Teórico Activo: {world['name']}",
            f"Directores de referencia: {world['description']}",
            f"Vocabulario dominante: {', '.join(world['dominant_vocabulary'])}",
            f"Escalas preferidas: {', '.join(world['preferred_scales'])}",
            f"Tono: {world['agent_tone']}",
            f"\n{world['system_note']}",
        ]

        # Query the world's RAG collection for relevant passages
        chunks = rag_engine.query_with_citations(
            question=question,
            world_id=world_id,
            n_results=n_results,
        )

        if chunks:
            parts.append("\n## Contexto teórico relevante:")
            for chunk in chunks:
                citation = chunk["source"]
                if chunk.get("page"):
                    citation += f", p. {chunk['page']}"
                parts.append(f"\n[{citation}]:\n{chunk['text']}")
        else:
            parts.append(
                "\n(Biblioteca del mundo aún sin textos ingresados. "
                "Respondés desde los parámetros del mundo, sin citas textuales.)"
            )

        return "\n".join(parts)

    def format_world_header(self, world_id: str) -> str:
        """One-line summary for logging / UI display."""
        world = WORLDS.get(world_id)
        if not world:
            return f"[mundo desconocido: {world_id}]"
        return f"{world['name']} ({world['agent_tone']})"


# ─── Singleton ────────────────────────────────────────────────────────────────

_worlds_engine: Optional[WorldsEngine] = None


def get_worlds_engine() -> WorldsEngine:
    global _worlds_engine
    if _worlds_engine is None:
        _worlds_engine = WorldsEngine()
    return _worlds_engine
