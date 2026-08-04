"""
Pydantic schemas for request/response validation.
Kept separate from SQLAlchemy ORM models (api/models/db.py).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from api.models.db import (
    ProductStatus,
    ReviewStatus,
    SourceType,
    UncertaintyReason,
    VerificationStatus,
)

# ---------------------------------------------------------------------------
# Field Sources
# ---------------------------------------------------------------------------


class FieldSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_type: SourceType
    source_ref: str
    extracted_snippet: Optional[str]
    extraction_agent: str
    extracted_at: datetime


# ---------------------------------------------------------------------------
# Product Fields
# ---------------------------------------------------------------------------


class ProductFieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    field_name: str
    value: Optional[str]
    contradicting_value: Optional[str] = None  # populated when verification_status == contradiction
    confidence: float
    verification_status: VerificationStatus
    uncertainty_reason: UncertaintyReason
    schema_field_id: Optional[str]
    sources: list[FieldSourceOut] = []
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=512)
    input_url: Optional[str] = Field(None, max_length=2048)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: Optional[str]
    status: ProductStatus
    created_at: datetime
    updated_at: datetime
    fields: list[ProductFieldOut] = []


class ProductSummaryOut(BaseModel):
    """Lightweight product list item — no fields."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: Optional[str]
    status: ProductStatus
    created_at: datetime


# ---------------------------------------------------------------------------
# Review Queue
# ---------------------------------------------------------------------------


class ReviewQueueItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    field_id: uuid.UUID
    status: ReviewStatus
    reviewer: Optional[str]
    reviewed_at: Optional[datetime]
    human_corrected_value: Optional[str]
    field: ProductFieldOut


class ReviewActionRequest(BaseModel):
    action: ReviewStatus  # accepted | edited | rejected
    reviewer: str = Field(..., min_length=1, max_length=256)
    human_corrected_value: Optional[str] = None  # required if action == edited


# ---------------------------------------------------------------------------
# Pipeline / SSE
# ---------------------------------------------------------------------------


class PipelineStartRequest(BaseModel):
    product_id: uuid.UUID


class AgentEvent(BaseModel):
    """
    Emitted over SSE as each agent completes or updates.
    Frontend uses this to animate agent cards.
    """

    event_type: str  # "agent_start" | "agent_complete" | "agent_error" | "pipeline_complete"
    agent_name: str
    message: str
    partial_fields: Optional[list[ProductFieldOut]] = None
    product_id: Optional[uuid.UUID] = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    db: str
    version: str
