import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from core.database import Base, engine
from api.routes import analysis, auth, chat, jobs, library, projects

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AMLKR Dashboard API...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Column-level migrations (safe to run repeatedly)
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"
        ))
    logger.info("Database tables ready.")
    yield
    logger.info("Shutting down...")
    await engine.dispose()


app = FastAPI(
    title="AMLKR Dashboard API",
    description="AI-powered visual analysis — th3lab + VISUAL CULT",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",               # results page (same server)
        "http://localhost:5173",               # Vite dev
        "http://localhost:3000",
        "https://amlkr-dashboard.vercel.app",  # production Vercel
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(auth.router,              prefix="/api/auth",     tags=["auth"])
app.include_router(chat.router,              prefix="/api/chat",     tags=["chat"])
app.include_router(analysis.router,          prefix="/api",          tags=["analysis"])
app.include_router(jobs.router,              prefix="/api/jobs",     tags=["jobs"])
app.include_router(projects.router,          prefix="/api/projects", tags=["projects"])
app.include_router(library.users_router,     prefix="/api/users",    tags=["users"])
app.include_router(library.library_router,   prefix="/api/library",  tags=["library"])
app.include_router(library.chat_router,      prefix="/api/chat",     tags=["chat"])


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "service": "amlkr-dashboard-api", "version": "0.1.0"}


@app.get("/results", tags=["ui"])
async def results_page():
    return FileResponse(os.path.join(os.path.dirname(__file__), "results.html"))


# ─── Static file serving ─────────────────────────────────────────────────────
_upload_dir = os.getenv("UPLOAD_DIR", "/tmp/amlkr-uploads")
os.makedirs(_upload_dir, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=_upload_dir), name="uploads")
app.mount("/uploads",        StaticFiles(directory=_upload_dir), name="uploads_short")
