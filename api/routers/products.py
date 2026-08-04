"""
Products router — CRUD + pipeline trigger.
"""

from __future__ import annotations

import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database import get_db
from api.models.db import Product, ProductStatus
from api.models.schemas import ProductCreate, ProductOut, ProductSummaryOut

router = APIRouter()

UPLOAD_DIR = "uploads"


@router.get("/", response_model=list[ProductSummaryOut])
async def list_products(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
) -> list[Product]:
    """List all products (summary, no fields)."""
    result = await db.execute(
        select(Product).order_by(Product.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Product:
    """Get a single product with all fields and sources."""
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(
            selectinload(Product.fields).selectinload(
                __import__("api.models.db", fromlist=["ProductField"]).ProductField.sources
            )
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    name: str = Form(...),
    input_url: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    image_files: Optional[list[UploadFile]] = File(None),
    db: AsyncSession = Depends(get_db),
) -> Product:
    """
    Create a product record and kick off the enrichment pipeline.
    Accepts multipart/form-data so PDF and images can be uploaded alongside metadata.
    """
    import os
    import aiofiles

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Save PDF
    pdf_path: Optional[str] = None
    if pdf_file and pdf_file.filename:
        pdf_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{pdf_file.filename}")
        async with aiofiles.open(pdf_path, "wb") as f:
            content = await pdf_file.read()
            await f.write(content)

    # Save images
    image_paths: list[str] = []
    if image_files:
        for img in image_files:
            if img and img.filename:
                img_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{img.filename}")
                async with aiofiles.open(img_path, "wb") as f:
                    content = await img.read()
                    await f.write(content)
                image_paths.append(img_path)

    product = Product(
        name=name,
        status=ProductStatus.PROCESSING,
        input_pdf_path=pdf_path,
        input_image_paths=json.dumps(image_paths) if image_paths else None,
        input_url=input_url,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    # Pipeline is triggered via SSE stream endpoint (client subscribes then calls /run)
    return product


@router.post("/{product_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def trigger_pipeline(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Trigger the enrichment pipeline for an existing product.
    Clients should subscribe to /api/v1/stream/{product_id} before calling this.
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Import here to avoid circular import at module load
    from api.agents.orchestrator import OrchestratorAgent

    import asyncio
    asyncio.create_task(OrchestratorAgent().run(product_id=product_id))

    return {"message": "Pipeline started", "product_id": str(product_id)}
