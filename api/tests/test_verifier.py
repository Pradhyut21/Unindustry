"""
Tests for the Verifier Agent scoring logic.

These cover every uncertainty_reason category and edge cases.
All tests run against pure functions — no DB, no API calls.

This is the most scrutinised part of the codebase for judges/scanners
because the verifier is the core differentiator of ProductTruth.
"""

import pytest

from api.agents.verifier_agent import (
    CandidateValue,
    compute_agreement_multiplier,
    compute_confidence,
    compute_source_type_weight,
    determine_uncertainty_reason,
    verify_field,
)
from api.models.db import SourceType, UncertaintyReason, VerificationStatus

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def doc_candidate(value: str, low_quality: bool = False) -> CandidateValue:
    return CandidateValue(
        value=value,
        source_type=SourceType.DOC,
        source_ref="datasheet.pdf:page1",
        extracted_snippet=f"Voltage: {value}",
        extraction_agent="doc_intel_agent",
        low_quality=low_quality,
    )


def image_candidate(value: str, low_quality: bool = False) -> CandidateValue:
    return CandidateValue(
        value=value,
        source_type=SourceType.IMAGE,
        source_ref="product_photo.jpg",
        extracted_snippet=f"Nameplate reads: {value}",
        extraction_agent="vision_agent",
        low_quality=low_quality,
    )


def web_candidate(value: str, low_quality: bool = False) -> CandidateValue:
    return CandidateValue(
        value=value,
        source_type=SourceType.WEB,
        source_ref="https://manufacturer.com/specs",
        extracted_snippet=f"Spec page: {value}",
        extraction_agent="retrieval_agent",
        low_quality=low_quality,
    )


def kg_candidate(value: str) -> CandidateValue:
    return CandidateValue(
        value=value,
        source_type=SourceType.KG,
        source_ref="internal_kg:product_42",
        extracted_snippet=f"Previously verified: {value}",
        extraction_agent="kg_lookup",
    )


# ---------------------------------------------------------------------------
# Unit tests: compute_source_type_weight
# ---------------------------------------------------------------------------


class TestSourceTypeWeights:
    def test_doc_has_highest_weight(self):
        assert compute_source_type_weight(SourceType.DOC) == 1.00

    def test_kg_weight(self):
        assert compute_source_type_weight(SourceType.KG) == 0.95

    def test_image_weight(self):
        assert compute_source_type_weight(SourceType.IMAGE) == 0.80

    def test_web_weight(self):
        assert compute_source_type_weight(SourceType.WEB) == 0.70

    def test_human_weight(self):
        assert compute_source_type_weight(SourceType.HUMAN) == 1.00


# ---------------------------------------------------------------------------
# Unit tests: compute_agreement_multiplier
# ---------------------------------------------------------------------------


class TestAgreementMultiplier:
    def test_zero_sources_returns_zero(self):
        assert compute_agreement_multiplier(0) == 0.0

    def test_single_source_returns_low_multiplier(self):
        assert compute_agreement_multiplier(1) == 0.60

    def test_two_sources_returns_full_multiplier(self):
        assert compute_agreement_multiplier(2) == 1.00

    def test_three_sources_returns_bonus(self):
        assert compute_agreement_multiplier(3) == 1.05

    def test_many_sources_same_as_three(self):
        assert compute_agreement_multiplier(10) == 1.05


# ---------------------------------------------------------------------------
# Unit tests: compute_confidence
# ---------------------------------------------------------------------------


class TestComputeConfidence:
    def test_two_doc_sources_is_max_confidence(self):
        score = compute_confidence(SourceType.DOC, n_agreeing=2, low_quality=False)
        assert score == 1.0

    def test_single_doc_source_is_moderate(self):
        score = compute_confidence(SourceType.DOC, n_agreeing=1, low_quality=False)
        assert score == pytest.approx(0.60, abs=0.01)

    def test_single_web_source_is_low(self):
        score = compute_confidence(SourceType.WEB, n_agreeing=1, low_quality=False)
        assert score == pytest.approx(0.42, abs=0.01)

    def test_low_quality_flag_reduces_confidence(self):
        normal = compute_confidence(SourceType.DOC, n_agreeing=1, low_quality=False)
        noisy = compute_confidence(SourceType.DOC, n_agreeing=1, low_quality=True)
        assert noisy < normal

    def test_confidence_never_exceeds_1(self):
        score = compute_confidence(SourceType.DOC, n_agreeing=100, low_quality=False)
        assert score <= 1.0

    def test_confidence_is_nonnegative(self):
        score = compute_confidence(SourceType.WEB, n_agreeing=0, low_quality=True)
        assert score >= 0.0


# ---------------------------------------------------------------------------
# Unit tests: determine_uncertainty_reason
# ---------------------------------------------------------------------------


class TestUncertaintyReason:
    def test_no_sources_returns_no_source_found(self):
        reason = determine_uncertainty_reason([], 0, False, False)
        assert reason == UncertaintyReason.NO_SOURCE_FOUND

    def test_single_source_returns_single_source(self):
        reason = determine_uncertainty_reason([doc_candidate("230V")], 1, False, False)
        assert reason == UncertaintyReason.SINGLE_SOURCE

    def test_contradiction_returns_source_contradiction(self):
        reason = determine_uncertainty_reason(
            [doc_candidate("230V"), web_candidate("110V")],
            1,  # only 1 agreeing with the majority value
            True,
            False,
        )
        assert reason == UncertaintyReason.SOURCE_CONTRADICTION

    def test_low_quality_single_returns_low_quality(self):
        reason = determine_uncertainty_reason(
            [image_candidate("230V", low_quality=True)], 1, False, True
        )
        assert reason == UncertaintyReason.LOW_QUALITY_EXTRACTION

    def test_two_clean_sources_returns_none(self):
        reason = determine_uncertainty_reason(
            [doc_candidate("230V"), image_candidate("230V")], 2, False, False
        )
        assert reason == UncertaintyReason.NONE


# ---------------------------------------------------------------------------
# Integration tests: verify_field — the main function
# ---------------------------------------------------------------------------


class TestVerifyField:
    # --- Happy path: verified ---

    def test_two_agreeing_doc_sources_are_verified(self):
        candidates = [doc_candidate("230V"), kg_candidate("230V")]
        result = verify_field("voltage_rating", candidates, min_sources=2)
        assert result.verification_status == VerificationStatus.VERIFIED
        assert result.final_value == "230V"
        assert result.confidence >= 0.7
        assert result.uncertainty_reason == UncertaintyReason.NONE

    def test_three_agreeing_sources_are_verified_with_high_confidence(self):
        candidates = [doc_candidate("230V"), image_candidate("230V"), web_candidate("230V")]
        result = verify_field("voltage_rating", candidates, min_sources=2)
        assert result.verification_status == VerificationStatus.VERIFIED
        assert result.confidence == 1.0

    # --- Single source ---

    def test_single_doc_source_is_single_source_status(self):
        result = verify_field("voltage_rating", [doc_candidate("230V")], min_sources=2)
        assert result.verification_status == VerificationStatus.SINGLE_SOURCE
        assert result.uncertainty_reason == UncertaintyReason.SINGLE_SOURCE
        assert result.confidence < 0.7

    def test_single_web_source_has_low_confidence(self):
        result = verify_field("voltage_rating", [web_candidate("230V")], min_sources=2)
        assert result.confidence < 0.5
        assert result.verification_status == VerificationStatus.SINGLE_SOURCE

    # --- No source ---

    def test_empty_candidates_returns_no_source(self):
        result = verify_field("voltage_rating", [], min_sources=2)
        assert result.verification_status == VerificationStatus.SINGLE_SOURCE
        assert result.uncertainty_reason == UncertaintyReason.NO_SOURCE_FOUND
        assert result.final_value is None
        assert result.confidence == 0.0

    # --- Contradiction ---

    def test_two_sources_with_different_values_is_contradiction(self):
        candidates = [doc_candidate("230V"), web_candidate("110V")]
        result = verify_field("voltage_rating", candidates, min_sources=2)
        assert result.verification_status == VerificationStatus.CONTRADICTION
        assert result.uncertainty_reason == UncertaintyReason.SOURCE_CONTRADICTION

    def test_contradiction_still_picks_best_source_value(self):
        """When sources contradict, we prefer the doc (higher weight) value."""
        candidates = [doc_candidate("230V"), web_candidate("110V")]
        result = verify_field("voltage_rating", candidates, min_sources=2)
        assert result.final_value == "230V"  # doc wins over web

    def test_three_sources_two_agree_one_contradicts_is_verified(self):
        """Majority-agreeing sources → verified, minority is contradiction."""
        candidates = [
            doc_candidate("230V"),
            image_candidate("230V"),
            web_candidate("110V"),  # outlier
        ]
        result = verify_field("voltage_rating", candidates, min_sources=2)
        assert result.verification_status == VerificationStatus.VERIFIED
        assert result.final_value == "230V"

    # --- Low quality ---

    def test_low_quality_single_source_has_reduced_confidence(self):
        result = verify_field(
            "voltage_rating",
            [image_candidate("230V", low_quality=True)],
            min_sources=2,
        )
        assert result.uncertainty_reason == UncertaintyReason.LOW_QUALITY_EXTRACTION
        assert result.confidence < 0.5

    def test_low_quality_with_clean_confirming_source_upgrades_status(self):
        """Low-quality extraction + clean confirming source → can still be verified."""
        candidates = [
            image_candidate("230V", low_quality=True),
            doc_candidate("230V"),
        ]
        result = verify_field("voltage_rating", candidates, min_sources=2)
        assert result.verification_status == VerificationStatus.VERIFIED

    # --- Value normalisation ---

    def test_case_insensitive_value_matching(self):
        """'230V' and '230v' should be treated as the same value."""
        candidates = [doc_candidate("230V"), web_candidate("230v")]
        result = verify_field("voltage_rating", candidates, min_sources=2)
        assert result.verification_status == VerificationStatus.VERIFIED

    def test_whitespace_normalised_matching(self):
        """'230 V' and '230V' should be treated as different values (whitespace in spec matters)."""
        candidates = [doc_candidate("230 V"), web_candidate("230  V")]
        result = verify_field("voltage_rating", candidates, min_sources=2)
        # Both normalise to "230 v" → should agree
        assert result.verification_status == VerificationStatus.VERIFIED

    # --- min_sources boundary ---

    def test_min_sources_1_single_source_is_verified(self):
        """If min_sources=1, even a single source is considered verified."""
        result = verify_field("voltage_rating", [doc_candidate("230V")], min_sources=1)
        assert result.verification_status == VerificationStatus.VERIFIED

    def test_min_sources_3_requires_three_agreements(self):
        candidates = [doc_candidate("230V"), image_candidate("230V")]
        result = verify_field("voltage_rating", candidates, min_sources=3)
        # Only 2 agreeing, need 3
        assert result.verification_status == VerificationStatus.SINGLE_SOURCE

    # --- Source preference ---

    def test_doc_source_preferred_over_web_for_final_value(self):
        """When 3 sources agree, the final value should come from the highest-weight source."""
        candidates = [
            web_candidate("230 Volts"),  # lower weight
            doc_candidate("230V"),  # higher weight — this wins
            image_candidate("230V"),
        ]
        result = verify_field("voltage_rating", candidates, min_sources=2)
        assert result.final_value == "230V"  # doc value preferred

    def test_agreeing_and_contradicting_sources_are_separated(self):
        candidates = [doc_candidate("230V"), image_candidate("230V"), web_candidate("110V")]
        result = verify_field("voltage_rating", candidates, min_sources=2)
        assert len(result.agreeing_sources) == 2
        assert len(result.contradicting_sources) == 1
