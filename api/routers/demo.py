"""
Demo router — zero-config pipeline runner for live hackathon evaluations.
Uses bundled sample datasheet without requiring user file uploads or API keys.
"""

from __future__ import annotations

import asyncio
import pathlib

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.db import Product, ProductStatus

router = APIRouter()

DEMO_PDF = pathlib.Path("api/fixtures/sample_siemens_3rt2015_datasheet.pdf")


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
async def run_demo(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """
    Zero-config live demo endpoint.
    Uses bundled Siemens 3RT2015 datasheet, creates product, and runs pipeline.
    """
    from api.agents.orchestrator import OrchestratorAgent

    pdf_path = str(DEMO_PDF) if DEMO_PDF.exists() else None

    product = Product(
        name="Siemens 3RT2015 (demo)",
        status=ProductStatus.PROCESSING,
        input_pdf_path=pdf_path,
        input_image_paths=None,
        input_url=None,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    # Launch pipeline background task
    asyncio.create_task(OrchestratorAgent().run(product_id=product.id))

    return {
        "message": "Demo pipeline started",
        "product_id": str(product.id),
        "name": product.name,
    }
