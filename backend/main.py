"""
Main Application Entrypoint for Unified Progressive Entity Resolution & Data Repository (PRJ-07).
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.routes import api_router
from backend.config import DATABASE_URL, GEMINI_API_KEY


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Unified Progressive Entity Resolution & Data Repository (PRJ-07)",
    description=(
        "Progressive Entity Resolution engine combining deterministic rules, "
        "RapidFuzz string algorithms, and Google Gemini LLM semantic disambiguation."
    ),
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(api_router, prefix="/api")


@app.get("/")
def root():
    return {
        "project": "Unified Progressive Entity Resolution & Data Repository (PRJ-07)",
        "status": "online",
        "docs_url": "/docs",
        "database": DATABASE_URL.split("///")[-1] if "///" in DATABASE_URL else "configured",
        "gemini_active": bool(GEMINI_API_KEY and len(GEMINI_API_KEY.strip()) > 0)
    }
