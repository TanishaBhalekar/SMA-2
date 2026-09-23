"""
Health check and system diagnostics route.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import get_db
from backend.config import GEMINI_API_KEY
from backend.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)):
    """
    Returns backend service health, database connectivity status, and LLM configuration state.
    """
    db_connected = False
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    gemini_configured = bool(GEMINI_API_KEY and len(GEMINI_API_KEY.strip()) > 0)

    return HealthResponse(
        status="ok" if db_connected else "degraded",
        database_connected=db_connected,
        gemini_configured=gemini_configured
    )
