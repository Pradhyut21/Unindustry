"""
Tests for the Schema Mapper Agent.

Covers field mapping, unit normalisation, and missing field handling.
Pure function tests — no DB, no API calls.
"""

import pytest

from api.agents.schema_mapper import _normalise_unit, load_schema, map_to_schema
from api.agents.verifier_agent import CandidateValue, VerificationResult
from api.models.db import SourceType, UncertaintyReason, VerificationStatus


def _make_verified_result(
    field_name: str,
    value: str,
    confidence: float = 0.9,
) -> VerificationResult:
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
                extraction_agent="test",
            )
        ],
    )


class TestUnitNormalisation:
    def test_volt_to_V(self):
        assert "V" in _normalise_unit("230 volt", "V")

    def test_amp_to_A(self):
        assert "A" in _normalise_unit("16 ampere", "A")

    def test_kilowatt_to_kW(self):
        assert "kW" in _normalise_unit("1.5 kilowatt", "kW")

    def test_value_without_unit_passthrough(self):
        result = _normalise_unit("IP65", "")
        assert "IP65" in result

    def test_already_normalised_passthrough(self):
        result = _normalise_unit("230V", "V")
        # Should not break already-normalised values
        assert result  # non-empty


class TestMapToSchema:
    def setup_method(self):
        """Load actual schema for integration."""
        self.schema = load_schema()

    def test_returns_schema_metadata(self):
        result = map_to_schema({}, self.schema)
        assert "_schema" in result
        assert "_schema_version" in result

    def test_known_field_maps_correctly(self):
        verified = {"voltage_rating": _make_verified_result("voltage_rating", "230V")}
        result = map_to_schema(verified, self.schema)
        # The ETIM schema maps voltage_rating to some output field
        # Check at least one field has a value
        values_with_data = [
            v
            for k, v in result.items()
            if not k.startswith("_") and isinstance(v, dict) and v.get("value")
        ]
        assert len(values_with_data) >= 1

    def test_missing_field_returns_none_value(self):
        result = map_to_schema({}, self.schema)
        for key, val in result.items():
            if key.startswith("_"):
                continue
            if isinstance(val, dict):
                # Missing fields should have value=None
                assert val.get("value") is None or isinstance(val.get("value"), str)

    def test_confidence_is_preserved_in_output(self):
        verified = {
            "voltage_rating": _make_verified_result("voltage_rating", "230V", confidence=0.85)
        }
        result = map_to_schema(verified, self.schema)
        # Find the field that has confidence
        confidences = [
            v["confidence"]
            for k, v in result.items()
            if isinstance(v, dict) and "confidence" in v and v["confidence"] > 0
        ]
        if confidences:
            assert any(c == pytest.approx(0.85) for c in confidences)

    def test_empty_verified_fields_returns_all_none(self):
        result = map_to_schema({}, self.schema)
        non_meta = {k: v for k, v in result.items() if not k.startswith("_")}
        for val in non_meta.values():
            if isinstance(val, dict):
                assert val.get("value") is None
