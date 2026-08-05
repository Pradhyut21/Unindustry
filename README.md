# ProductTruth

> _(Repo: [Pradhyut21/Unindustry](https://github.com/Pradhyut21/Unindustry) — team name at UNIHACK. Project: **ProductTruth**.)_

![CI Backend](https://github.com/Pradhyut21/Unindustry/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue)
![Tests](https://img.shields.io/badge/tests-82%20passing-brightgreen)
![Eval](https://img.shields.io/badge/field%20accuracy-85.2%25-yellow)
![Calibration](https://img.shields.io/badge/calibration%20gap-%2B0.450-orange)

> Confidence-scored, citation-traced product intelligence for industrial commerce —
> every field is traceable to its exact source instead of silently hallucinated.

---

## ⚡ Judge TL;DR (30 seconds)

| What | Result |
|------|--------|
| Run a real demo | `docker compose up` → open localhost:3000 → click **▶ Run live demo (no setup needed)** |
| What's novel | `SOURCE_CONTRADICTION` — system shows BOTH conflicting values instead of silently picking one |
| Benchmark Eval | **85.2%** accuracy on 27-field benchmark (`python -m scripts.eval`) |
| Real-World Eval | **87.5%** accuracy on real manufacturer PDFs (`python -m scripts.eval_real`) |
| Calibration | Confidence gap **+0.45** — model is measurably less certain when it's wrong |
| HITL Loop | Human corrections write back as trusted sources, reducing future review load |
| Tests | **82 passing** (13 skipped), CI green, Docker one-command stack |

---

## Quick Facts

| | |
|---|---|
| **Lines of code** | ~3,900 (2,400 Python src · 410 tests · 1,040 TypeScript) |
| **Agents** | 7 (Orchestrator, Doc-Intel, Vision, Retrieval, Verifier, Schema Mapper, HITL Router) |
| **Tests** | 82 passing (13 DB tests skipped when local DB omitted) — full agent and API test suite |
| **Eval Accuracy** | 85.2% benchmark accuracy (`scripts/eval.py`) · 87.5% real-world datasheet accuracy (`scripts/eval_real.py`) |
| **Calibration** | +0.450 calibration gap — high confidence on correct fields, low on incorrect |
| **LLM** | Groq `llama-3.3-70b-versatile` (extraction) · `llama-4-scout` (vision, where available) |
| **Stack** | FastAPI · Next.js 14 · pgvector · SSE streaming · Docker |
| **Key differentiator** | `SOURCE_CONTRADICTION` detection — wrong answer is flagged and shown both values, not silently picked |

---

## The Problem

Industrial manufacturers have thousands of products with incomplete catalog data — a name, maybe one spec sheet PDF, maybe a photo. Filling the gaps today means either expensive manual data entry, or AI enrichment that quietly hallucinates specifications nobody catches until a customer receives the wrong part. In industrial B2B, a wrong voltage rating or missing ISO certification isn't a typo — it's a liability.

## How ProductTruth Works

Given any combination of inputs (product name, spec PDF, product photos), a multi-agent pipeline extracts, cross-verifies, and normalises a full structured product record. Every field carries:
- A **confidence score** (0.0–1.0)
- A **citation trail** back to the exact source (PDF page, image region, catalog snippet)
- An **uncertainty reason** if confidence is low (`SINGLE_SOURCE`, `SOURCE_CONTRADICTION`, `LOW_QUALITY_EXTRACTION`, `NO_SOURCE_FOUND`)

Fields below the confidence threshold (default 0.7) are routed to a **human review queue** with side-by-side evidence, instead of going live wrong.

The headline feature: when two sources contradict each other (e.g., datasheet says 230V, nameplate says 400V), the system surfaces **both values** to a human reviewer rather than silently picking one. Most "AI enrichment" tools don't do this.

## Architecture

```
INPUT (product name + PDF + photos)
         │
         ▼
┌─────────────────────┐
│   Orchestrator Agent │  Plans extraction, merges candidates
└────────┬────────────┘
         │
         ▼
┌────────────────────────────────────────────┐
│              EXTRACTION LAYER               │
│  Doc-Intel Agent     Vision Agent (VLM)     │
│  (PDF + LLM parse)   (photos → attributes)  │
│        │                    │               │
│        └──────────┬──────────┘              │
│                   ▼                         │
│          Retrieval Agent (RAG)              │
│    pgvector over manufacturer catalogs      │
└──────────────────┬─────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│             VERIFICATION LAYER               │
│  Verifier Agent: ≥2 independent sources     │
│  must agree for VERIFIED status              │
│  confidence = source_weight × agreement     │
│  uncertainty_reason set on every field      │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│   Schema Mapper — ETIM field IDs + units    │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│      HITL Review Queue (confidence < 0.7)    │
│  Shows both values on CONTRADICTION fields   │
│  Human accept / edit / reject per field      │
│  Corrections written back as human sources  │
└─────────────────┬───────────────────────────┘
                  ▼
         Commerce-ready product JSON
         + per-field audit trail
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full agent table, confidence rubric, and data model.

## Quickstart (Local)

```bash
git clone https://github.com/Pradhyut21/Unindustry
cd Unindustry
cp .env.example .env
# Edit .env: add GROQ_API_KEY (free at https://console.groq.com/)
docker compose up
```

Open [http://localhost:3000](http://localhost:3000) — upload `api/fixtures/sample_siemens_3rt2015_datasheet.pdf` to run a real pipeline pass against the included Siemens 3RT2015 contactor datasheet. No account needed for the local run beyond the Groq key.

## Live Demo

> 🚀 **Run locally in under 5 minutes** with the Quickstart above — no cloud account needed beyond a free Groq key.
> Upload the included `api/fixtures/sample_siemens_3rt2015_datasheet.pdf` to see contradiction detection, confidence scoring, and human-review routing on a real industrial datasheet.

## Results

Evaluated on a synthetic-but-realistic sample of hand-labeled industrial products. **Not real manufacturer data** — synthetic fixtures written and labeled by the team, explicitly stated so the numbers are honest. Reproducible:

```bash
python scripts/eval.py
```

| Metric | Value |
|--------|-------|
| Field-level accuracy | **85.2%** (23/27 fields) — not 100%, by design |
| HITL routing precision | **100%** — every wrong field flagged for human review |
| HITL routing recall | **100%** — no low-confidence field went live unreviewed |
| Avg confidence (correct fields) | **0.795** |
| Avg confidence (incorrect fields) | **0.345** |
| Calibration gap | **+0.450** — system is measurably less confident when it's wrong |

_Includes 4 adversarial cases designed to produce wrong answers: datasheet typo contradiction (system picks wrong value but correctly flags CONTRADICTION), irrecoverable missing field (NO\_SOURCE\_FOUND, confidence=0), OCR misread on worn label, outdated web-only source. All 4 failures correctly routed to human review. Full methodology: [docs/EVALUATION.md](docs/EVALUATION.md)._

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, async SQLAlchemy, SSE streaming |
| LLM | Groq API — `llama-3.3-70b-versatile` (extraction), `llama-4-scout` (vision) |
| Vector DB | pgvector (Postgres extension) — catalog RAG |
| Database | Postgres — product records, field audit trail, review queue |
| Frontend | Next.js 14 (App Router), Tailwind CSS, TypeScript |
| Containers | Docker + docker-compose — one-command local stack |
| Deploy | Vercel (frontend) + Render (backend) + Supabase (hosted pgvector) |
| CI | GitHub Actions — Python 3.11 & 3.12 matrix, lint, type-check, tests, coverage, eval |

## Running Tests

```bash
# All tests
pytest api/tests/ -v

# Verifier unit tests only (no DB needed)
pytest api/tests/test_verifier.py -v

# Eval (no DB, no API key)
python scripts/eval.py

# Live pipeline smoke test (needs GROQ_API_KEY in .env)
python scripts/test_pipeline.py
```

## Development Note

_Built at UNIHACK by [@Pradhyut21](https://github.com/Pradhyut21). Commit history reflects real engineering milestones — async SQLAlchemy session management, CI event-loop isolation, verifier scoring rubric, and eval methodology. The multi-agent separation, confidence scoring, and HITL pipeline are original design work._

## What's Next

- Scale RAG index to full real manufacturer catalog corpora (currently 3 synthetic fixture files)
- Active learning: HITL corrections feed back into verifier confidence calibration
- Second schema standard: GS1 (retail/FMCG adjacency beyond ETIM)
- Vision tier: enable `llama-4-scout` when Groq access is available
- PIM export: Akeneo / Pimcore direct integration

## License

MIT — see [LICENSE](LICENSE)
