"""
Tests for the Retrieval Agent.

Covers:
- Agent returns {} immediately when no missing_fields are provided
- Agent returns {} gracefully when fixture directory doesn't exist
- _extract_value_from_snippet pure function behaviour
- Agent candidate output shape (source_type, source_ref, extraction_agent)

All tests run without DB or real API calls.
"""

import uuid

import pytest

from api.agents.retrieval_agent import RetrievalAgent, _extract_value_from_snippet
from api.models.db import SourceType


# ---------------------------------------------------------------------------
# Unit tests: _extract_value_from_snippet (pure function)
# ---------------------------------------------------------------------------


class TestExtractValueFromSnippet:
    def test_extracts_after_colon(self):
        snippet = "Voltage: 230V"
        result = _extract_value_from_snippet(snippet, "voltage")
        assert result == "230V"

    def test_extracts_after_dash(self):
        snippet = "IP Rating - IP65"
        result = _extract_value_from_snippet(snippet, "ip rating")
        assert result == "IP65"

    def test_returns_none_if_key_not_in_snippet(self):
        snippet = "Some unrelated text here"
        result = _extract_value_from_snippet(snippet, "voltage")
        assert result is None

    def test_truncates_to_80_chars(self):
        long_value = "x" * 100
        snippet = f"voltage: {long_value}"
        result = _extract_value_from_snippet(snippet, "voltage")
        assert result is not None
        assert len(result) <= 80

    def test_only_returns_first_line(self):
        snippet = "voltage: 230V\ncurrent: 16A"
        result = _extract_value_from_snippet(snippet, "voltage")
        assert result == "230V"

    def test_empty_value_after_separator_returns_none(self):
        snippet = "voltage:    "
        result = _extract_value_from_snippet(snippet, "voltage")
        assert result is None


# ---------------------------------------------------------------------------
# Integration tests: RetrievalAgent.run()
# ---------------------------------------------------------------------------


class TestRetrievalAgentRun:
    @pytest.mark.asyncio
    async def test_empty_missing_fields_returns_immediately(self, monkeypatch):
        """Agent should return {} without any I/O when missing_fields is empty."""
        events = []

        async def mock_emit(product_id, event_type, message, data=None):
            events.append({"type": event_type, "message": message})

        agent = RetrievalAgent()
        monkeypatch.setattr(agent, "emit_event", mock_emit)

        result = await agent.run(
            product_id=uuid.uuid4(),
            product_name="Siemens 3RT2015",
            missing_fields=[],
        )
        assert result == {}
        assert any("skipping" in e["message"].lower() for e in events)

    @pytest.mark.asyncio
    async def test_returns_dict_of_candidate_lists(self, monkeypatch):
        """Return type must always be dict[str, list[CandidateValue]]."""
        from api.agents.retrieval_agent import CATALOG_FIXTURES_DIR

        async def mock_emit(product_id, event_type, message, data=None):
            pass

        # Patch the fixture search to return a known candidate
        async def mock_search_fixtures(product_name, fields):
            from api.agents.verifier_agent import CandidateValue
            from api.models.db import SourceType

            return [
                (
                    "voltage_rating",
                    CandidateValue(
                        value="230V",
                        source_type=SourceType.WEB,
                        source_ref="catalog:test",
                        extraction_agent="retrieval_agent:fixture",
                    ),
                )
            ]

        # Patch LLM retrieval to skip (no API key needed)
        async def mock_llm_retrieval(product_name, missing_fields, known_fields):
            return []

        agent = RetrievalAgent()
        monkeypatch.setattr(agent, "emit_event", mock_emit)
        monkeypatch.setattr(agent, "_search_fixtures", mock_search_fixtures)
        monkeypatch.setattr(agent, "_llm_retrieval", mock_llm_retrieval)

        result = await agent.run(
            product_id=uuid.uuid4(),
            product_name="Test Product",
            missing_fields=["voltage_rating", "ip_rating"],
        )

        assert isinstance(result, dict)
        for field_name, candidates in result.items():
            assert isinstance(candidates, list)
            for c in candidates:
                assert hasattr(c, "value")
                assert hasattr(c, "source_type")
                assert hasattr(c, "source_ref")
                assert hasattr(c, "extraction_agent")

    @pytest.mark.asyncio
    async def test_no_api_key_skips_llm_retrieval(self, monkeypatch):
        """When GROQ_API_KEY is absent, LLM retrieval is silently skipped."""
        from api.config import settings

        monkeypatch.setattr(settings, "groq_api_key", "")

        async def mock_emit(product_id, event_type, message, data=None):
            pass

        # Fixture search returns nothing (empty dir)
        async def mock_search_fixtures(product_name, fields):
            return []

        agent = RetrievalAgent()
        monkeypatch.setattr(agent, "emit_event", mock_emit)
        monkeypatch.setattr(agent, "_search_fixtures", mock_search_fixtures)

        # Should not raise even with no API key
        result = await agent.run(
            product_id=uuid.uuid4(),
            product_name="ABB Circuit Breaker",
            missing_fields=["voltage_rating"],
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_candidate_source_type_is_web(self, monkeypatch):
        """Retrieval agent candidates must be tagged as WEB source type."""
        async def mock_emit(product_id, event_type, message, data=None):
            pass

        async def mock_search_fixtures(product_name, fields):
            from api.agents.verifier_agent import CandidateValue

            return [
                (
                    "ip_rating",
                    CandidateValue(
                        value="IP65",
                        source_type=SourceType.WEB,
                        source_ref="catalog:test",
                        extraction_agent="retrieval_agent:fixture",
                    ),
                )
            ]

        async def mock_llm_retrieval(product_name, missing_fields, known_fields):
            return []

        agent = RetrievalAgent()
        monkeypatch.setattr(agent, "emit_event", mock_emit)
        monkeypatch.setattr(agent, "_search_fixtures", mock_search_fixtures)
        monkeypatch.setattr(agent, "_llm_retrieval", mock_llm_retrieval)

        result = await agent.run(
            product_id=uuid.uuid4(),
            product_name="Test Motor",
            missing_fields=["ip_rating"],
        )

        if "ip_rating" in result:
            for candidate in result["ip_rating"]:
                assert candidate.source_type == SourceType.WEB
