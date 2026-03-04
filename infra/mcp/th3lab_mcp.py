import os
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


BACKEND_URL = os.getenv("MCP_BACKEND_URL", "http://localhost:8000")
PROJECT_ROOT = Path(os.getenv("MCP_PROJECT_ROOT", "/workspace"))
ALLOWED_EXT = {".pdf", ".epub", ".txt", ".md", ".docx"}

app = FastAPI(title="th3lab MCP Bridge", version="0.1.0")


class IngestWorldRequest(BaseModel):
    world_id: str = Field(description="amniotic | cine_lentitud | cuerpo_politico")
    path: str = Field(description="File path or directory inside PROJECT_ROOT")
    project_id: str = Field(default="_admin")


class QueryWorldRequest(BaseModel):
    world_id: str
    question: str
    n_results: int = 5


class AskWorldRequest(BaseModel):
    world_id: str
    message: str
    project_id: Optional[str] = None


def _resolve_path(path_value: str) -> Path:
    raw = Path(path_value)
    if raw.is_absolute():
        resolved = raw.resolve()
    else:
        resolved = (PROJECT_ROOT / raw).resolve()
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {resolved}")
    return resolved


def _iter_ingest_files(base: Path) -> list[Path]:
    if base.is_file():
        if base.suffix.lower() not in ALLOWED_EXT:
            raise HTTPException(status_code=400, detail=f"Unsupported extension: {base.suffix}")
        return [base]

    files: list[Path] = []
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in ALLOWED_EXT:
            files.append(p)
    if not files:
        raise HTTPException(status_code=400, detail="No ingestible files found in directory")
    return files


@app.get("/health")
async def health():
    return {"status": "ok", "service": "th3lab-mcp-bridge"}


@app.post("/mcp/world/ingest")
async def ingest_world(req: IngestWorldRequest):
    target = _resolve_path(req.path)
    files = _iter_ingest_files(target)

    results = []
    async with httpx.AsyncClient(timeout=120.0) as client:
        for f in files:
            with f.open("rb") as fp:
                resp = await client.post(
                    f"{BACKEND_URL}/api/library/worlds/{req.world_id}/ingest",
                    data={"project_id": req.project_id},
                    files={"file": (f.name, fp, "application/octet-stream")},
                )
            if resp.status_code >= 400:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail={"file": str(f), "backend_error": resp.text},
                )
            results.append(resp.json())

    return {"world_id": req.world_id, "files_ingested": len(results), "results": results}


@app.post("/mcp/world/query")
async def query_world(req: QueryWorldRequest):
    payload = {"question": req.question, "world_id": req.world_id, "n_results": req.n_results}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{BACKEND_URL}/api/library/query", json=payload)
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@app.post("/mcp/world/ask")
async def ask_world(req: AskWorldRequest):
    payload = {"message": req.message, "history": [], "world_id": req.world_id}
    if req.project_id:
        payload["project_id"] = req.project_id
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{BACKEND_URL}/api/chat/", json=payload)
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
