import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "amlkr_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "api.routes.analysis",
        "api.routes.library",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # solo pool — no forking, required on macOS Apple Silicon to avoid
    # SIGABRT from MPSGraphObject / Metal GPU conflict with prefork
    worker_pool="solo",
    result_expires=86400,   # 24 hours
    broker_connection_retry_on_startup=True,
    # task_routes removed — all tasks go to the default "celery" queue so the
    # worker picks them up without needing -Q flags. Re-enable with named queues
    # in production when running separate workers per queue type.
)
