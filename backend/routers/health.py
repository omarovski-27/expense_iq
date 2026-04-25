import os

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlmodel import Session

from database import get_session

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/detailed")
def detailed_health_check(db: Session = Depends(get_session)):
    database_status = "connected"
    try:
        db.exec(text("SELECT 1"))
    except Exception as exc:
        database_status = f"error: {exc}"

    return {
        "status": "ok",
        "database": database_status,
        "ai_service": "configured" if os.getenv("ANTHROPIC_API_KEY") else "not configured",
        "version": "1.0.0",
    }