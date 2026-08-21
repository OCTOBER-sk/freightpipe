<div align="center">

# 📦 FreightPipe

**Headless freight document normalization API**

Turn messy freight PDFs into clean, validated JSON with 3-way matching — no TMS required.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

</div>

---

## What it is

FreightPipe ingests freight documents — rate confirmations, Bills of Lading, Proofs of Delivery, and carrier invoices (often merged into a single PDF) — and returns structured, validated JSON with per-field confidence scores and a 3-way match across the shipment lifecycle.

Built for small freight brokerages and carriers who need document automation without adopting a full TMS platform.

## What it does

- 📄 **Multi-format ingestion** — PDF upload via API, handles merged documents (rate-con + BOL + invoice in one file)
- 🔍 **Intelligent extraction** — Rules-first pipeline with LLM escalation for messy/scanned documents
- 🔗 **3-way match engine** — Compares agreed (rate-con) ↔ delivered (BOL/POD) ↔ billed (invoice), flags discrepancies
- 📊 **Confidence scoring** — Per-field confidence (0–1) with automatic human-in-the-loop routing
- ✅ **Review dashboard** — Dark-themed React UI for reviewing flagged documents with inline corrections
- 🔌 **Provider-agnostic LLM** — Pools OpenRouter, Gemini Flash, and Groq free tiers with automatic fallback

## How it works

1. **Submit** a PDF via `POST /v1/documents`
2. **Pipeline** classifies, splits (if merged), extracts fields, normalizes, validates, and matches
3. **Review** items below confidence threshold appear in the dashboard for human correction
4. **Results** returned as structured JSON with source coordinates and confidence scores

## Quick start

```bash
# Clone
git clone https://github.com/OCTOBER-sk/freightpipe.git
cd freightpipe

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env  # fill in your Neon URL + LLM keys
python -m uvicorn freightpipe.api.app:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/bootstrap` | Create first account + API key |
| `POST` | `/v1/documents` | Submit PDF for processing |
| `GET` | `/v1/jobs` | List all jobs |
| `GET` | `/v1/jobs/{id}` | Poll job status |
| `GET` | `/v1/jobs/{id}/result` | Get structured output |
| `GET` | `/v1/review-queue` | List items needing review |
| `POST` | `/v1/review-queue/{id}/resolve` | Approve/correct/escalate |
| `GET` | `/v1/analytics/usage` | Usage metrics |
| `GET` | `/v1/health` | Liveness check |

Full API documentation in [`BACKEND.md`](BACKEND.md).

## Architecture

```
Client → Cloudflare Workers (edge) → Render (FastAPI) → Neon Postgres
                                    ↓
                              LLM Router (OpenRouter → Gemini → Groq)
```

**Free tier only** — no credit card required for any service.

| Layer | Service | Free Tier |
|-------|---------|-----------|
| Processing | Render | 750 hrs/month |
| Database | Neon Postgres | 0.5GB |
| LLM | OpenRouter + Gemini + Groq | Pooled free tiers |
| Frontend | Cloudflare Pages | Unlimited |

## Tech stack

**Backend:** Python 3.11 · FastAPI · asyncpg · pdfplumber · pypdf
**Frontend:** React 18 · TypeScript · Vite · TanStack Query · Recharts · react-pdf
**Database:** Neon Postgres (PDFs stored as BYTEA — no external object storage)
**LLM:** Provider-agnostic router with key pooling, caching, and budget tracking

## Project structure

```
freightpipe/
├── backend/
│   ├── src/freightpipe/
│   │   ├── api/          # FastAPI routes, auth, rate limiting
│   │   ├── db/           # Connection pool, 9 repository modules
│   │   ├── llm/          # Provider-agnostic LLM router
│   │   ├── pipeline/     # Classify → split → extract → normalize → validate → match
│   │   ├── models/       # Pydantic schemas
│   │   └── utils/        # Configuration
│   └── tests/            # 391 tests
├── frontend/
│   ├── src/
│   │   ├── components/   # 12 reusable components
│   │   ├── routes/       # 9 page components
│   │   ├── api/          # API client layer
│   │   └── types/        # TypeScript types (synced with backend)
│   └── dist/             # Built frontend
├── BACKEND.md            # Backend design document
├── FRONTEND.md           # Frontend design document
└── PROJECT.md            # Authoritative project spec
```

## Design philosophy

- **Deterministic rules first, LLM escalation second** — regex/heuristics handle the 80% of clean documents; LLM handles the fuzzy 20%
- **Gates before tokens** — budget/type/locality filters run before the LLM sees anything
- **Price-echo verification** — every price in a generated draft must match the source data verbatim
- **Measured, not claimed** — accuracy targets are benchmarks to verify on a corpus, never assertions

## License

MIT
