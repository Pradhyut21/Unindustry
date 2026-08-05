"""
ProductTruth API — FastAPI application entry point.
"""

from __future__ import annotations

import io
import logging
import sys

# Force UTF-8 output on Windows (default is cp1252, which can't encode ≥, →, —)
# This prevents UnicodeEncodeError from crashing background pipeline tasks.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import init_db
from api.routers import demo, products, review, stream

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="ProductTruth API",
    description=(
        "AI-powered product intelligence engine. "
        "Every field is confidence-scored and traceable to its source."
    ),
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow the Next.js frontend (dev + Vercel previews)
# NOTE: CORSMiddleware does NOT support wildcards mid-string in allow_origins.
# Use allow_origin_regex for *.vercel.app pattern.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # needed for SSE EventSource to read headers
)


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting ProductTruth API", version=settings.version)
    try:
        await init_db()
        logger.info("Database initialised")
    except Exception as exc:
        logger.warning(
            "Database initialisation failed on startup (server starting in fallback/degraded mode)",
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(review.router, prefix="/api/v1/review", tags=["review"])
app.include_router(stream.router, prefix="/api/v1/stream", tags=["stream"])
app.include_router(demo.router, prefix="/api/v1/demo", tags=["demo"])


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    """
    Health check endpoint.
    Returns 200 with DB connectivity status.
    Used by docker-compose healthcheck and CI smoke test.
    """
    from sqlalchemy import text

    from api.database import AsyncSessionLocal

    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_status = f"error: {exc}"
        logging.error("DB health check failed", exc_info=exc)

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "version": settings.version,
    }
