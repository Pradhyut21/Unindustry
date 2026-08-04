"""
SQLAlchemy ORM models for ProductTruth.

Tables:
  products        — one row per product being enriched
  product_fields  — one row per extracted field (with confidence + source info)
  field_sources   — one row per source that contributed to a field value
  review_queue    — HITL review actions on low-confidence fields
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ProductStatus(str, enum.Enum):
    PROCESSING = "processing"
    PENDING_REVIEW = "pending_review"
    COMPLETE = "complete"
    FAILED = "failed"


class VerificationStatus(str, enum.Enum):
    VERIFIED = "verified"  # ≥2 independent sources agree
    SINGLE_SOURCE = "single_source"
    CONTRADICTION = "contradiction"
    PENDING = "pending"
    HUMAN_ACCEPTED = "human_accepted"
    HUMAN_EDITED = "human_edited"
    HUMAN_REJECTED = "human_rejected"


class UncertaintyReason(str, enum.Enum):
    """
    Why a field has low confidence — visible in output, not just a raw number.
    This is the hallucination-taxonomy-style classification the verifier assigns.
    """

    NONE = "none"  # fully verified
    SINGLE_SOURCE = "single_source"  # only one source found
    SOURCE_CONTRADICTION = "source_contradiction"  # sources disagree
    LOW_QUALITY_EXTRACTION = "low_quality_extraction"  # noisy extract (OCR, etc.)
    NO_SOURCE_FOUND = "no_source_found"  # couldn't find any source


class SourceType(str, enum.Enum):
    DOC = "doc"  # parsed from PDF / datasheet
    IMAGE = "image"  # extracted via VLM from product photo
    WEB = "web"  # retrieved via RAG / web search
    KG = "kg"  # from internal knowledge graph (past verified products)
    HUMAN = "human"  # HITL correction


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus), default=ProductStatus.PROCESSING, nullable=False
    )
    input_pdf_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    input_image_paths: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    input_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    fields: Mapped[list[ProductField]] = relationship(
        "ProductField", back_populates="product", cascade="all, delete-orphan"
    )


class ProductField(Base):
    __tablename__ = "product_fields"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(256), nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # When verification_status == CONTRADICTION, this stores the losing value
    # so the frontend can show both sides without parsing source snippets.
    contradicting_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus), default=VerificationStatus.PENDING, nullable=False
    )
    uncertainty_reason: Mapped[UncertaintyReason] = mapped_column(
        Enum(UncertaintyReason), default=UncertaintyReason.NONE, nullable=False
    )
    schema_field_id: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True
    )  # maps to ETIM field ID e.g. "EF000001"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    product: Mapped[Product] = relationship("Product", back_populates="fields")
    sources: Mapped[list[FieldSource]] = relationship(
        "FieldSource", back_populates="field", cascade="all, delete-orphan"
    )
    review: Mapped[Optional[ReviewQueueItem]] = relationship(
        "ReviewQueueItem", back_populates="field", uselist=False
    )


class FieldSource(Base):
    __tablename__ = "field_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_fields.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    # Human-readable reference: filename+page, image filename, URL, "internal KG"
    source_ref: Mapped[str] = mapped_column(String(2048), nullable=False)
    # The snippet / region that justified the value
    extracted_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_agent: Mapped[str] = mapped_column(String(128), nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    field: Mapped[ProductField] = relationship("ProductField", back_populates="sources")


class ReviewQueueItem(Base):
    __tablename__ = "review_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_fields.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False
    )
    reviewer: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    human_corrected_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    field: Mapped[ProductField] = relationship("ProductField", back_populates="review")
