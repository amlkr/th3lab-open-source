import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import Project, get_db

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    module: str                   # th3lab | visual_cult
    owner_id: Optional[str] = None
    metadata: dict = {}


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None


def _to_dict(p: Project) -> dict:
    return {
        "id":          str(p.id),
        "owner_id":    str(p.owner_id) if p.owner_id else None,
        "name":        p.name,
        "description": p.description,
        "module":      p.module,
        "metadata":    p.metadata_,
        "created_at":  p.created_at.isoformat(),
        "updated_at":  p.updated_at.isoformat(),
    }


@router.post("/")
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    """POST /api/projects/ — create a new project."""
    if body.module not in ("th3lab", "visual_cult"):
        raise HTTPException(400, "module must be 'th3lab' or 'visual_cult'")

    project = Project(
        owner_id=uuid.UUID(body.owner_id) if body.owner_id else None,
        name=body.name,
        description=body.description,
        module=body.module,
        metadata_=body.metadata,
    )
    db.add(project)
    await db.flush()
    return _to_dict(project)


@router.get("/")
async def list_projects(
    module: Optional[str] = None,
    owner_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """GET /api/projects/ — list all projects."""
    query = select(Project).order_by(Project.created_at.desc())
    if module:
        query = query.where(Project.module == module)
    if owner_id:
        query = query.where(Project.owner_id == uuid.UUID(owner_id))

    rows = (await db.execute(query)).scalars().all()
    return {"projects": [_to_dict(p) for p in rows]}


@router.get("/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """GET /api/projects/{project_id}."""
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id")

    project = await db.get(Project, pid)
    if not project:
        raise HTTPException(404, "Project not found")
    return _to_dict(project)


@router.patch("/{project_id}")
async def update_project(
    project_id: str, body: ProjectUpdate, db: AsyncSession = Depends(get_db)
):
    """PATCH /api/projects/{project_id} — partial update."""
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id")

    project = await db.get(Project, pid)
    if not project:
        raise HTTPException(404, "Project not found")

    if body.name        is not None: project.name        = body.name
    if body.description is not None: project.description = body.description
    if body.metadata    is not None: project.metadata_   = body.metadata

    await db.flush()
    return _to_dict(project)


@router.delete("/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """DELETE /api/projects/{project_id}."""
    try:
        pid = uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id")

    project = await db.get(Project, pid)
    if not project:
        raise HTTPException(404, "Project not found")

    await db.delete(project)
    return {"deleted": True, "project_id": project_id}
