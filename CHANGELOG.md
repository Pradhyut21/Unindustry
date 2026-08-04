# Changelog

All notable changes to ProductTruth are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

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
