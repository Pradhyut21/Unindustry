# ProductTruth

**[github.com/Pradhyut21/Unindustry](https://github.com/Pradhyut21/Unindustry)**

![CI](https://github.com/Pradhyut21/Unindustry/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Tests](https://img.shields.io/badge/tests-37%20passing-brightgreen)
![Eval](https://img.shields.io/badge/field%20accuracy-85.2%25-yellow)

> Turns limited product inputs into commerce-ready records where every field
> is confidence-scored and traceable to its source — instead of silently hallucinated.

<!-- INSERT 15–30 sec demo GIF here after recording -->

## The Problem

Industrial manufacturers have thousands of products with incomplete catalog data — a name, maybe one spec sheet PDF, maybe a photo. Filling the gaps today means either expensive manual data entry, or AI enrichment that quietly hallucinates specifications nobody catches until a customer receives the wrong part. In industrial B2B, a wrong voltage rating or missing ISO certification isn't a typo — it's a liability.

## How ProductTruth Works

Given any combination of inputs (product name, spec PDF, product photos), a multi-agent pipeline extracts, cross-verifies, and normalises a full structured product record. Every field carries:
- A **confidence score** (0.0–1.0)
- A **citation trail** back to the exact source (PDF page, image region, catalog snippet)
- An **uncertainty reason** if confidence is low (`SINGLE_SOURCE`, `SOURCE_CONTRADICTION`, `LOW_QUALITY_EXTRACTION`, `NO_SOURCE_FOUND`)

Fields below the confidence threshold (default 0.7) are routed to a **human review queue** with side-by-side evidence, instead of going live wrong.

## Architecture

```
INPUT (product name + PDF + photos)
         │
         ▼
┌─────────────────────┐
│   Orchestrator Agent │  Plans extraction based on available inputs
└────────┬────────────┘
         │
         ▼
┌────────────────────────────────────────────┐
│              EXTRACTION LAYER               │
│  Doc-Intel Agent   Vision Agent (VLM)       │
│  (PDF/datasheet)   (photos → attributes)    │
│        │                  │                 │
│        └────────┬──────────┘                │
│                 ▼                           │
│         Retrieval Agent (RAG)               │
│   pgvector over manufacturer catalogs       │
└─────────────────┬──────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│            VERIFICATION LAYER                │
│  Verifier Agent: ≥2 sources must agree       │
│  confidence score + uncertainty_reason       │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│   Schema Mapper (ETIM-inspired taxonomy)     │
└─────────────────┬───────────────────────────┘
                  ▼
┌─────────────────────────────────────────────┐
│      HITL Review Queue (confidence < 0.7)    │
│  Human accepts / edits / rejects per field   │
└─────────────────┬───────────────────────────┘
                  ▼
         Commerce-ready product JSON
         + full audit trail per field
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full agent breakdown.

## Quickstart (Local)

```bash
git clone https://github.com/Pradhyut21/Unindustry
cd Unindustry
cp .env.example .env          # add your GROQ_API_KEY (free at console.groq.com)
docker compose up
```

Open [http://localhost:3000](http://localhost:3000) — upload `api/fixtures/sample_siemens_3rt2015_datasheet.pdf` to run a live pipeline pass.

## Live Demo

> Deploy in progress — link will be updated here before submission.
> To run locally: follow the Quickstart above. A sample PDF is included at `api/fixtures/sample_siemens_3rt2015_datasheet.pdf`.

## Results

Evaluated against a synthetic-but-realistic sample of hand-labeled industrial products (see [`scripts/eval.py`](scripts/eval.py) and [`docs/EVALUATION.md`](docs/EVALUATION.md)). **Not real manufacturer data** — synthetic fixtures written and labeled by the team, including deliberately adversarial cases designed to fail. Numbers are reproducible:

```bash
python scripts/eval.py
```

| Metric | Value |
|--------|-------|
| Field-level accuracy | **85.2%** (23/27 fields) |
| HITL routing precision | **100%** — every wrong field flagged for review |
| HITL routing recall | **100%** — no low-confidence field slipped through |
| Avg confidence (correct fields) | **0.795** |
| Avg confidence (incorrect fields) | **0.345** |
| Calibration gap | **+0.450** — system is measurably less confident when it's wrong |

_Includes 4 adversarial cases: datasheet typo contradiction, irrecoverable missing field, OCR misread on worn label, outdated web-only source. All 4 failures were correctly routed to human review. Full methodology in [docs/EVALUATION.md](docs/EVALUATION.md)._

## Tech Stack

- **Backend**: Python 3.11, FastAPI, async, SSE streaming
- **LLM**: Groq API — `llama-3.3-70b-versatile` for extraction; `llama-4-scout` for vision (where available)
- **RAG / Vector store**: pgvector (Postgres) for catalog retrieval
- **Database**: Postgres — product records, field-level audit trail, review queue
- **Frontend**: Next.js 14, Tailwind CSS
- **Containerisation**: Docker + docker-compose
- **Deploy**: Vercel (frontend) + Render (backend) + Supabase (hosted pgvector)
- **CI**: GitHub Actions — lint, test, build on every push

## Repo Note

_Built at UNIHACK. The repository is named Unindustry (team name) — the project is called ProductTruth. Core logic developed over ~12 hours; commits reflect integration milestones rather than every individual change._

## What's Next

- Scale RAG index to full real manufacturer catalog corpora
- Active learning: HITL corrections feed back into verifier confidence calibration
- Second schema target: GS1 (retail/FMCG adjacency)
- Provider abstraction for VLM (swap llama-4-scout → GPT-4o-vision or Gemini)
- Akeneo / Pimcore direct PIM export

## License

MIT — see [LICENSE](LICENSE)
