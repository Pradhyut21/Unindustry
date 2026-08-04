"""
Verifier Agent — the core differentiator of ProductTruth.

For every candidate field value, this agent:
1. Collects all extracted values for the same field from different source agents
2. Requires ≥2 independent sources to agree before marking a field "verified"
3. Computes a 0.0–1.0 confidence score using an explicit, documented rubric
4. Classifies the uncertainty reason when confidence is low
5. Flags contradictions explicitly (both values + both sources shown)

The confidence scoring rubric is implemented as pure functions so they can
be unit-tested in isolation (see api/tests/test_verifier.py).

SCORING RUBRIC
--------------
confidence = source_type_weight(best_source) × agreement_multiplier(n_agreeing)

source_type_weight:
  doc   → 1.00   (manufacturer spec sheet is gold standard)
  kg    → 0.95   (previously human-verified in our system)
  image → 0.80   (VLM extraction, can have OCR errors)
  web   → 0.70   (web/RAG retrieval, unverified provenance)
  human → 1.00   (HITL correction, trusted by definition)

agreement_multiplier:
  n=1  → 0.60   (single source, not verified)
  n=2  → 1.00   (two independent sources agree)
  n=3+ → 1.05   (capped at 1.0 in final score)

uncertainty_reason (enum, visible in output):
  NONE                    — fully verified (conf ≥ threshold)
  SINGLE_SOURCE           — only one source found, even if high quality
  SOURCE_CONTRADICTION    — ≥2 sources found but disagree on value
  LOW_QUALITY_EXTRACTION  — extraction confidence flagged as noisy (OCR, blur)
  NO_SOURCE_FOUND         — no source found for this field at all
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from api.agents.base import BaseAgent
from api.models.db import SourceType, UncertaintyReason, VerificationStatus

# ---------------------------------------------------------------------------
# Source type reliability weights (used in scoring rubric)
# ---------------------------------------------------------------------------

SOURCE_TYPE_WEIGHTS: dict[SourceType, float] = {
    SourceType.DOC: 1.00,
    SourceType.KG: 0.95,
    SourceType.IMAGE: 0.80,
    SourceType.WEB: 0.70,
    SourceType.HUMAN: 1.00,
}

# ---------------------------------------------------------------------------
# Pure data types (no DB dependency — pure, testable)
# ---------------------------------------------------------------------------


@dataclass
class CandidateValue:
    """A single extracted value from one source."""

    value: str
    source_type: SourceType
    source_ref: str
    extracted_snippet: Optional[str] = None
    extraction_agent: str = "unknown"
    low_quality: bool = False  # flagged by the extracting agent (OCR noise, blur, etc.)


@dataclass
class VerificationResult:
    """
    Output of the verifier for one field.
    This is what gets written to product_fields + field_sources.
    """

    field_name: str
    final_value: Optional[str]
    confidence: float
    verification_status: VerificationStatus
    uncertainty_reason: UncertaintyReason
    agreeing_sources: list[CandidateValue] = field(default_factory=list)
    contradicting_sources: list[CandidateValue] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pure scoring functions (tested independently)
# ---------------------------------------------------------------------------


def compute_source_type_weight(source_type: SourceType) -> float:
    """Return the reliability weight for a given source type."""
    return SOURCE_TYPE_WEIGHTS.get(source_type, 0.5)


def compute_agreement_multiplier(n_agreeing: int) -> float:
    """
    How much to boost confidence based on number of agreeing sources.
    Two independent sources agreeing is the verification threshold.
    """
    if n_agreeing <= 0:
        return 0.0
    if n_agreeing == 1:
        return 0.60
    if n_agreeing == 2:
        return 1.00
    return 1.05  # 3+ sources; will be capped at 1.0


def compute_confidence(
    best_source_type: SourceType,
    n_agreeing: int,
    low_quality: bool = False,
) -> float:
    """
    Compute field confidence score.

    Parameters
    ----------
    best_source_type : SourceType
        The highest-reliability source type among agreeing sources.
    n_agreeing : int
        Number of independent sources that agree on this value.
    low_quality : bool
        Whether any extraction was flagged as low quality (OCR noise, etc.).

    Returns
    -------
    float
        Confidence score in [0.0, 1.0].
    """
    weight = compute_source_type_weight(best_source_type)
    multiplier = compute_agreement_multiplier(n_agreeing)
    raw = weight * multiplier
    if low_quality:
        raw *= 0.75  # penalty for noisy extraction
    return round(min(raw, 1.0), 4)


def determine_uncertainty_reason(
    candidates: list[CandidateValue],
    n_agreeing: int,
    has_contradiction: bool,
    low_quality: bool,
) -> UncertaintyReason:
    """
    Classify WHY a field has low confidence.
    The classification must be visible in output, not just a raw number.
    """
    if not candidates:
        return UncertaintyReason.NO_SOURCE_FOUND
    if low_quality and n_agreeing < 2:
        return UncertaintyReason.LOW_QUALITY_EXTRACTION
    if has_contradiction:
        return UncertaintyReason.SOURCE_CONTRADICTION
    if n_agreeing == 1:
        return UncertaintyReason.SINGLE_SOURCE
    return UncertaintyReason.NONE


def _normalise_value(value: str) -> str:
    """Normalise for comparison: lowercase, strip, collapse whitespace."""
    return " ".join(value.lower().strip().split())


def verify_field(
    field_name: str,
    candidates: list[CandidateValue],
    min_sources: int = 2,
) -> VerificationResult:
    """
    Core verification logic for a single field.
    Pure function — no I/O, no DB, fully unit-testable.

    Parameters
    ----------
    field_name : str
        Name of the field being verified (e.g. "voltage_rating").
    candidates : list[CandidateValue]
        All extracted candidates for this field from different agents.
    min_sources : int
        Minimum independent sources required to mark as VERIFIED (default 2).

    Returns
    -------
    VerificationResult
    """
    if not candidates:
        return VerificationResult(
            field_name=field_name,
            final_value=None,
            confidence=0.0,
            verification_status=VerificationStatus.SINGLE_SOURCE,
            uncertainty_reason=UncertaintyReason.NO_SOURCE_FOUND,
        )

    # Group candidates by normalised value
    value_groups: dict[str, list[CandidateValue]] = {}
    for c in candidates:
        key = _normalise_value(c.value)
        value_groups.setdefault(key, []).append(c)

    has_contradiction = len(value_groups) > 1

    # Pick the value with the most sources; break ties by best source weight
    def group_score(group: list[CandidateValue]) -> tuple[int, float]:
        best_weight = max(compute_source_type_weight(c.source_type) for c in group)
        return (len(group), best_weight)

    best_group_key = max(value_groups, key=lambda k: group_score(value_groups[k]))
    agreeing = value_groups[best_group_key]
    contradicting = [
        c for k, v in value_groups.items() if k != best_group_key for c in v
    ]

    n_agreeing = len(agreeing)
    any_low_quality = any(c.low_quality for c in agreeing)
    best_source_type = max(
        agreeing, key=lambda c: compute_source_type_weight(c.source_type)
    ).source_type

    confidence = compute_confidence(best_source_type, n_agreeing, any_low_quality)
    uncertainty_reason = determine_uncertainty_reason(
        candidates, n_agreeing, has_contradiction, any_low_quality
    )

    if n_agreeing >= min_sources:
        # Majority agrees — verified even if a minority contradicts
        verification_status = VerificationStatus.VERIFIED
    elif has_contradiction:
        verification_status = VerificationStatus.CONTRADICTION
    else:
        verification_status = VerificationStatus.SINGLE_SOURCE

    # Use the original (un-normalised) value from the best source in the group
    best_candidate = max(
        agreeing, key=lambda c: compute_source_type_weight(c.source_type)
    )

    return VerificationResult(
        field_name=field_name,
        final_value=best_candidate.value,
        confidence=confidence,
        verification_status=verification_status,
        uncertainty_reason=uncertainty_reason,
        agreeing_sources=agreeing,
        contradicting_sources=contradicting,
    )


# ---------------------------------------------------------------------------
# Agent wrapper (DB integration)
# ---------------------------------------------------------------------------


class VerifierAgent(BaseAgent):
    """
    Runs verify_field() for every field collected by the extraction agents,
    then writes results to product_fields + field_sources.
    """

    name = "verifier_agent"

    async def run(
        self,
        product_id: uuid.UUID,
        field_candidates: dict[str, list[CandidateValue]],
        min_sources: int = 2,
        **kwargs,
    ) -> dict[str, VerificationResult]:
        """
        Parameters
        ----------
        product_id : uuid.UUID
        field_candidates : dict mapping field_name → list of CandidateValue
        min_sources : int

        Returns
        -------
        dict mapping field_name → VerificationResult
        """
        await self.emit_event(
            product_id, "agent_start", f"Verifying {len(field_candidates)} fields..."
        )

        results: dict[str, VerificationResult] = {}
        for field_name, candidates in field_candidates.items():
            result = verify_field(field_name, candidates, min_sources)
            results[field_name] = result

        verified = sum(1 for r in results.values() if r.verification_status == VerificationStatus.VERIFIED)
        await self.emit_event(
            product_id,
            "agent_complete",
            f"Verified {verified}/{len(results)} fields at ≥{min_sources} sources.",
            data={"verified_count": verified, "total_count": len(results)},
        )

        return results
