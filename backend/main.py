"""
Main Application Entrypoint for Unified Progressive Entity Resolution & Data Repository (PRJ-07).
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from backend.database import engine, Base
from backend.routes import api_router
from backend.config import DATABASE_URL, GEMINI_API_KEY


from backend.migrate import run_migration


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inline SQLite defensive column creation for environments without migrations
    from sqlalchemy import text
    with engine.connect() as conn:
        for table in ["workspaces", "sources", "datasets", "session_histories"]:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id TEXT;"))
                conn.commit()
            except Exception:
                pass

    # Ensure database tables and schema migrations exist on startup
    run_migration()
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

# Global catch-all CORS header injector for any 4xx/5xx or OPTIONS drops
##class SafeCORSResponseMiddleware(BaseHTTPMiddleware):
    ##async def dispatch(self, request: Request, call_next):
       # if request.method == "OPTIONS":
           # response = Response(status_code=204)
        #else:
            #try:
                #response = await call_next(request)
            #except Exception as exc:
                # Ensure 500 crashes still have CORS headers attached
                #from fastapi.responses import JSONResponse
                #response = JSONResponse(
                   # status_code=500,
                    #content={"detail": f"Internal Server Error: {str(exc)}"}
               # )

        #origin = request.headers.get("origin")
        #if origin:
            #response.headers["Access-Control-Allow-Origin"] = origin
            #response.headers["Access-Control-Allow-Credentials"] = "true"
          #  response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            #response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, Origin, X-Requested-With, X-Workspace-Id, *"
            #response.headers["Access-Control-Expose-Headers"] = "*"
        #return response


#app.add_middleware(SafeCORSResponseMiddleware)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://unified-entity-resolution-frontend.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
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
