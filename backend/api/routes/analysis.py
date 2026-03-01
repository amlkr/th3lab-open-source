import logging
import os
import uuid
from typing import Optional

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from core.celery_app import celery_app
from core.database import AnalysisJob, MirrorScore, VisualMap, get_db
from services.clip_engine import get_clip_engine
from services.semantic_engine import get_semantic_engine
from services.shot_analyzer import get_shot_analyzer

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/amlkr-uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _save_upload(file: UploadFile, dest: str) -> str:
    async with aiofiles.open(dest, "wb") as f:
        await f.write(await file.read())
    return dest


# ─── Celery tasks ─────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="tasks.analyze_video")
def task_analyze_video(self, job_id: str, video_path: str):
    """Shot detection + scale / movement / brightness / saturation + frame thumbnails."""
    import asyncio
    import os
    from sqlalchemy import update
    from core.database import AnalysisJob, AsyncSessionLocal, Shot

    _upload_dir   = os.getenv("UPLOAD_DIR", "/tmp/amlkr-uploads")
    thumbnail_dir = os.path.join(_upload_dir, f"{job_id}_frames")

    async def _run():
        shots = get_shot_analyzer().analyze_video(video_path, thumbnail_dir=thumbnail_dir)

        # Rewrite local thumbnail paths → server-accessible URLs
        for s in shots:
            if s.get("thumbnail_url"):
                fname = os.path.basename(s["thumbnail_url"])
                s["thumbnail_url"] = f"/static/uploads/{job_id}_frames/{fname}"

        # Aggregate scale distribution and dominant camera movement
        scale_counts:    dict[str, int] = {}
        movement_counts: dict[str, int] = {}
        for s in shots:
            scale_counts[s["shot_scale"]] = scale_counts.get(s["shot_scale"], 0) + 1
            m = s.get("camera_movement", "static")
            movement_counts[m] = movement_counts.get(m, 0) + 1
        total = len(shots) or 1
        scale_distribution = {k: round(v / total * 100) for k, v in scale_counts.items()}
        dominant_movement  = max(movement_counts, key=movement_counts.get) if movement_counts else "static"

        async with AsyncSessionLocal() as db:
            db.add_all([Shot(job_id=uuid.UUID(job_id), **s) for s in shots])
            await db.execute(
                update(AnalysisJob)
                .where(AnalysisJob.id == uuid.UUID(job_id))
                .values(status="completed", progress=100, result={
                    "shots":              shots,
                    "shot_count":         len(shots),
                    "scale_distribution": scale_distribution,
                    "dominant_movement":  dominant_movement,
                })
            )
            await db.commit()

    asyncio.run(_run())


@celery_app.task(bind=True, name="tasks.analyze_images")
def task_analyze_images(self, job_id: str, image_paths: list[str]):
    """CLIP coherence + Qwen2.5-VL per-image analysis + series report."""
    import asyncio
    from core.database import AnalysisJob, AsyncSessionLocal

    async def _run():
        clip     = get_clip_engine()
        semantic = get_semantic_engine()

        embeddings        = clip.embed_images(image_paths)
        coherence         = clip.collection_coherence(embeddings)
        semantic_results  = semantic.analyze_images_batch(image_paths)
        report            = semantic.generate_series_report(semantic_results)

        async with AsyncSessionLocal() as db:
            await db.execute(
                update(AnalysisJob)
                .where(AnalysisJob.id == uuid.UUID(job_id))
                .values(status="completed", progress=100, result={
                    "coherence": coherence,
                    "semantic_analysis": semantic_results,
                    "report": report,
                    "image_count": len(image_paths),
                })
            )
            await db.commit()

    asyncio.run(_run())


@celery_app.task(bind=True, name="tasks.build_visual_map")
def task_build_visual_map(self, job_id: str, project_id: str, user_id: Optional[str], image_paths: list[str]):
    """Módulo 1 — build Mapa Visual Interno."""
    import asyncio
    from core.database import AnalysisJob, AsyncSessionLocal, VisualMap

    async def _run():
        clip     = get_clip_engine()
        semantic = get_semantic_engine()

        embeddings       = clip.embed_images(image_paths)
        coherence        = clip.collection_coherence(embeddings)
        semantic_results = semantic.analyze_images_batch(image_paths)
        report           = semantic.generate_visual_map_report(
            semantic_results, coherence["score"], coherence["outlier_indices"]
        )

        vm = VisualMap(
            project_id=uuid.UUID(project_id),
            user_id=uuid.UUID(user_id) if user_id else None,
            image_urls=image_paths,
            clip_embeddings=[e.tolist() for e in embeddings],
            centroid=coherence["centroid"],
            coherence_score=coherence["score"],
            outlier_indices=coherence["outlier_indices"],
            semantic_analysis={"images": semantic_results},
            report=report,
        )

        async with AsyncSessionLocal() as db:
            db.add(vm)
            await db.execute(
                update(AnalysisJob)
                .where(AnalysisJob.id == uuid.UUID(job_id))
                .values(status="completed", progress=100, result={
                    "visual_map_id": str(vm.id),
                    "coherence_score": coherence["score"],
                })
            )
            await db.commit()

    asyncio.run(_run())


@celery_app.task(bind=True, name="tasks.compute_mirror_score")
def task_compute_mirror_score(
    self, job_id: str, project_id: str, user_id: Optional[str],
    visual_map_id: str, series_paths: list[str]
):
    """Módulo 3 — Modo Espejo mirror score."""
    import asyncio
    import numpy as np
    from core.database import AnalysisJob, AsyncSessionLocal, MirrorScore, VisualMap

    async def _run():
        clip     = get_clip_engine()
        semantic = get_semantic_engine()

        async with AsyncSessionLocal() as db:
            vm = await db.get(VisualMap, uuid.UUID(visual_map_id))
            if not vm or not vm.centroid:
                raise ValueError(f"VisualMap {visual_map_id} missing centroid")
            centroid     = np.array(vm.centroid, dtype=np.float32)
            map_analysis = (vm.semantic_analysis or {}).get("images", [])

        series_embeddings = clip.embed_images(series_paths)
        mirror            = clip.mirror_score(centroid, series_embeddings)
        series_analysis   = semantic.analyze_images_batch(series_paths)
        report            = semantic.generate_mirror_report(map_analysis, series_analysis, mirror["mirror_score"])

        ms = MirrorScore(
            project_id=uuid.UUID(project_id),
            user_id=uuid.UUID(user_id) if user_id else None,
            visual_map_id=uuid.UUID(visual_map_id),
            series_image_urls=series_paths,
            mirror_score=mirror["mirror_score"],
            per_image_scores=mirror["per_image_scores"],
            report=report,
        )

        async with AsyncSessionLocal() as db:
            db.add(ms)
            await db.execute(
                update(AnalysisJob)
                .where(AnalysisJob.id == uuid.UUID(job_id))
                .values(status="completed", progress=100, result={
                    "mirror_score_id": str(ms.id),
                    "mirror_score": mirror["mirror_score"],
                    "report": report,
                })
            )
            await db.commit()

    asyncio.run(_run())


@celery_app.task(bind=True, name="tasks.generate_report")
def task_generate_report(self, job_id: str, report_type: str, analysis_data: dict):
    """Standalone Qwen2.5:14b narrative report."""
    import asyncio
    from core.database import AnalysisJob, AsyncSessionLocal

    async def _run():
        semantic = get_semantic_engine()
        if report_type == "series":
            report = semantic.generate_series_report(analysis_data.get("images", []))
        elif report_type == "visual_map":
            report = semantic.generate_visual_map_report(
                analysis_data.get("images", []),
                analysis_data.get("coherence_score", 0),
                analysis_data.get("outliers", []),
            )
        elif report_type == "mirror":
            report = semantic.generate_mirror_report(
                analysis_data.get("map_analysis", []),
                analysis_data.get("series_analysis", []),
                analysis_data.get("mirror_score", 0),
            )
        else:
            raise ValueError(f"Unknown report_type: {report_type}")

        async with AsyncSessionLocal() as db:
            await db.execute(
                update(AnalysisJob)
                .where(AnalysisJob.id == uuid.UUID(job_id))
                .values(status="completed", progress=100, result={"report": report})
            )
            await db.commit()

    asyncio.run(_run())


# ─── API endpoints ────────────────────────────────────────────────────────────

@router.post("/analysis/video")
async def analyze_video(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """POST /api/analysis/video — shot detection + classification."""
    job_id     = str(uuid.uuid4())
    video_path = os.path.join(UPLOAD_DIR, f"{job_id}_{file.filename}")
    await _save_upload(file, video_path)

    job = AnalysisJob(
        id=uuid.UUID(job_id),
        project_id=uuid.UUID(project_id) if project_id else None,
        user_id=uuid.UUID(user_id) if user_id else None,
        job_type="video",
        status="processing",
        input_data={"filename": file.filename, "video_path": video_path},
    )
    db.add(job)
    await db.commit()  # commit before dispatch so the worker can find the row

    task = task_analyze_video.delay(job_id, video_path)
    job.celery_task_id = task.id
    return {"job_id": job_id, "task_id": task.id, "status": "processing"}


@router.post("/analysis/images")
async def analyze_images(
    files: list[UploadFile] = File(...),
    project_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """POST /api/analysis/images — CLIP + Qwen2.5-VL series analysis."""
    job_id = str(uuid.uuid4())
    image_paths = []
    for f in files:
        dest = os.path.join(UPLOAD_DIR, f"{job_id}_{f.filename}")
        await _save_upload(f, dest)
        image_paths.append(dest)

    job = AnalysisJob(
        id=uuid.UUID(job_id),
        project_id=uuid.UUID(project_id) if project_id else None,
        user_id=uuid.UUID(user_id) if user_id else None,
        job_type="images",
        status="processing",
        input_data={"filenames": [f.filename for f in files], "image_paths": image_paths},
    )
    db.add(job)
    await db.commit()  # commit before dispatch so the worker can find the row

    task = task_analyze_images.delay(job_id, image_paths)
    job.celery_task_id = task.id
    return {"job_id": job_id, "task_id": task.id, "status": "processing"}


@router.post("/analysis/visual-map")
async def build_visual_map(
    files: list[UploadFile] = File(...),
    project_id: str = Form(...),
    user_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """POST /api/analysis/visual-map — Módulo 1: build Mapa Visual Interno."""
    job_id = str(uuid.uuid4())
    image_paths = []
    for f in files:
        dest = os.path.join(UPLOAD_DIR, f"{job_id}_{f.filename}")
        await _save_upload(f, dest)
        image_paths.append(dest)

    job = AnalysisJob(
        id=uuid.UUID(job_id),
        project_id=uuid.UUID(project_id),
        user_id=uuid.UUID(user_id) if user_id else None,
        job_type="visual_map",
        status="processing",
        input_data={"filenames": [f.filename for f in files], "image_paths": image_paths},
    )
    db.add(job)
    await db.commit()  # commit before dispatch so the worker can find the row

    task = task_build_visual_map.delay(job_id, project_id, user_id, image_paths)
    job.celery_task_id = task.id
    return {"job_id": job_id, "task_id": task.id, "status": "processing"}


@router.post("/analysis/mirror")
async def compute_mirror(
    files: list[UploadFile] = File(...),
    project_id: str = Form(...),
    visual_map_id: str = Form(...),
    user_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """POST /api/analysis/mirror — Módulo 3: Modo Espejo, mirror score 0-100."""
    job_id = str(uuid.uuid4())
    series_paths = []
    for f in files:
        dest = os.path.join(UPLOAD_DIR, f"{job_id}_{f.filename}")
        await _save_upload(f, dest)
        series_paths.append(dest)

    job = AnalysisJob(
        id=uuid.UUID(job_id),
        project_id=uuid.UUID(project_id),
        user_id=uuid.UUID(user_id) if user_id else None,
        job_type="mirror",
        status="processing",
        input_data={
            "visual_map_id": visual_map_id,
            "filenames": [f.filename for f in files],
            "series_paths": series_paths,
        },
    )
    db.add(job)
    await db.commit()  # commit before dispatch so the worker can find the row

    task = task_compute_mirror_score.delay(job_id, project_id, user_id, visual_map_id, series_paths)
    job.celery_task_id = task.id
    return {"job_id": job_id, "task_id": task.id, "status": "processing"}


class ReportRequest(BaseModel):
    report_type: str          # series | visual_map | mirror
    analysis_data: dict
    project_id: Optional[str] = None
    user_id: Optional[str] = None


@router.post("/semantic/report")
async def generate_report(body: ReportRequest, db: AsyncSession = Depends(get_db)):
    """POST /api/semantic/report — standalone Qwen2.5:14b narrative report."""
    if body.report_type not in ("series", "visual_map", "mirror"):
        raise HTTPException(400, "report_type must be: series | visual_map | mirror")

    job_id = str(uuid.uuid4())
    job = AnalysisJob(
        id=uuid.UUID(job_id),
        project_id=uuid.UUID(body.project_id) if body.project_id else None,
        user_id=uuid.UUID(body.user_id) if body.user_id else None,
        job_type="semantic_report",
        status="processing",
        input_data={"report_type": body.report_type},
    )
    db.add(job)
    await db.commit()  # commit before dispatch so the worker can find the row

    task = task_generate_report.delay(job_id, body.report_type, body.analysis_data)
    job.celery_task_id = task.id
    return {"job_id": job_id, "task_id": task.id, "status": "processing"}
