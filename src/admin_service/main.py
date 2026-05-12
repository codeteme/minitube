import logging
import logging.handlers
import os
import time

import psutil
from datetime import datetime, timezone
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.video_crud_service.database import SessionLocal
from src.video_crud_service.models import Video
from src.admin_service.models import User

logging.basicConfig(level=logging.INFO)
_memory_handler = logging.handlers.MemoryHandler(
    capacity=200,
    flushLevel=logging.CRITICAL + 1,
)
logging.getLogger().addHandler(_memory_handler)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Uvicorn calls logging.config.dictConfig() on startup, which replaces all
    # root-logger handlers and removes _memory_handler. Re-attach it here so
    # the buffer captures records from the first real request onward.
    root = logging.getLogger()
    if _memory_handler not in root.handlers:
        root.addHandler(_memory_handler)
    root.setLevel(logging.INFO)
    yield


app = FastAPI(title="Admin Service", lifespan=lifespan)

_default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://vcm-52418.vm.duke.edu:5173",
    "http://vcm-52527.vm.duke.edu:5173",
]
_extra_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_start_time = time.time()
_request_count = 0


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.middleware("http")
async def count_requests(request, call_next):
    global _request_count
    _request_count += 1
    return await call_next(request)


@app.get("/health")
def health():
    """Admin service liveness check."""
    logger.info("Health check requested")
    return {"status": "ok", "service": "admin"}


@app.get("/admin/health")
def get_system_health():
    """Return admin service health status for the admin dashboard."""
    logger.info("System health check requested")
    return {"status": "ok", "service": "admin"}


@app.get("/admin/logs")
def get_logs():
    """Return recent system logs."""
    logger.info("Logs requested")
    return {
        "logs": [
            {
                "timestamp": datetime.fromtimestamp(r.created, tz=timezone.utc).isoformat(),
                "level": r.levelname,
                "logger": r.name,
                "message": r.getMessage(),
            }
            for r in _memory_handler.buffer
        ]
    }


@app.get("/admin/users/count")
def get_user_count(db: Session = Depends(get_db)):
    """Return total and active user counts."""
    logger.info("User count requested")
    total = db.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    active = db.execute(text("SELECT COUNT(*) FROM users WHERE is_active = true")).scalar() or 0
    return {"total": total, "active": active}


@app.patch("/admin/users/{user_id}/ban")
def ban_user(user_id: int, db: Session = Depends(get_db)):
    """Ban a user by ID (sets is_active=False)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    logger.info("User %s banned by admin", user_id)
    return {"user_id": user_id, "banned": True}


@app.post("/admin/auth/reset")
def reset_admin_password(email: str, db: Session = Depends(get_db)):
    """Trigger a password reset for the given admin email."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    logger.info("Password reset requested for %s", email)
    return {"email": email, "reset_sent": True}


@app.delete("/admin/content/{video_id}")
def delete_content(video_id: str, db: Session = Depends(get_db)):
    """Delete a video from storage and the database."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    file_path = Path(video.path)
    if file_path.exists():
        file_path.unlink()

    db.delete(video)
    db.commit()

    logger.info("Video %s deleted by admin", video_id)
    return {"video_id": video_id, "deleted": True}


@app.get("/admin/metrics")
def get_metrics():
    """Return real-time performance and usage metrics."""
    logger.info("Metrics requested")
    return {
        "uptime_seconds": round(time.time() - _start_time, 2),
        "total_requests": _request_count,
        "log_entries": len(_memory_handler.buffer),
        "memory_rss_mb": round(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024, 2),
    }
