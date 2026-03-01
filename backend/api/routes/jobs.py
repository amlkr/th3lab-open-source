import uuid
from typing import Optional

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.celery_app import celery_app
from core.database import AnalysisJob, get_db

router = APIRouter()


@router.get("/{job_id}")
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """GET /api/jobs/{job_id} — job status + result."""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(400, "Invalid job_id")

    job = await db.get(AnalysisJob, job_uuid)
    if not job:
        raise HTTPException(404, "Job not found")

    # Sync status from Celery if still in-flight
    if job.status == "processing" and job.celery_task_id:
        result = AsyncResult(job.celery_task_id, app=celery_app)
        if result.state == "FAILURE":
            job.status = "failed"
            job.error_message = str(result.result)
            await db.commit()
        elif result.state == "SUCCESS" and job.status != "completed":
            job.status = "completed"
            job.progress = 100
            await db.commit()

    return {
        "job_id":        str(job.id),
        "project_id":    str(job.project_id)   if job.project_id else None,
        "user_id":       str(job.user_id)       if job.user_id    else None,
        "job_type":      job.job_type,
        "status":        job.status,
        "progress":      job.progress,
        "input_data":    job.input_data,
        "result":        job.result,
        "error_message": job.error_message,
        "created_at":    job.created_at.isoformat(),
        "updated_at":    job.updated_at.isoformat(),
    }


@router.get("/")
async def list_jobs(
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """GET /api/jobs/ — list jobs with optional filters."""
    query = (
        select(AnalysisJob)
        .order_by(AnalysisJob.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if project_id:
        query = query.where(AnalysisJob.project_id == uuid.UUID(project_id))
    if user_id:
        query = query.where(AnalysisJob.user_id == uuid.UUID(user_id))
    if status:
        query = query.where(AnalysisJob.status == status)
    if job_type:
        query = query.where(AnalysisJob.job_type == job_type)

    rows = (await db.execute(query)).scalars().all()

    return {
        "jobs": [
            {
                "job_id":     str(j.id),
                "project_id": str(j.project_id) if j.project_id else None,
                "user_id":    str(j.user_id)    if j.user_id    else None,
                "job_type":   j.job_type,
                "status":     j.status,
                "progress":   j.progress,
                "created_at": j.created_at.isoformat(),
            }
            for j in rows
        ],
        "total": len(rows),
    }
