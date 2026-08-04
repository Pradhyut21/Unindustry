# ProductTruth

![CI](https://github.com/PLACEHOLDER/producttruth/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)

> Turns limited product inputs into commerce-ready records where every field
> is confidence-scored and traceable to its source — instead of silently hallucinated.

<!-- INSERT 15–30 sec demo GIF here after recording -->

## The Problem

Industrial manufacturers have thousands of products with incomplete catalog data — a name, maybe one spec sheet PDF, maybe a photo. Filling the gaps today means either expensive manual data entry, or AI enrichment that quietly hallucinates specifications nobody catches until a customer receives the wrong part. In industrial B2B, a wrong voltage rating or missing ISO certification isn't a typo — it's a liability.

## How ProductTruth Works

Given any combination of inputs (product name, spec PDF, product photos, competitor URL), a multi-agent pipeline extracts, cross-verifies, and normalises a full structured product record. Every field carries:
- A **confidence score** (0.0–1.0)
- A **citation trail** back to the exact source (PDF page, image region, URL snippet)
- An **uncertainty reason** if confidence is low (`SINGLE_SOURCE`, `SOURCE_CONTRADICTION`, `LOW_QUALITY_EXTRACTION`, `NO_SOURCE_FOUND`)

Fields below the confidence threshold (default 0.7) are routed to a **human review queue** with side-by-side evidence, instead of going live wrong.

## Architecture

```
INPUT (product name + PDF + photos + URL)
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
git clone https://github.com/PLACEHOLDER/producttruth
cd producttruth
cp .env.example .env          # add your ANTHROPIC_API_KEY
docker-compose up
```

Open [http://localhost:3000](http://localhost:3000)

## Quickstart (Deployed)

Live demo: **https://PLACEHOLDER.vercel.app**

## Results

Evaluated against a synthetic-but-realistic sample of hand-labeled industrial products (see [`scripts/eval.py`](scripts/eval.py) and [`docs/EVALUATION.md`](docs/EVALUATION.md)). **Not real manufacturer data** — synthetic fixtures written and labeled by the team, explicit about this so the numbers are honest.

```
python scripts/eval.py
```

| Metric | Value |
|--------|-------|
| Field-level accuracy | **100%** (18/18 fields) |
| Fields correctly routed to human review | **100% precision, 100% recall** (6/18 routed) |
| Avg confidence of correct fields | **0.777** |
| Confidence calibration gap | **+0.777** (higher = better calibrated) |

_Evaluated on 8 synthetic-but-realistic industrial products (18 hand-labeled fields) — written and verified by the team. Not real manufacturer data. See [docs/EVALUATION.md](docs/EVALUATION.md) for methodology and caveats._

## Tech Stack

- **Backend**: Python 3.11, FastAPI, async, SSE streaming
- **LLM/VLM**: Claude (Anthropic) — vision + text extraction and verification
- **RAG / Vector store**: pgvector (Postgres) for catalog retrieval
- **Database**: Postgres — product records, field-level audit trail, review queue
- **Frontend**: Next.js 14, Tailwind CSS
- **Containerisation**: Docker + docker-compose
- **Deploy**: Vercel (frontend) + Render (backend) + Supabase (hosted pgvector)
- **CI**: GitHub Actions — lint, test, build on every push

## What's Next

- Scale RAG index to full real manufacturer catalog corpora
- Active learning: HITL corrections feed back into verifier confidence calibration
- Second schema target: GS1 (for retail/FMCG adjacency)
- Provider abstraction for VLM (swap Claude → GPT-4o-vision or Gemini)
- Akeneo / Pimcore direct PIM export

## License

MIT — see [LICENSE](LICENSE)
