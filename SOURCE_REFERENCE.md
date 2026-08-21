# FreightPipe — Final Source Reference

**Generated:** 2026-08-20 20:30 IST
**Repo:** github.com/OCTOBER-sk/freightpipe (private)
**Status:** All coding complete. Deployment pending (needs credentials).

---

## Architecture (Free Tier — No Credit Card Required)

| Layer | Service | Free Tier | Card? |
|---|---|---|---|
| API edge | Cloudflare Workers | 100K req/day | No |
| Processing | **Render free** | 750 hrs/month, 512MB RAM, auto-deploy from GitHub | No |
| DB + PDF storage | Neon Postgres | 0.5GB (DB + PDFs as BYTEA) | No |
| LLM | OpenRouter free + Gemini Flash + Groq + BYOK | Pooled free tiers | No |
| Frontend | Cloudflare Pages | Static, unlimited bandwidth | No |
| DNS/CDN | Cloudflare free | SSL, DDoS protection | No |

**Key decision:** PDFs stored in Postgres as BYTEA (no R2/S3 — Sandy's constraint: no credit card).

---

## Backend — 391 Tests Passing

### Pipeline (10 modules)
| Module | Purpose | Spec Reference |
|---|---|---|
| `pipeline/ingest.py` | PDF validation, job creation, idempotency | BACKEND.md §4.1 |
| `pipeline/classify.py` | Rules-first + LLM escalation | §5.1 |
| `pipeline/split.py` | Merged-PDF page-split | §5.2 |
| `pipeline/extract.py` | Text/OCR/vision extraction | §5.3, §6.1 |
| `pipeline/normalize.py` | Dates, money, units, accessorial vocab | §5.4 |
| `pipeline/validate.py` | Required fields, date/money sanity | §5.5 |
| `pipeline/match.py` | 3-way match engine | §5.6 |
| `pipeline/confidence.py` | Per-field + per-doc scoring, HITL routing | §5.7 |
| `pipeline/review.py` | State machine (pending→in_review→resolved/escalated) | §5.8 |

### API (18 endpoints)
| # | Method | Path | Status |
|---|---|---|---|
| 1 | POST | /v1/documents | 202 |
| 2 | GET | /v1/jobs | 200 |
| 3 | GET | /v1/jobs/{id} | 200 |
| 4 | GET | /v1/jobs/{id}/result | 200/409 |
| 5 | GET | /v1/review-queue | 200 |
| 6 | POST | /v1/review-queue/{id}/resolve | 200 |
| 7 | GET | /v1/documents/{id}/pdf | 200 (binary PDF) |
| 8 | POST | /v1/webhooks/test | 200 |
| 9 | GET | /v1/health | 200 |
| 10 | GET | /v1/api-keys | 200 |
| 11 | POST | /v1/api-keys | 201 |
| 12 | DELETE | /v1/api-keys/{id} | 200 |
| 13 | GET | /v1/settings/webhook | 200 |
| 14 | PUT | /v1/settings/webhook | 200 |
| 15 | GET | /v1/analytics/usage | 200 |
| 16 | — | Webhook dispatch (4 events) | — |
| 17 | — | Error envelope (9 codes) | — |
| 18 | — | Rate limiting (60/hr/account) | 429 |

### DB (9 tables)
accounts, api_keys, jobs (with pdf_data BYTEA), documents, extracted_fields, match_results, review_queue, llm_cache, provider_usage_log

### LLM Router
- Key pool: round-robin, health tracking, 429 backoff (30s→60s→120s→300s→600s)
- Fallback: OpenRouter → Gemini Flash → Groq → BYOK
- Cache: sha256 key, Postgres llm_cache, 30-day TTL
- Budget: 90% soft ceiling per provider

---

## Frontend — 12 Components + 9 Routes

### Design System
- Dark theme: #0E1013 base, #16191D surface
- Typography: Inter (UI) + JetBrains Mono (data)
- Signature: confidence rail (3px left-edge bar)
- No gradients, no shadows, no emoji, no generic SaaS

### Components (12)
ConfidenceBadge, DiscrepancyFlag, DocTypeIndicator, JobStatusPill, ConfidenceRail, ReviewQueueCard, FieldDetailRow, MatchResultRow, UploadZone, WebhookStatusIndicator, ApiKeyCard, PdfViewerWithOverlay

### Routes (9)
JobList, JobSubmit, JobDetail, JobResult, ReviewQueueList, ReviewItemDetail, Analytics, ApiKeys, Webhooks

---

## Credentials Needed for Deployment

| Credential | Used for | Env var |
|---|---|---|
| Neon Postgres URL | Backend DB + PDF storage | NEON_DATABASE_URL |
| OpenRouter API key(s) | LLM router | OPENROUTER_API_KEYS |
| Gemini API key(s) | LLM router + vision OCR | GEMINI_API_KEYS |
| Groq API key(s) | LLM router fallback | GROQ_API_KEYS |
| **Render account** | Backend hosting | render.com (free, no card, GitHub login) |
| Cloudflare account | Frontend (Pages) + Workers | — |
| Webhook HMAC secret | Webhook signing | WEBHOOK_HMAC_SECRET |
| BYOK encryption key | Tenant BYOK keys | BYOK_ENCRYPTION_KEY |

---

## Git History (7 commits)

```
b2af2ff REFACTOR: Replace Cloudflare R2 with Postgres BYTEA storage
c38db52 Phase 4 COMPLETE: All 18 API endpoints — 394 tests
33289b5 Phase 7 COMPLETE: All 9 route pages + CSS modules
46a73b8 Phase 2 COMPLETE: Pipeline (Extract + Normalize + Validate)
e7da3de Phase 1 COMPLETE: DB repos + LLM router + Alembic migration
1333cb7 Phase 1 partial: DB repos + alembic migration
459c834 Phase 0: scaffold backend + frontend
```
