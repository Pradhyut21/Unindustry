"""
Orchestrator Agent — the conductor of the ProductTruth pipeline.

Responsibilities:
1. Load the product record and inspect available inputs
2. Dispatch to Doc-Intel, Vision, and Retrieval agents in parallel where possible
3. Merge all CandidateValue outputs into a per-field candidate list
4. Hand off to Verifier Agent for confidence scoring
5. Hand off to Schema Mapper for ETIM normalisation
6. Route low-confidence fields to HITL queue
7. Persist everything to the database
8. Emit SSE events throughout so the frontend can animate agent progress

This is the entry point called by /api/v1/products/{id}/run.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Optional

import structlog
from sqlalchemy import select

from api.agents.base import BaseAgent
from api.agents.doc_intel_agent import DocIntelAgent
from api.agents.hitl_router import HITLRouter
from api.agents.retrieval_agent import RetrievalAgent
from api.agents.schema_mapper import SchemaMappingAgent
from api.agents.verifier_agent import CandidateValue, VerificationResult, VerifierAgent
from api.config import settings
from api.database import AsyncSessionLocal
from api.models.db import (
    FieldSource,
    Product,
    ProductField,
    ProductStatus,
    ReviewQueueItem,
    ReviewStatus,
)

logger = structlog.get_logger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Orchestrates the full ProductTruth enrichment pipeline.
    Called as a background asyncio task.
    """

    name = "orchestrator"

    async def run(self, product_id: uuid.UUID, **kwargs) -> None:  # type: ignore[override]
        """
        Main pipeline entry point.
        Loads the product, dispatches agents, merges results, persists to DB.
        """
        async with AsyncSessionLocal() as db:
            # Load product
            result = await db.execute(select(Product).where(Product.id == product_id))
            product: Optional[Product] = result.scalar_one_or_none()
            if not product:
                logger.error("Product not found", product_id=str(product_id))
                return

            await self.emit_event(
                product_id,
                "agent_start",
                f"Pipeline starting for '{product.name}'...",
            )

            # ---------------------------------------------------------------
            # EXTRACTION PHASE — run doc + vision in parallel, then retrieval
            # ---------------------------------------------------------------

            image_paths: list[str] = []
            if product.input_image_paths:
                try:
                    image_paths = json.loads(product.input_image_paths)
                except (json.JSONDecodeError, TypeError):
                    image_paths = []

            doc_agent = DocIntelAgent()
            vision_agent = __import__(
                "api.agents.vision_agent", fromlist=["VisionAgent"]
            ).VisionAgent()

            # Run doc and vision extraction in parallel
            doc_task = asyncio.create_task(
                doc_agent.run(product_id=product_id, pdf_path=product.input_pdf_path)
            )
            vision_task = asyncio.create_task(
                vision_agent.run(product_id=product_id, image_paths=image_paths)
            )

            doc_candidates, vision_candidates = await asyncio.gather(doc_task, vision_task)

            # Merge all candidates per field
            merged: dict[str, list[CandidateValue]] = {}
            for field_name, candidates in doc_candidates.items():
                merged.setdefault(field_name, []).extend(candidates)
            for field_name, candidates in vision_candidates.items():
                merged.setdefault(field_name, []).extend(candidates)

            # Determine missing fields for retrieval
            all_known_fields = {
                fn: candidates[0].value for fn, candidates in merged.items() if candidates
            }
            target_fields = [
                "voltage_rating",
                "current_rating",
                "power_rating",
                "frequency",
                "ip_rating",
                "operating_temperature",
                "dimensions",
                "weight",
                "material",
                "certifications",
                "model_number",
                "manufacturer",
                "product_category",
                "description",
            ]
            missing_fields = [f for f in target_fields if f not in merged]

            # Retrieval for missing fields
            retrieval_agent = RetrievalAgent()
            retrieval_candidates = await retrieval_agent.run(
                product_id=product_id,
                product_name=product.name,
                missing_fields=missing_fields,
                known_fields=all_known_fields,
            )
            for field_name, candidates in retrieval_candidates.items():
                merged.setdefault(field_name, []).extend(candidates)

            # ---------------------------------------------------------------
            # VERIFICATION PHASE
            # ---------------------------------------------------------------

            verifier = VerifierAgent()
            verified: dict[str, VerificationResult] = await verifier.run(
                product_id=product_id,
                field_candidates=merged,
                min_sources=settings.min_sources_for_verified,
            )

            # ---------------------------------------------------------------
            # SCHEMA MAPPING PHASE
            # ---------------------------------------------------------------

            mapper = SchemaMappingAgent()
            _commerce_record = await mapper.run(
                product_id=product_id,
                verified_fields=verified,
            )

            # ---------------------------------------------------------------
            # PERSIST TO DATABASE
            # ---------------------------------------------------------------

            await self.emit_event(
                product_id, "agent_start", "Persisting verified fields to database..."
            )

            hitl_count = 0
            for field_name, result in verified.items():
                pf = ProductField(
                    product_id=product_id,
                    field_name=field_name,
                    value=result.final_value,
                    # If sources contradict, store the losing value for display
                    contradicting_value=(
                        result.contradicting_sources[0].value
                        if result.contradicting_sources
                        else None
                    ),
                    confidence=result.confidence,
                    verification_status=result.verification_status,
                    uncertainty_reason=result.uncertainty_reason,
                )
                db.add(pf)
                await db.flush()  # get pf.id

                # Persist sources
                all_sources = result.agreeing_sources + result.contradicting_sources
                for src in all_sources:
                    fs = FieldSource(
                        field_id=pf.id,
                        source_type=src.source_type,
                        source_ref=src.source_ref,
                        extracted_snippet=src.extracted_snippet,
                        extraction_agent=src.extraction_agent,
                    )
                    db.add(fs)

                # Route to HITL if confidence below threshold
                if result.confidence < settings.confidence_threshold:
                    rq = ReviewQueueItem(
                        field_id=pf.id,
                        status=ReviewStatus.PENDING,
                    )
                    db.add(rq)
                    hitl_count += 1

            # Determine product category from verified fields
            if "product_category" in verified and verified["product_category"].final_value:
                product.category = verified["product_category"].final_value

            product.status = (
                ProductStatus.PENDING_REVIEW if hitl_count > 0 else ProductStatus.COMPLETE
            )
            await db.commit()

            # ---------------------------------------------------------------
            # HITL ROUTING
            # ---------------------------------------------------------------

            hitl_router = HITLRouter()
            await hitl_router.run(product_id=product_id, hitl_count=hitl_count)

            # ---------------------------------------------------------------
            # DONE
            # ---------------------------------------------------------------

            await self.emit_event(
                product_id,
                "pipeline_complete",
                f"Pipeline complete. {len(verified)} fields extracted, "
                f"{hitl_count} routed to human review.",
                data={
                    "product_id": str(product_id),
                    "total_fields": len(verified),
                    "hitl_count": hitl_count,
                    "status": product.status.value,
                },
            )
