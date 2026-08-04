"""
ProductTruth API — FastAPI application entry point.
"""

from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import init_db
from api.routers import products, review, stream

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
# CORS — allow the Next.js frontend and deployed Vercel origin
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting ProductTruth API", version=settings.version)
    await init_db()
    logger.info("Database initialised")


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(review.router, prefix="/api/v1/review", tags=["review"])
app.include_router(stream.router, prefix="/api/v1/stream", tags=["stream"])


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
