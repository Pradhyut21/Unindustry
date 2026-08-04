"""
Review queue router — HITL accept / edit / reject per field.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database import get_db
from api.models.db import (
    FieldSource,
    ProductField,
    ReviewQueueItem,
    ReviewStatus,
    SourceType,
    UncertaintyReason,
    VerificationStatus,
)
from api.models.schemas import ReviewActionRequest, ReviewQueueItemOut

router = APIRouter()


@router.get("/", response_model=list[ReviewQueueItemOut])
async def list_review_queue(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
) -> list[ReviewQueueItem]:
    """List all pending review items with their field + sources."""
    result = await db.execute(
        select(ReviewQueueItem)
        .where(ReviewQueueItem.status == ReviewStatus.PENDING)
        .options(selectinload(ReviewQueueItem.field).selectinload(ProductField.sources))
        .order_by(ReviewQueueItem.id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.post("/{item_id}/action", response_model=ReviewQueueItemOut)
async def review_action(
    item_id: uuid.UUID,
    body: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
) -> ReviewQueueItem:
    """
    Accept, edit, or reject a review queue item.

    - accepted: field goes live as-is
    - edited: human-provided value replaces AI value; logged as a KG source
    - rejected: field is cleared and marked for re-extraction or removal
    """
    if body.action == ReviewStatus.EDITED and not body.human_corrected_value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="human_corrected_value is required when action is 'edited'",
        )

    result = await db.execute(
        select(ReviewQueueItem)
        .where(ReviewQueueItem.id == item_id)
        .options(selectinload(ReviewQueueItem.field).selectinload(ProductField.sources))
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    if item.status != ReviewStatus.PENDING:
        raise HTTPException(status_code=409, detail=f"Item already actioned: {item.status}")

    item.status = body.action
    item.reviewer = body.reviewer
    item.reviewed_at = datetime.now(timezone.utc)

    field: ProductField = item.field

    if body.action == ReviewStatus.ACCEPTED:
        field.verification_status = VerificationStatus.HUMAN_ACCEPTED
        field.confidence = 1.0
        field.uncertainty_reason = UncertaintyReason.NONE

    elif body.action == ReviewStatus.EDITED:
        item.human_corrected_value = body.human_corrected_value
        field.value = body.human_corrected_value
        field.verification_status = VerificationStatus.HUMAN_EDITED
        field.confidence = 1.0
        field.uncertainty_reason = UncertaintyReason.NONE

        # Log the human correction as a KG source for future pipeline runs
        kg_source = FieldSource(
            field_id=field.id,
            source_type=SourceType.HUMAN,
            source_ref=f"human_review:{body.reviewer}",
            extracted_snippet=body.human_corrected_value,
            extraction_agent="hitl_review",
        )
        db.add(kg_source)

    elif body.action == ReviewStatus.REJECTED:
        field.value = None
        field.verification_status = VerificationStatus.HUMAN_REJECTED
        field.confidence = 0.0

    await db.commit()
    result = await db.execute(
        select(ReviewQueueItem)
        .where(ReviewQueueItem.id == item_id)
        .options(selectinload(ReviewQueueItem.field).selectinload(ProductField.sources))
    )
    return result.scalar_one()
