# ProductTruth — Evaluation Methodology

## How to Run

```bash
# From repo root (no DB or API key needed — pure function evaluation)
python scripts/eval.py
```

Runs in < 1 second. No external API calls. Output is printed to stdout.

---

## What It Measures

The eval script runs the ProductTruth verifier pipeline against a hand-labeled set of synthetic industrial products and reports three metrics:

### 1. Field-Level Accuracy
**Definition**: Fraction of fields where `predicted_value.lower().strip() == ground_truth.lower().strip()`

**What it tells you**: Does the verifier's logic for choosing the "best" value from multiple candidates produce the correct answer?

**Caveat**: In a real pipeline, "predicted value" would come from LLM extraction. In eval, we inject candidate values directly (bypassing the LLM extractors) to test the verifier logic in isolation. This is intentional — LLM extraction quality varies with model version, API latency, and prompt; verifier logic does not.

### 2. HITL Routing (Precision + Recall)
**Definition**:
- **Precision**: Of all fields routed to human review (confidence < threshold), what fraction actually needed review (single_source or contradiction)?
- **Recall**: Of all fields that needed review, what fraction were correctly routed?

**What it tells you**: Is the confidence threshold well-calibrated? Are we sending the right fields to a human reviewer?

### 3. Confidence Calibration
**Definition**: Average confidence score on correct vs. incorrect fields.

**What it tells you**: Is the model "aware" of when it's wrong? A well-calibrated system has higher confidence on correct fields than incorrect ones. The "calibration gap" (avg_conf_correct − avg_conf_incorrect) should be positive and as large as possible.

---

## Sample Set

**8 synthetic products, ~22 labeled fields.**

Products are designed to cover every uncertainty_reason category:

| # | Product | Primary scenario |
|---|---------|-----------------|
| 1 | Siemens 3RT2015 Contactor | All fields two-source verified |
| 2 | ABB S201 Circuit Breaker | Mix of single-source and verified |
| 3 | Generic 3-Phase Motor | Source contradiction (voltage 400V vs 230V) |
| 4 | Industrial Valve IP67 | Low-quality OCR extraction |
| 5 | Legacy Industrial Relay | No source for some fields |
| 6 | Schneider XB4BA21 Push Button | Three-source agreement |
| 7 | Previously Catalogued Motor Starter | KG-only source |
| 8 | Thermal Overload Relay | Clean doc + noisy image agree |

---

## Honest Caveats

> **This is a synthetic sample set.** The products, candidate values, and ground-truth labels were all written by the ProductTruth team. The numbers tell you the verifier logic works as designed — they do not tell you how well the LLM extractors perform on real-world datasheets.

> **Small sample.** 22 fields across 8 products is directionally useful for validating the scoring rubric, not statistically meaningful at production scale.

> **What would a real eval look like?** You'd need 100+ real manufacturer datasheets with ground-truth field values verified by a domain expert. The RAG + LLM extraction steps would also need to be in the loop (not bypassed). This is the next step after a production pilot.

---

## Extending the Sample Set

Add items to `SAMPLE_PRODUCTS` in `scripts/eval.py`. Each item needs:
- `ground_truth: dict[str, str]` — the correct values (hand-verified)
- `candidates: dict[str, list[CandidateValue]]` — simulated extraction outputs
- A description of what scenario it's testing

If you have real datasheets with known correct values, you can integrate the full extraction pipeline by calling `OrchestratorAgent().run()` instead of injecting candidates manually.
