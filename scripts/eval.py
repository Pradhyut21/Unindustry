"""
eval.py — ProductTruth evaluation script

Runs the verifier pipeline against a hand-labeled synthetic sample set
and prints real field-accuracy, HITL routing, and confidence calibration metrics.

IMPORTANT: The sample set is synthetic — products and ground-truth values
were written by the ProductTruth team. This is stated explicitly in the
README and docs/EVALUATION.md. These numbers are directionally useful
but are not a production benchmark against real manufacturer data.

Usage:
    python scripts/eval.py

Requires:
    - pip install -r api/requirements.txt
    - No external API calls needed (runs pure verifier logic)
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Ensure the repo root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.agents.verifier_agent import (
    CandidateValue,
    VerificationResult,
    verify_field,
)
from api.config import settings
from api.models.db import SourceType, VerificationStatus


# ---------------------------------------------------------------------------
# Labeled sample set
# Each item has a product name, simulated candidates, and known ground truth.
# ---------------------------------------------------------------------------


@dataclass
class SampleProduct:
    name: str
    ground_truth: dict[str, str]  # field_name → correct value
    candidates: dict[str, list[CandidateValue]]  # field_name → candidates
    description: str = ""


def _c(value: str, src: SourceType, low_quality: bool = False) -> CandidateValue:
    return CandidateValue(
        value=value,
        source_type=src,
        source_ref=f"eval_fixture:{src.value}",
        extracted_snippet=f"eval: {value}",
        extraction_agent="eval_fixture",
        low_quality=low_quality,
    )


SAMPLE_PRODUCTS: list[SampleProduct] = [
    # 1. Full verification — two sources agree, high confidence expected
    SampleProduct(
        name="Siemens 3RT2015 Contactor",
        description="Two-source verified; all fields should be VERIFIED",
        ground_truth={
            "voltage_rating": "230V AC",
            "current_rating": "7A",
            "ip_rating": "IP20",
            "certifications": "CE, UL, CSA, RoHS, IEC 60947-4-1",
            "weight": "0.24 kg",
        },
        candidates={
            "voltage_rating": [
                _c("230V AC", SourceType.DOC),
                _c("230V AC", SourceType.IMAGE),
            ],
            "current_rating": [
                _c("7A", SourceType.DOC),
                _c("7A", SourceType.KG),
            ],
            "ip_rating": [
                _c("IP20", SourceType.DOC),
                _c("IP20", SourceType.WEB),
            ],
            "certifications": [
                _c("CE, UL, CSA, RoHS, IEC 60947-4-1", SourceType.DOC),
                _c("CE, UL, CSA, RoHS, IEC 60947-4-1", SourceType.KG),
            ],
            "weight": [
                _c("0.24 kg", SourceType.DOC),
                _c("0.24 kg", SourceType.IMAGE),
            ],
        },
    ),
    # 2. Single-source fields — should route to HITL
    SampleProduct(
        name="ABB S201 Circuit Breaker",
        description="Single-source fields; expect SINGLE_SOURCE + HITL routing",
        ground_truth={
            "voltage_rating": "230/400V AC",
            "current_rating": "16A",
            "ip_rating": "IP20",
        },
        candidates={
            "voltage_rating": [_c("230/400V AC", SourceType.DOC)],  # single source
            "current_rating": [_c("16A", SourceType.DOC)],           # single source
            "ip_rating": [_c("IP20", SourceType.DOC), _c("IP20", SourceType.WEB)],
        },
    ),
    # 3. Contradiction — two sources disagree
    SampleProduct(
        name="Generic 3-Phase Motor",
        description="Contradicting sources on voltage; should flag CONTRADICTION",
        ground_truth={
            "voltage_rating": "400V",  # correct value (3-phase standard)
        },
        candidates={
            "voltage_rating": [
                _c("400V", SourceType.DOC),   # correct
                _c("230V", SourceType.WEB),   # wrong (1-phase confusion)
            ],
        },
    ),
    # 4. Low-quality extraction (OCR noise)
    SampleProduct(
        name="Industrial Valve IP67",
        description="Low-quality OCR extraction; expect LOW_QUALITY_EXTRACTION",
        ground_truth={
            "ip_rating": "IP67",
            "voltage_rating": "24V DC",
        },
        candidates={
            "ip_rating": [_c("IP67", SourceType.IMAGE, low_quality=True)],
            "voltage_rating": [
                _c("24V DC", SourceType.IMAGE, low_quality=True),
                _c("24V DC", SourceType.DOC),
            ],
        },
    ),
    # 5. No source found for some fields
    SampleProduct(
        name="Legacy Industrial Relay",
        description="Some fields have no source — expect NO_SOURCE_FOUND",
        ground_truth={
            "voltage_rating": "110V AC",
            "certifications": None,  # unknown in ground truth too
        },
        candidates={
            "voltage_rating": [_c("110V AC", SourceType.DOC), _c("110V AC", SourceType.KG)],
            "certifications": [],  # no source found
        },
    ),
    # 6. Three-way agreement — highest confidence
    SampleProduct(
        name="Schneider XB4BA21 Push Button",
        description="Three sources agree; expect maximum confidence",
        ground_truth={
            "ip_rating": "IP66",
            "voltage_rating": "250V AC",
        },
        candidates={
            "ip_rating": [
                _c("IP66", SourceType.DOC),
                _c("IP66", SourceType.IMAGE),
                _c("IP66", SourceType.WEB),
            ],
            "voltage_rating": [
                _c("250V AC", SourceType.DOC),
                _c("250V AC", SourceType.KG),
                _c("250V AC", SourceType.IMAGE),
            ],
        },
    ),
    # 7. KG source only — high single-source confidence
    SampleProduct(
        name="Previously Catalogued Motor Starter",
        description="KG-only source; expect SINGLE_SOURCE but higher confidence than WEB",
        ground_truth={
            "voltage_rating": "400V AC",
        },
        candidates={
            "voltage_rating": [_c("400V AC", SourceType.KG)],
        },
    ),
    # 8. Mixed quality — one clean doc, one noisy image agree
    SampleProduct(
        name="Thermal Overload Relay",
        description="Clean doc + noisy image agree; should be VERIFIED with slight penalty",
        ground_truth={
            "current_rating": "12A",
            "operating_temperature": "-20°C to +60°C",
        },
        candidates={
            "current_rating": [
                _c("12A", SourceType.DOC),
                _c("12A", SourceType.IMAGE, low_quality=True),
            ],
            "operating_temperature": [
                _c("-20°C to +60°C", SourceType.DOC),
                _c("-20°C to +60°C", SourceType.IMAGE, low_quality=True),
            ],
        },
    ),
    # ── ADVERSARIAL CASES ────────────────────────────────────────────────────
    # These are deliberately hard — the system is expected to get some wrong
    # or correctly refuse to commit. They validate that the calibration gap
    # is real: when confidence is low, the field IS wrong.

    # 9. Source contradiction — system picks wrong value (doc wins over image
    #    by weight, but the image was correct and doc was a typo in the sheet)
    #    Ground truth: 400V (3-phase motor). Doc says 230V (datasheet error).
    #    Image says 400V (correct nameplate). Verifier picks doc (higher weight)
    #    → WRONG prediction, but correctly flags SOURCE_CONTRADICTION.
    SampleProduct(
        name="Atlas Copco GA11 Compressor Motor",
        description="ADVERSARIAL: doc has a typo (230V), nameplate shows correct 400V. "
                    "Verifier picks doc by source weight — wrong answer, but flags contradiction.",
        ground_truth={
            "voltage_rating": "400V",   # correct value
            "power_rating": "11 kW",    # both sources agree — correct
        },
        candidates={
            "voltage_rating": [
                _c("230V", SourceType.DOC),    # datasheet typo — higher weight, wins
                _c("400V", SourceType.IMAGE),  # correct nameplate — lower weight, loses
            ],
            "power_rating": [
                _c("11 kW", SourceType.DOC),
                _c("11 kW", SourceType.IMAGE),
            ],
        },
    ),
    # 10. Completely irrecoverable field — no source found for a required field.
    #     Ground truth: "Epoxy-coated aluminium" (material).
    #     No source at all → final_value=None → definitely wrong.
    #     Also has a recoverable field to show the system works partially.
    SampleProduct(
        name="Parker Hannifin Solenoid Valve",
        description="ADVERSARIAL: material field has zero sources (irrecoverable). "
                    "Voltage field is correct. Tests NO_SOURCE_FOUND path.",
        ground_truth={
            "voltage_rating": "24V DC",
            "material": "Epoxy-coated aluminium",  # no source → will be None → wrong
            "ip_rating": "IP65",
        },
        candidates={
            "voltage_rating": [
                _c("24V DC", SourceType.DOC),
                _c("24V DC", SourceType.KG),
            ],
            "material": [],  # no source — system correctly returns None, but it's wrong
            "ip_rating": [_c("IP65", SourceType.DOC)],  # single source → HITL
        },
    ),
    # 11. OCR misread — low-quality vision extraction gets the value wrong,
    #     and there's no other source to catch it. System is "confident" for
    #     a single-source low-quality extraction but the value is wrong.
    #     Specifically: "30A" misread as "3A" (missing zero on a blurry label).
    SampleProduct(
        name="Eaton PKZM0 Motor Protector (worn label)",
        description="ADVERSARIAL: blurry nameplate. Vision reads '3A' but truth is '30A'. "
                    "Single low-quality image source — should route to HITL, still wrong.",
        ground_truth={
            "current_rating": "30A",   # correct
            "model_number": "PKZM0-32",  # different field, image got this right
        },
        candidates={
            "current_rating": [
                _c("3A", SourceType.IMAGE, low_quality=True),  # misread — wrong
            ],
            "model_number": [
                _c("PKZM0-32", SourceType.IMAGE, low_quality=True),
                _c("PKZM0-32", SourceType.DOC),  # confirmed by doc
            ],
        },
    ),
    # 12. Web-only retrieval for a discontinued product — single WEB source
    #     gets the certifications wrong (outdated catalog copy).
    SampleProduct(
        name="Schneider TeSys D LC1D Contactor (discontinued)",
        description="ADVERSARIAL: web-only source for a discontinued product. "
                    "Returns outdated certifications — single low-reliability source.",
        ground_truth={
            "certifications": "CE, IEC 60947-4-1, EN 60947-4-1, RoHS",
            "voltage_rating": "220V AC",  # web got this right
        },
        candidates={
            "certifications": [
                # Outdated web copy missing RoHS and citing wrong IEC year
                _c("CE, IEC 947-4-1", SourceType.WEB),
            ],
            "voltage_rating": [
                _c("220V AC", SourceType.WEB),
                _c("220V AC", SourceType.KG),
            ],
        },
    ),
]



# ---------------------------------------------------------------------------
# Evaluation logic
# ---------------------------------------------------------------------------


@dataclass
class FieldResult:
    product_name: str
    field_name: str
    ground_truth: Optional[str]
    predicted_value: Optional[str]
    confidence: float
    verification_status: str
    uncertainty_reason: str
    correct: bool
    routed_to_hitl: bool
    hitl_needed: bool  # True if single_source or contradiction or low confidence


@dataclass
class EvalSummary:
    total_fields: int = 0
    correct_predictions: int = 0
    fields_routed_to_hitl: int = 0
    fields_needing_hitl: int = 0
    correct_hitl_routing: int = 0
    confidences_when_correct: list[float] = field(default_factory=list)
    confidences_when_incorrect: list[float] = field(default_factory=list)


def evaluate_sample(
    sample: SampleProduct, confidence_threshold: float = 0.7
) -> list[FieldResult]:
    results: list[FieldResult] = []
    for field_name, gt_value in sample.ground_truth.items():
        candidates = sample.candidates.get(field_name, [])
        vr: VerificationResult = verify_field(field_name, candidates, min_sources=2)

        is_correct = (
            vr.final_value is not None
            and gt_value is not None
            and vr.final_value.lower().strip() == gt_value.lower().strip()
        ) or (vr.final_value is None and gt_value is None)

        routed_to_hitl = vr.confidence < confidence_threshold
        hitl_needed = vr.verification_status.value in (
            "single_source", "contradiction"
        ) or vr.confidence < confidence_threshold

        results.append(
            FieldResult(
                product_name=sample.name,
                field_name=field_name,
                ground_truth=gt_value,
                predicted_value=vr.final_value,
                confidence=vr.confidence,
                verification_status=vr.verification_status.value,
                uncertainty_reason=vr.uncertainty_reason.value,
                correct=is_correct,
                routed_to_hitl=routed_to_hitl,
                hitl_needed=hitl_needed,
            )
        )
    return results


def run_evaluation(threshold: float = 0.7) -> EvalSummary:
    summary = EvalSummary()
    all_results: list[FieldResult] = []

    for sample in SAMPLE_PRODUCTS:
        results = evaluate_sample(sample, confidence_threshold=threshold)
        all_results.extend(results)

    for r in all_results:
        summary.total_fields += 1
        if r.correct:
            summary.correct_predictions += 1
            summary.confidences_when_correct.append(r.confidence)
        else:
            summary.confidences_when_incorrect.append(r.confidence)

        if r.routed_to_hitl:
            summary.fields_routed_to_hitl += 1
        if r.hitl_needed:
            summary.fields_needing_hitl += 1
        if r.routed_to_hitl and r.hitl_needed:
            summary.correct_hitl_routing += 1

    return summary, all_results


def print_report(summary: EvalSummary, all_results: list[FieldResult]) -> None:
    print("\n" + "=" * 70)
    print("  ProductTruth — Evaluation Report")
    print("=" * 70)
    print(f"\n  Sample: {len(SAMPLE_PRODUCTS)} synthetic products, {summary.total_fields} labeled fields")
    print(f"  NOTE: Synthetic data — not real manufacturer catalog data\n")

    accuracy = summary.correct_predictions / summary.total_fields * 100
    print(f"  Field-level accuracy:              {accuracy:.1f}%  ({summary.correct_predictions}/{summary.total_fields})")

    hitl_precision = (
        summary.correct_hitl_routing / summary.fields_routed_to_hitl * 100
        if summary.fields_routed_to_hitl > 0 else 0
    )
    hitl_recall = (
        summary.correct_hitl_routing / summary.fields_needing_hitl * 100
        if summary.fields_needing_hitl > 0 else 0
    )
    print(f"  Fields correctly routed to HITL:   {hitl_precision:.1f}% precision, {hitl_recall:.1f}% recall")
    print(f"  Fields routed to HITL:             {summary.fields_routed_to_hitl}/{summary.total_fields}")
    print(f"  Fields needing HITL:               {summary.fields_needing_hitl}/{summary.total_fields}")

    avg_conf_correct = (
        sum(summary.confidences_when_correct) / len(summary.confidences_when_correct)
        if summary.confidences_when_correct else 0.0
    )
    avg_conf_incorrect = (
        sum(summary.confidences_when_incorrect) / len(summary.confidences_when_incorrect)
        if summary.confidences_when_incorrect else 0.0
    )
    print(f"\n  Confidence calibration:")
    print(f"    Avg confidence (correct fields):   {avg_conf_correct:.3f}")
    print(f"    Avg confidence (incorrect fields): {avg_conf_incorrect:.3f}")
    calibration_gap = avg_conf_correct - avg_conf_incorrect
    print(f"    Calibration gap (higher = better): {calibration_gap:+.3f}")

    print("\n  Per-field breakdown:")
    print(f"  {'Product':<35} {'Field':<25} {'Status':<15} {'Conf':>5} {'OK?':>4}")
    print("  " + "-" * 88)
    for r in all_results:
        tick = "[+]" if r.correct else "[-]"
        name_short = r.product_name[:33]
        print(
            f"  {name_short:<35} {r.field_name:<25} {r.verification_status:<15} "
            f"{r.confidence:>5.3f} {tick:>4}"
        )

    print("\n" + "=" * 70)
    print("  Reproduce: python scripts/eval.py")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    start = time.perf_counter()
    summary, all_results = run_evaluation(threshold=settings.confidence_threshold)
    elapsed = time.perf_counter() - start
    print_report(summary, all_results)
    print(f"  Eval completed in {elapsed:.2f}s")
