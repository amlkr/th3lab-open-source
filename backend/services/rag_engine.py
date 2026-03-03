import logging
import os
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

CHROMA_PATH     = os.getenv("CHROMA_PATH", "/tmp/amlkr-chroma")
EMBED_MODEL     = "all-MiniLM-L6-v2"      # sentence-transformers, runs fully local
CHUNK_SIZE      = 800                      # characters per chunk
CHUNK_OVERLAP   = 100


# ─── Text chunking ────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping character-level chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return [c for c in chunks if len(c) > 50]  # drop tiny fragments


# ─── Document parsers ─────────────────────────────────────────────────────────

def _parse_pdf(file_path: str) -> list[tuple[str, dict]]:
    """Extract text chunks from a PDF, one chunk per page."""
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    results = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        for j, chunk in enumerate(_chunk_text(text)):
            results.append((
                chunk,
                {"source": os.path.basename(file_path), "page": i + 1, "chunk": j},
            ))
    return results


def _parse_epub(file_path: str) -> list[tuple[str, dict]]:
    """Extract text chunks from an EPUB, one chunk per HTML document item."""
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(file_path, options={"ignore_ncx": True})
    results = []
    for item in book.get_items():
        if item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        soup = BeautifulSoup(item.get_content(), "lxml")
        text = soup.get_text(separator="\n", strip=True)
        if not text.strip():
            continue
        item_name = item.get_name()
        for j, chunk in enumerate(_chunk_text(text)):
            results.append((
                chunk,
                {"source": os.path.basename(file_path), "item": item_name, "chunk": j},
            ))
    return results


def _parse_txt(file_path: str) -> list[tuple[str, dict]]:
    """Extract text chunks from a plain text or markdown file."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    results = []
    for j, chunk in enumerate(_chunk_text(text)):
        results.append((
            chunk,
            {"source": os.path.basename(file_path), "chunk": j},
        ))
    return results


def _parse_docx(file_path: str) -> list[tuple[str, dict]]:
    """Extract text chunks from a DOCX file (requires python-docx)."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError("python-docx is required for DOCX support: pip install python-docx")

    doc = Document(file_path)
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    results = []
    for j, chunk in enumerate(_chunk_text(full_text)):
        results.append((
            chunk,
            {"source": os.path.basename(file_path), "chunk": j},
        ))
    return results


def _parse_by_extension(file_path: str) -> list[tuple[str, dict]]:
    """Dispatch to the correct parser based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return _parse_pdf(file_path)
    elif ext == ".epub":
        return _parse_epub(file_path)
    elif ext in (".txt", ".md"):
        return _parse_txt(file_path)
    elif ext == ".docx":
        return _parse_docx(file_path)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")


# ─── RAGEngine ────────────────────────────────────────────────────────────────

class RAGEngine:
    """
    Document ingestion and retrieval engine.

    Storage:  ChromaDB (persistent, file-based)
    Embeddings: sentence-transformers all-MiniLM-L6-v2 (fully local, CPU/MPS)
    LLM:      Qwen2.5:14b via Ollama (for OpenClaw chat with retrieved context)

    Collection naming: one collection per user — "student_{user_id_no_dashes}"
    Each document is stored with {"library_item_id": str} metadata for filtering.
    """

    def __init__(self):
        import chromadb
        from chromadb.config import Settings
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        logger.info(f"RAGEngine initializing, chroma path: {CHROMA_PATH}")
        os.makedirs(CHROMA_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False),
        )
        self.embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
        logger.info("RAGEngine ready.")

    # ─── Collection helpers ───────────────────────────────────────────────────

    def _collection_name(self, user_id: str) -> str:
        return f"student_{user_id.replace('-', '_')}"

    def _project_collection_name(self, project_id: str) -> str:
        return f"proj_{project_id.replace('-', '')}"

    def _world_collection_name(self, world_id: str) -> str:
        return f"world_{world_id}"

    def _get_or_create_collection(self, user_id: str):
        name = self._collection_name(user_id)
        return self.client.get_or_create_collection(
            name=name, embedding_function=self.embedding_fn
        )

    def _get_or_create_named_collection(self, name: str):
        return self.client.get_or_create_collection(
            name=name, embedding_function=self.embedding_fn
        )

    # ─── Ingestion ────────────────────────────────────────────────────────────

    def ingest_pdf(self, file_path: str, user_id: str, library_item_id: str) -> list[str]:
        """
        Parse a PDF, chunk it, and store in ChromaDB.
        Returns the list of ChromaDB document IDs created.
        """
        logger.info(f"Ingesting PDF: {file_path}")
        chunks = _parse_pdf(file_path)
        return self._store_chunks(chunks, user_id, library_item_id)

    def ingest_epub(self, file_path: str, user_id: str, library_item_id: str) -> list[str]:
        """
        Parse an EPUB, chunk it, and store in ChromaDB.
        Returns the list of ChromaDB document IDs created.
        """
        logger.info(f"Ingesting EPUB: {file_path}")
        chunks = _parse_epub(file_path)
        return self._store_chunks(chunks, user_id, library_item_id)

    def ingest_txt(self, file_path: str, user_id: str, library_item_id: str) -> list[str]:
        """Parse a TXT/MD file and store in the user's ChromaDB collection."""
        logger.info(f"Ingesting TXT/MD: {file_path}")
        chunks = _parse_txt(file_path)
        return self._store_chunks(chunks, user_id, library_item_id)

    def ingest_docx(self, file_path: str, user_id: str, library_item_id: str) -> list[str]:
        """Parse a DOCX file and store in the user's ChromaDB collection."""
        logger.info(f"Ingesting DOCX: {file_path}")
        chunks = _parse_docx(file_path)
        return self._store_chunks(chunks, user_id, library_item_id)

    def ingest_document(
        self,
        file_path: str,
        project_id: str,
        world_id: Optional[str] = None,
        doc_id: Optional[str] = None,
    ) -> list[str]:
        """
        Parse any supported document (PDF/EPUB/TXT/MD/DOCX) and store it in
        either a project collection or a world collection.

        Args:
            file_path  — path to the file on disk
            project_id — scopes the collection (always required)
            world_id   — if provided, stored in the world collection instead
            doc_id     — optional stable identifier stored in metadata

        Returns the list of ChromaDB document IDs created.
        """
        logger.info(f"Ingesting document (project={project_id}, world={world_id}): {file_path}")
        chunks = _parse_by_extension(file_path)

        ext = os.path.splitext(file_path)[1].lower().lstrip(".")
        extra: dict = {"file_type": ext}
        if doc_id:
            extra["doc_id"] = doc_id
        if world_id:
            extra["world_id"] = world_id
        else:
            extra["project_id"] = project_id

        tagged = [(text, {**meta, **extra}) for text, meta in chunks]

        collection_name = (
            self._world_collection_name(world_id)
            if world_id
            else self._project_collection_name(project_id)
        )
        collection = self._get_or_create_named_collection(collection_name)
        return self._store_chunks_to_named(tagged, collection)

    def _store_chunks(
        self,
        chunks: list[tuple[str, dict]],
        user_id: str,
        library_item_id: str,
    ) -> list[str]:
        if not chunks:
            logger.warning(f"No chunks extracted for library_item {library_item_id}")
            return []

        collection = self._get_or_create_collection(user_id)
        doc_ids    = [str(uuid.uuid4()) for _ in chunks]
        documents  = [c[0] for c in chunks]
        metadatas  = [{**c[1], "library_item_id": library_item_id} for c in chunks]

        # ChromaDB add in batches of 500 to avoid memory spikes
        batch_size = 500
        for i in range(0, len(doc_ids), batch_size):
            collection.add(
                ids=doc_ids[i : i + batch_size],
                documents=documents[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )

        logger.info(f"Stored {len(doc_ids)} chunks for item {library_item_id}")
        return doc_ids

    def _store_chunks_to_named(
        self,
        chunks: list[tuple[str, dict]],
        collection,
    ) -> list[str]:
        """Store pre-tagged chunks directly into any named collection."""
        if not chunks:
            return []

        doc_ids   = [str(uuid.uuid4()) for _ in chunks]
        documents = [c[0] for c in chunks]
        metadatas = [c[1] for c in chunks]

        batch_size = 500
        for i in range(0, len(doc_ids), batch_size):
            collection.add(
                ids=doc_ids[i : i + batch_size],
                documents=documents[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )

        logger.info(f"Stored {len(doc_ids)} chunks in collection '{collection.name}'")
        return doc_ids

    # ─── Deletion ────────────────────────────────────────────────────────────

    def delete_item(self, user_id: str, library_item_id: str) -> int:
        """
        Remove all ChromaDB documents belonging to a library item.
        Returns the number of documents deleted.
        """
        try:
            collection = self._get_or_create_collection(user_id)
            existing = collection.get(where={"library_item_id": library_item_id})
            ids_to_delete = existing["ids"]
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
            logger.info(f"Deleted {len(ids_to_delete)} chunks for item {library_item_id}")
            return len(ids_to_delete)
        except Exception as e:
            logger.error(f"Error deleting item {library_item_id}: {e}")
            return 0

    # ─── Retrieval ────────────────────────────────────────────────────────────

    def query(
        self,
        user_id: str,
        query_text: str,
        n_results: int = 6,
        library_item_ids: Optional[list[str]] = None,
    ) -> list[str]:
        """
        Retrieve the most relevant text chunks for a query from the user's collection.

        Args:
            user_id           — scopes the search to this student's collection
            query_text        — natural-language query
            n_results         — number of chunks to retrieve
            library_item_ids  — if provided, restrict to these specific items

        Returns list of text chunks, most relevant first.
        """
        try:
            collection = self._get_or_create_collection(user_id)
            if collection.count() == 0:
                return []

            where: Optional[dict] = None
            if library_item_ids:
                if len(library_item_ids) == 1:
                    where = {"library_item_id": library_item_ids[0]}
                else:
                    where = {"library_item_id": {"$in": library_item_ids}}

            kwargs: dict = {"query_texts": [query_text], "n_results": min(n_results, collection.count())}
            if where:
                kwargs["where"] = where

            results = collection.query(**kwargs)
            return results["documents"][0] if results["documents"] else []
        except Exception as e:
            logger.error(f"RAG query error for user {user_id}: {e}")
            return []

    def build_rag_context(
        self,
        user_id: str,
        query_text: str,
        library_item_ids: Optional[list[str]] = None,
        n_results: int = 6,
    ) -> Optional[str]:
        """
        Retrieve chunks and format them as a context string for OpenClaw.
        Returns None if no relevant documents found.
        """
        chunks = self.query(user_id, query_text, n_results=n_results,
                            library_item_ids=library_item_ids)
        if not chunks:
            return None
        return "\n\n---\n\n".join(chunks)

    def query_with_citations(
        self,
        question: str,
        project_id: Optional[str] = None,
        world_id: Optional[str] = None,
        n_results: int = 5,
    ) -> list[dict]:
        """
        Query a project or world collection and return chunks with source citations.

        Returns a list of dicts: {text, source, page, item, doc_id}
        """
        if world_id:
            name = self._world_collection_name(world_id)
        elif project_id:
            name = self._project_collection_name(project_id)
        else:
            return []

        try:
            collection = self._get_or_create_named_collection(name)
            if collection.count() == 0:
                return []

            results = collection.query(
                query_texts=[question],
                n_results=min(n_results, collection.count()),
                include=["documents", "metadatas"],
            )

            out = []
            for text, meta in zip(results["documents"][0], results["metadatas"][0]):
                out.append({
                    "text":   text,
                    "source": meta.get("source", ""),
                    "page":   meta.get("page"),
                    "item":   meta.get("item"),
                    "doc_id": meta.get("doc_id"),
                })
            return out
        except Exception as e:
            logger.error(f"query_with_citations error (name={name}): {e}")
            return []

    def list_documents(self, project_id: str) -> list[dict]:
        """
        List all ingested documents in a project's collection,
        aggregated by source filename.

        Returns list of {source, doc_id, file_type, chunk_count}.
        """
        try:
            name       = self._project_collection_name(project_id)
            collection = self._get_or_create_named_collection(name)
            if collection.count() == 0:
                return []

            result = collection.get(include=["metadatas"])
            docs: dict[str, dict] = {}
            for meta in result["metadatas"]:
                source = meta.get("source", "unknown")
                if source not in docs:
                    docs[source] = {
                        "source":      source,
                        "doc_id":      meta.get("doc_id", source),
                        "file_type":   meta.get("file_type", "unknown"),
                        "chunk_count": 0,
                    }
                docs[source]["chunk_count"] += 1

            return list(docs.values())
        except Exception as e:
            logger.error(f"list_documents error (project={project_id}): {e}")
            return []

    # ─── Document stats ───────────────────────────────────────────────────────

    def collection_stats(self, user_id: str) -> dict:
        """Return basic stats for a student's collection."""
        try:
            collection = self._get_or_create_collection(user_id)
            return {"total_chunks": collection.count(), "collection": self._collection_name(user_id)}
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {"total_chunks": 0, "collection": self._collection_name(user_id)}


# Singleton
_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
