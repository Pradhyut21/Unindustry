# Changelog

All notable changes to ProductTruth are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Planned
- Redis Pub/Sub to replace in-memory SSE queue (scalability)
- CI/CD deployment pipeline to Render + Vercel
- Active learning: HITL corrections feed back into verifier calibration

---

## [0.2.0] — 2026-08-05

### Added
- 4 new test files covering Doc-Intel, Vision, Retrieval, Orchestrator, and HITL Router agents
- Orchestrator integration tests with monkeypatched agents, real DB writes
- `_parse_value_from_line` unit tests (8 edge cases covering colon, tab, and noise patterns)
- `_extract_value_from_snippet` unit tests for retrieval agent pure function
- HITL Router event emission tests (zero vs. non-zero hitl_count)
- Vision agent graceful-skip tests (no images / no API key / no vision model)

### Fixed
- README: removed placeholder demo link that signalled incomplete submission
- CONTRIBUTORS: clarified primary authorship for placement context
- CHANGELOG: expanded from scaffold-only to full build history

---

## [0.1.3] — 2026-08-04

### Fixed
- **CI event loop bug**: `pytest-asyncio` fixture teardown was closing the event loop
  before `engine.dispose()` could complete. Fixed by restructuring `conftest.py`
  to separate engine disposal from async fixture lifecycle.
- **Async SQLAlchemy session leak**: `AsyncSession` was not being closed in error paths
  within the orchestrator pipeline. Added explicit `async with` context management
  throughout all agent DB interactions.

---

## [0.1.2] — 2026-08-04

### Added
- Full verifier unit test suite — 37 tests across all `uncertainty_reason` categories
  and edge cases: contradiction, single-source, low-quality, no-source, value normalisation,
  min_sources boundary conditions, and source preference ordering
- Schema mapper unit tests: unit normalisation, ETIM field mapping, empty-input handling
- API route integration tests: health check, products CRUD, review queue endpoints
- Eval script (`scripts/eval.py`) — 12 synthetic products, 27 labeled fields, adversarial cases
- Coverage reporting to CI via `--cov=api --cov-report=xml`

### Changed
- CI matrix expanded to Python 3.11 AND 3.12 (parallel jobs)
- CI now runs eval script as a separate step after tests
- CI runs Docker build as a post-test smoke check

---

## [0.1.1] — 2026-08-04

### Added
- All 7 agent implementations: Orchestrator, Doc-Intel, Vision, Retrieval, Verifier,
  Schema Mapper, HITL Router
- SSE streaming router with in-memory event queue per product_id
- Frontend: pipeline visualization page with live agent card animation
- Frontend: product detail page with per-field confidence badges and citation drawer
- Frontend: human review queue (accept / edit+accept / reject per field)
- `SOURCE_CONTRADICTION` UI — shows both conflicting values side-by-side on product page
- `schemas/etim_schema.json` — ETIM-inspired target commerce schema
- Sample Siemens 3RT2015 datasheet fixture for local demo

### Changed
- Confidence scoring rubric documented directly in `verifier_agent.py` module docstring
- All agents inherit from `BaseAgent` with `emit_event()` for SSE

---

## [0.1.0] — 2026-08-04

### Added
- Initial repo scaffold
- Postgres schema: `products`, `product_fields`, `field_sources`, `review_queue`
- FastAPI skeleton with `/health` and `/api/v1` prefix
- SQLAlchemy + Pydantic models
- Docker Compose: postgres (pgvector/pg16), api, web services
- Multi-stage Dockerfile for the API
- ETIM-inspired target commerce schema (`schemas/etim_schema.json`)
- MIT license, CONTRIBUTORS.md
