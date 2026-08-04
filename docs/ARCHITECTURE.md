# ProductTruth — Architecture Reference

> Written for a technical judge or reviewer who wants to understand the system design decisions, not just the output.

---

## Problem Statement

Industrial manufacturers have thousands of products with incomplete catalog data. Filling the gaps with AI today means either expensive manual entry or enrichment pipelines that silently hallucinate specifications — which in industrial B2B contexts (wrong voltage, wrong ISO cert, wrong dimensions) creates real liability, not just data quality debt.

## Core Design Decision: Provenance as Architecture

Most enrichment pipelines treat citations as a nice-to-have output. ProductTruth makes them a constraint: **a field value cannot be marked "verified" unless ≥2 independent sources agree on it**. Fields that don't meet this bar are classified by *why* they're uncertain and routed to a human reviewer instead of going live.

This isn't a cosmetic difference. It changes the data model, the agent design, the output schema, and the UX — which is why it's the architectural decision, not a feature flag.

---

## Agent Roster

| Agent | File | Job | Failure mode it prevents |
|---|---|---|---|
| **Orchestrator** | `api/agents/orchestrator.py` | Inspects available inputs, builds extraction plan, dispatches agents, merges results, persists to DB | Wasted API calls on missing data types; partial results not persisted |
| **Doc-Intel Agent** | `api/agents/doc_intel_agent.py` | Parses PDFs/datasheets (PyMuPDF + Claude LLM-assisted), extracts tables and KV spec pairs, tags each value with `{source_file, page_number, snippet}` | Structured data buried in PDF tables silently lost |
| **Vision Agent** | `api/agents/vision_agent.py` | Uses Claude's vision capability to read nameplates, labels, and specs from product photos; classifies product category from image | Manual re-typing of nameplate data; missed specs on unlabeled parts |
| **Retrieval Agent** | `api/agents/retrieval_agent.py` | RAG over local catalog fixture index + Claude LLM inference for still-missing fields; tags outputs with `{source_ref, snippet}` | Blank fields when no PDF or image is available |
| **Verifier Agent** | `api/agents/verifier_agent.py` | Cross-checks every field against ≥2 independent sources; assigns confidence 0–1 using explicit rubric; classifies uncertainty reason | Hallucinated specs reaching the commerce system |
| **Schema Mapper** | `api/agents/schema_mapper.py` | Maps verified record to ETIM-inspired target schema (JSON-configurable); applies unit normalisation | Data that "looks right" but can't integrate with PIM systems |
| **HITL Router** | `api/agents/hitl_router.py` | Routes fields below confidence threshold to human review queue; emits SSE event with count | Reviewer fatigue from reviewing everything; low-confidence fields going live |

---

## Confidence Scoring Rubric

This is the rubric every field's confidence score comes from. It's implemented as pure functions in `api/agents/verifier_agent.py` and has 25+ unit tests in `api/tests/test_verifier.py`.

```
confidence = source_type_weight(best_source) × agreement_multiplier(n_agreeing)
             × low_quality_penalty (if applicable)

source_type_weight:
  doc   → 1.00   (manufacturer spec sheet is the gold standard)
  kg    → 0.95   (previously human-verified in our system)
  image → 0.80   (VLM extraction — can have OCR/label errors)
  web   → 0.70   (web/RAG retrieval — unverified provenance)
  human → 1.00   (HITL correction — trusted by definition)

agreement_multiplier:
  n=1  → 0.60   (single source — not verified, still useful)
  n=2  → 1.00   (two independent sources agree — verification threshold)
  n=3+ → 1.05   (capped at 1.0 in final score — bonus for strong consensus)

low_quality_penalty:
  If any source flagged as noisy (OCR blur, partial label): × 0.75
```

### Uncertainty Reason Taxonomy

Every low-confidence field is classified into *why* it's uncertain — visible in output, not just a raw number:

| Reason | When assigned | What it means for the reviewer |
|---|---|---|
| `NONE` | confidence ≥ threshold, ≥2 sources agree | Ready for commerce |
| `SINGLE_SOURCE` | Only 1 source found | Needs a second verification pass |
| `SOURCE_CONTRADICTION` | ≥2 sources found but disagree | Human must adjudicate the conflict |
| `LOW_QUALITY_EXTRACTION` | Extraction flagged as noisy (OCR, blur) | Verify against original source |
| `NO_SOURCE_FOUND` | No source found for this field | Re-extraction or manual entry needed |

---

## Data Flow

```
INPUT: product name + optional PDF + optional images + optional URL
         │
         ▼
┌─────────────────────┐
│   Orchestrator       │  Inspects inputs, dispatches agents
└────────┬────────────┘
         │ asyncio.gather (parallel)
         ├────────────────────────────┐
         ▼                            ▼
┌──────────────────┐       ┌────────────────────┐
│  Doc-Intel Agent  │       │  Vision Agent (VLM) │
│  PyMuPDF + Claude │       │  Claude vision API  │
└────────┬─────────┘       └──────────┬──────────┘
         └──────────────┬─────────────┘
                         ▼
              Merge: field_name → [CandidateValue, ...]
                         │
                         ▼
              ┌─────────────────────┐
              │   Retrieval Agent    │  Fills still-missing fields
              │   pgvector catalog   │
              └────────┬────────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │   Verifier Agent     │  Core logic: ≥2 sources,
              │   verify_field()     │  confidence scoring, uncertainty_reason
              └────────┬────────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │   Schema Mapper      │  ETIM field IDs, unit normalisation
              └────────┬────────────┘
                        │
              ┌─────────┴──────────────────┐
              │ confidence ≥ 0.7           │ confidence < 0.7
              ▼                            ▼
     product_fields (VERIFIED)    review_queue (PENDING)
                                           │
                                           ▼
                                  HITL Review Console
                                  accept / edit / reject
                                  → written back as KG source
```

---

## Database Schema

```sql
products(id UUID, name TEXT, category TEXT, status ENUM, created_at, updated_at)

product_fields(
  id UUID, product_id UUID,
  field_name TEXT, value TEXT,
  confidence FLOAT,
  verification_status ENUM,   -- verified | single_source | contradiction | ...
  uncertainty_reason ENUM,    -- none | single_source | source_contradiction | ...
  schema_field_id TEXT,       -- ETIM field ID (e.g. EF000001)
  created_at, updated_at
)

field_sources(
  id UUID, field_id UUID,
  source_type ENUM,           -- doc | image | web | kg | human
  source_ref TEXT,            -- "datasheet.pdf:page3" | "photo.jpg" | "https://..."
  extracted_snippet TEXT,     -- the exact text that justified the value
  extraction_agent TEXT,      -- which agent extracted this
  extracted_at TIMESTAMP
)

review_queue(
  id UUID, field_id UUID,
  status ENUM,                -- pending | accepted | edited | rejected
  reviewer TEXT,
  reviewed_at TIMESTAMP,
  human_corrected_value TEXT
)
```

---

## SSE Streaming

The pipeline streams live progress to the frontend via Server-Sent Events (SSE). The client subscribes to `GET /api/v1/stream/{product_id}` before triggering the pipeline run. Each agent emits structured events:

```json
{
  "event_type": "agent_start | agent_complete | agent_error | pipeline_complete",
  "agent_name": "doc_intel_agent",
  "message": "Parsing spec_sheet.pdf...",
  "field_count": 8
}
```

The frontend uses these to animate agent cards in sequence.

---

## HITL Feedback Loop

Human corrections are written back to `field_sources` with `source_type = HUMAN`. This means future pipeline runs for similar products will find the human-verified value in the knowledge graph and use it as a high-confidence source — gradually reducing the number of fields that need human review over time.

---

## What's Next (honest scope note)

This is a foundation built at hackathon pace:
- **Scale**: RAG index currently covers synthetic catalog fixtures; production would index real manufacturer catalog corpora (100k+ documents)
- **Active learning**: HITL corrections can feed into verifier calibration (adjust source_type_weight based on real correction rates)
- **More schema targets**: GS1 (retail/FMCG), Akeneo direct export, Pimcore native format
- **Provider abstraction**: VLM is Claude today; a provider interface would let you swap to GPT-4o-vision or Gemini — one-line change
- **pgvector production**: Currently uses keyword search over fixtures; production would use real embedding-based similarity search
