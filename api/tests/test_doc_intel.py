"""
Tests for the Doc-Intel Agent.

Covers:
- Pure value-parsing function (_parse_value_from_line)
- Agent returns {} gracefully when no PDF is provided
- Agent returns {} gracefully when a nonexistent path is given
- SPEC_FIELD_PATTERNS structure is well-formed

Runs without DB, API calls, or real PDF files — all I/O paths are guarded.
"""

import pytest

from api.agents.doc_intel_agent import (
    SPEC_FIELD_PATTERNS,
    DocIntelAgent,
    _parse_value_from_line,
)

# ---------------------------------------------------------------------------
# Unit tests: _parse_value_from_line (pure function)
# ---------------------------------------------------------------------------


class TestParseValueFromLine:
    def test_colon_separated_returns_value(self):
        line = "Voltage: 230V AC"
        result = _parse_value_from_line(line, "voltage")
        assert result == "230V AC"

    def test_tab_separated_returns_value(self):
        line = "Current Rating\t16A"
        result = _parse_value_from_line(line, "current rating")
        assert result == "16A"

    def test_no_separator_returns_none(self):
        line = "This line has no colon or tab"
        result = _parse_value_from_line(line, "voltage")
        assert result is None

    def test_empty_value_after_colon_returns_none(self):
        line = "Voltage:"
        result = _parse_value_from_line(line, "voltage")
        assert result is None

    def test_value_too_long_returns_none(self):
        # Values > 200 chars should be rejected (noise)
        line = "Voltage: " + "x" * 201
        result = _parse_value_from_line(line, "voltage")
        assert result is None

    def test_colon_value_is_stripped(self):
        line = "IP Rating:   IP65   "
        result = _parse_value_from_line(line, "ip rating")
        assert result == "IP65"

    def test_tab_value_is_stripped(self):
        line = "Weight\t  1.2 kg  "
        result = _parse_value_from_line(line, "weight")
        assert result == "1.2 kg"

    def test_multiple_colons_uses_first_split(self):
        """Only split on first colon — value may contain additional colons."""
        line = "Source URL: https://example.com:8080/specs"
        result = _parse_value_from_line(line, "source url")
        assert result == "https://example.com:8080/specs"


# ---------------------------------------------------------------------------
# Structure tests: SPEC_FIELD_PATTERNS
# ---------------------------------------------------------------------------


class TestSpecFieldPatterns:
    def test_all_patterns_are_strings(self):
        for field_name, patterns in SPEC_FIELD_PATTERNS.items():
            for pattern in patterns:
                assert isinstance(
                    pattern, str
                ), f"Pattern in {field_name!r} is not a string: {pattern!r}"

    def test_all_patterns_are_lowercase(self):
        """Patterns must be lowercase for case-insensitive matching to work."""
        for field_name, patterns in SPEC_FIELD_PATTERNS.items():
            for pattern in patterns:
                assert (
                    pattern == pattern.lower()
                ), f"Pattern {pattern!r} in {field_name!r} is not lowercase"

    def test_key_fields_are_present(self):
        required = [
            "voltage_rating",
            "current_rating",
            "ip_rating",
            "certifications",
            "model_number",
            "manufacturer",
        ]
        for field in required:
            assert field in SPEC_FIELD_PATTERNS, f"Missing field pattern: {field!r}"

    def test_each_field_has_at_least_one_pattern(self):
        for field_name, patterns in SPEC_FIELD_PATTERNS.items():
            assert len(patterns) >= 1, f"Field {field_name!r} has no patterns"


# ---------------------------------------------------------------------------
# Integration tests: DocIntelAgent.run() — graceful skipping
# ---------------------------------------------------------------------------


class TestDocIntelAgentRun:
    @pytest.mark.asyncio
    async def test_no_pdf_returns_empty_dict(self, monkeypatch):
        """Agent must return {} gracefully when no PDF path is given."""
        import uuid

        events = []

        async def mock_emit(product_id, event_type, message, data=None):
            events.append({"type": event_type, "message": message})

        agent = DocIntelAgent()
        monkeypatch.setattr(agent, "emit_event", mock_emit)

        result = await agent.run(product_id=uuid.uuid4(), pdf_path=None)
        assert result == {}
        assert any("skipping" in e["message"].lower() for e in events)

    @pytest.mark.asyncio
    async def test_nonexistent_pdf_returns_empty_dict(self, monkeypatch):
        """Agent must return {} when the PDF file doesn't exist."""
        import uuid

        async def mock_emit(product_id, event_type, message, data=None):
            pass

        agent = DocIntelAgent()
        monkeypatch.setattr(agent, "emit_event", mock_emit)

        result = await agent.run(
            product_id=uuid.uuid4(),
            pdf_path="/nonexistent/path/to/missing.pdf",
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_string_pdf_returns_empty_dict(self, monkeypatch):
        """Agent must return {} when pdf_path is empty string."""
        import uuid

        async def mock_emit(product_id, event_type, message, data=None):
            pass

        agent = DocIntelAgent()
        monkeypatch.setattr(agent, "emit_event", mock_emit)

        result = await agent.run(product_id=uuid.uuid4(), pdf_path="")
        assert result == {}
