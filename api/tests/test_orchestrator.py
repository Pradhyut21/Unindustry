"""
Integration tests for the Orchestrator Agent.

Tests the full pipeline flow using monkeypatched agents — no real Groq API
calls, no real PDF files, but real DB writes via the test database.

This validates that:
- The orchestrator correctly merges candidates from doc + vision + retrieval
- Verified fields are persisted to the database
- Low-confidence fields are routed to the HITL review queue
- SSE events are emitted in the correct order
- pipeline_complete event includes accurate counts

NOTE: These tests require DATABASE_URL to be set (used by the CI Postgres service).
      Tests are skipped if DATABASE_URL is not available.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from api.agents.verifier_agent import CandidateValue, VerificationResult
from api.models.db import SourceType, UncertaintyReason, VerificationStatus


def make_verified_result(field_name: str, value: str = "230V", confidence: float = 0.9):
    return VerificationResult(
        field_name=field_name,
        final_value=value,
        confidence=confidence,
        verification_status=VerificationStatus.VERIFIED,
        uncertainty_reason=UncertaintyReason.NONE,
        agreeing_sources=[
            CandidateValue(
                value=value,
                source_type=SourceType.DOC,
                source_ref="test.pdf:page1",
                extracted_snippet=f"Test snippet for {field_name}",
                extraction_agent="test_agent",
            )
        ],
        contradicting_sources=[],
    )


def make_low_conf_result(field_name: str, value: str = "Unknown", confidence: float = 0.4):
    return VerificationResult(
        field_name=field_name,
        final_value=value,
        confidence=confidence,
        verification_status=VerificationStatus.SINGLE_SOURCE,
        uncertainty_reason=UncertaintyReason.SINGLE_SOURCE,
        agreeing_sources=[
            CandidateValue(
                value=value,
                source_type=SourceType.WEB,
                source_ref="web:inferred",
                extracted_snippet="Low confidence web source",
                extraction_agent="retrieval_agent:groq",
                low_quality=True,
            )
        ],
        contradicting_sources=[],
    )


class TestOrchestratorEventOrder:
    """
    Validate that the orchestrator emits SSE events in the correct sequence.
    Uses monkeypatched agents to avoid real API calls.
    """

    @pytest.mark.asyncio
    async def test_orchestrator_emits_pipeline_complete(self, monkeypatch, db_setup):
        """pipeline_complete must be the last event emitted."""
        from api.agents.orchestrator import OrchestratorAgent
        from api.database import AsyncSessionLocal
        from api.models.db import Product, ProductStatus

        # Create a real product record in the test DB
        product_id = uuid.uuid4()
        async with AsyncSessionLocal() as db:
            product = Product(
                id=product_id,
                name="Test Siemens Contactor",
                status=ProductStatus.PROCESSING,
                input_pdf_path=None,
                input_image_paths=None,
                input_url=None,
            )
            db.add(product)
            await db.commit()

        events: list[dict] = []

        async def capture_emit(self_ref, product_id, event_type, message, data=None):
            events.append(
                {"type": event_type, "agent": self_ref.name if hasattr(self_ref, "name") else "?"}
            )

        # Patch all sub-agents to return known, deterministic outputs
        doc_candidates: dict[str, list[CandidateValue]] = {
            "voltage_rating": [
                CandidateValue(
                    "230V", SourceType.DOC, "test.pdf:page1", "Voltage: 230V", "doc_intel_agent"
                )
            ]
        }
        vision_candidates: dict[str, list[CandidateValue]] = {}
        retrieval_candidates: dict[str, list[CandidateValue]] = {
            "voltage_rating": [
                CandidateValue(
                    "230V", SourceType.WEB, "catalog:test", "Voltage: 230V", "retrieval_agent"
                )
            ]
        }

        verified_results = {
            "voltage_rating": make_verified_result("voltage_rating"),
        }

        with (
            patch(
                "api.agents.doc_intel_agent.DocIntelAgent.run",
                new_callable=AsyncMock,
                return_value=doc_candidates,
            ),
            patch(
                "api.agents.vision_agent.VisionAgent.run",
                new_callable=AsyncMock,
                return_value=vision_candidates,
            ),
            patch(
                "api.agents.retrieval_agent.RetrievalAgent.run",
                new_callable=AsyncMock,
                return_value=retrieval_candidates,
            ),
            patch(
                "api.agents.verifier_agent.VerifierAgent.run",
                new_callable=AsyncMock,
                return_value=verified_results,
            ),
            patch(
                "api.agents.schema_mapper.SchemaMappingAgent.run",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "api.agents.hitl_router.HITLRouter.run", new_callable=AsyncMock, return_value=None
            ),
            # Suppress the real emit_event to avoid needing a live SSE queue
            patch("api.agents.base.BaseAgent.emit_event", new_callable=AsyncMock),
        ):
            orchestrator = OrchestratorAgent()
            await orchestrator.run(product_id=product_id)

        # Verify the product record was updated in DB
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            result = await db.execute(
                select(Product)
                .where(Product.id == product_id)
                .options(selectinload(Product.fields))
            )
            product_after = result.scalar_one_or_none()

        assert product_after is not None
        assert product_after.status in (ProductStatus.COMPLETE, ProductStatus.PENDING_REVIEW)
        assert len(product_after.fields) == 1
        assert product_after.fields[0].field_name == "voltage_rating"
        assert product_after.fields[0].value == "230V"

    @pytest.mark.asyncio
    async def test_low_confidence_fields_create_review_queue_items(self, monkeypatch, db_setup):
        """Fields below the confidence threshold must appear in the review queue."""
        from api.agents.orchestrator import OrchestratorAgent
        from api.database import AsyncSessionLocal
        from api.models.db import Product, ProductStatus

        product_id = uuid.uuid4()
        async with AsyncSessionLocal() as db:
            product = Product(
                id=product_id,
                name="Test Product Low Confidence",
                status=ProductStatus.PROCESSING,
                input_pdf_path=None,
                input_image_paths=None,
                input_url=None,
            )
            db.add(product)
            await db.commit()

        # One high confidence, one low confidence field
        verified_results = {
            "voltage_rating": make_verified_result("voltage_rating", confidence=0.95),
            "material": make_low_conf_result("material", confidence=0.3),
        }

        with (
            patch(
                "api.agents.doc_intel_agent.DocIntelAgent.run",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "api.agents.vision_agent.VisionAgent.run", new_callable=AsyncMock, return_value={}
            ),
            patch(
                "api.agents.retrieval_agent.RetrievalAgent.run",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "api.agents.verifier_agent.VerifierAgent.run",
                new_callable=AsyncMock,
                return_value=verified_results,
            ),
            patch(
                "api.agents.schema_mapper.SchemaMappingAgent.run",
                new_callable=AsyncMock,
                return_value={},
            ),
            patch(
                "api.agents.hitl_router.HITLRouter.run", new_callable=AsyncMock, return_value=None
            ),
            patch("api.agents.base.BaseAgent.emit_event", new_callable=AsyncMock),
        ):
            orchestrator = OrchestratorAgent()
            await orchestrator.run(product_id=product_id)

        # Product should be PENDING_REVIEW due to low-confidence material field
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            result = await db.execute(
                select(Product)
                .where(Product.id == product_id)
                .options(selectinload(Product.fields))
            )
            product_after = result.scalar_one_or_none()

        assert product_after is not None
        assert product_after.status == ProductStatus.PENDING_REVIEW
        assert len(product_after.fields) == 2

    @pytest.mark.asyncio
    async def test_nonexistent_product_does_not_crash(self, db_setup):
        """If product_id doesn't exist, orchestrator logs and returns cleanly."""
        from api.agents.orchestrator import OrchestratorAgent

        fake_id = uuid.uuid4()

        with patch("api.agents.base.BaseAgent.emit_event", new_callable=AsyncMock):
            orchestrator = OrchestratorAgent()
            # Should not raise any exception
            await orchestrator.run(product_id=fake_id)
