# FreightPipe — End-to-End Coding Plan

**Repo:** github.com/OCTOBER-sk/freightpipe
**Design truth:** BACKEND.md + FRONTEND.md (synced, 18/18 endpoints ✅)
**Agents:** Zeus (backend, mimo v2.5) + Midas (frontend, mimo v2.5)
**Supervisor:** Atom (QA, sync verification, deployment)

---

## PHASE 0: Project Scaffolding (Atom — parallel)

### B0. Backend scaffold
- [ ] Create `backend/` directory structure per BACKEND.md §11
- [ ] `pyproject.toml` with deps: fastapi, uvicorn, pdfplumber, pypdf, Pillow, httpx, asyncpg, pg-boss-py (or psycopg2 + custom queue), boto3 (R2), python-multipart
- [ ] `.env.example` with all keys from BACKEND.md §11.2
- [ ] Dockerfile (for Koyeb deployment)
- [ ] `alembic/` migrations directory with initial schema from BACKEND.md §3.1

### F0. Frontend scaffold
- [ ] `npm create vite@latest frontend -- --template react-ts`
- [ ] Install deps: @tanstack/react-query, react-pdf, recharts, react-router-dom
- [ ] Set up CSS Modules + tokens.css from FRONTEND.md §1.2–1.4
- [ ] Set up file tree per FRONTEND.md §11
- [ ] Configure for Cloudflare Pages deployment

---

## PHASE 1: Backend Core — DB + LLM Router (Zeus)

### B1.1 Database layer
- [ ] Implement full schema from BACKEND.md §3.1 (all 9 tables)
- [ ] Alembic migration: initial create
- [ ] Connection pool (asyncpg, Neon-compatible)
- [ ] Repository pattern: `jobs_repo`, `documents_repo`, `extracted_fields_repo`, `match_results_repo`, `review_queue_repo`

### B1.2 LLM Router
- [ ] Provider-agnostic router per BACKEND.md §2.1
- [ ] Key pool with round-robin + health state tracking
- [ ] 429/rate-limit backoff (exponential: 30s, 60s, 120s, cap 10min)
- [ ] Fallback chain: OpenRouter free → Gemini Flash → Groq → BYOK
- [ ] Response cache (sha256 key, Postgres `llm_cache` table, 30-day TTL)
- [ ] Daily budget tracker (90% soft ceiling)
- [ ] Metering log (`provider_usage_log` table)

### B1.3 Self-review checkpoint
- [ ] Zeus runs: `python -m pytest tests/test_llm_router.py -v`
- [ ] Zeus runs: `python -m pytest tests/test_db.py -v`
- [ ] Verify: all tests pass, no import errors, schema matches BACKEND.md §3.1

---

## PHASE 2: Pipeline — Ingest + Classify + Split (Zeus)

### B2.1 Document ingestion
- [ ] R2 upload handler (boto3-compatible, Cloudflare R2 endpoint)
- [ ] PDF validation (magic bytes + parse attempt, reject at 400)
- [ ] Job creation (INSERT into `jobs`, return 202)
- [ ] Idempotency check (`UNIQUE (account_id, idempotency_key)`)

### B2.2 Classification
- [ ] Rules-first: regex/keyword scoring against freight doc headers
- [ ] LLM escalation when score < 0.75 or top-2 within 0.1
- [ ] Classification prompt template from BACKEND.md §6.1
- [ ] Store result on `documents.doc_type` + `documents.classification_confidence`

### B2.3 Merged-PDF page-split
- [ ] Header-repeat detection
- [ ] Font/layout discontinuity heuristics (pdfplumber metadata)
- [ ] LLM fallback (summarized page digest, not full pages)
- [ ] Split segments → individual R2 objects + `documents` rows

### B2.4 Self-review checkpoint
- [ ] Zeus runs: `python -m pytest tests/test_ingest.py tests/test_classify.py tests/test_split.py -v`
- [ ] Test with sample PDFs (create 3 test fixtures: single rate-con, merged rate-con+BOL+invoice, scanned POD)

---

## PHASE 3: Pipeline — Extract + Normalize + Validate (Zeus)

### B3.1 Extraction
- [ ] Born-digital path: pdfplumber/pypdf text extraction
- [ ] Scan detection (text density threshold: >20 chars/page)
- [ ] OCR path: Gemini Flash vision (primary) → pytesseract (fallback) → PaddleOCR (secondary)
- [ ] LLM extraction prompt templates from BACKEND.md §6.1
- [ ] Structured output enforcement (JSON schema where supported, post-processing fallback)
- [ ] Store per-field in `extracted_fields` with confidence + source bbox

### B3.2 Normalization
- [ ] Dates → ISO 8601 (reference_date = job submission date)
- [ ] Money → `{"amount": float, "currency": "USD"}`
- [ ] Units → weight to lbs
- [ ] Accessorial vocabulary mapping (controlled vocab + synonym table)

### B3.3 Domain validation
- [ ] Required fields check per doc type (BACKEND.md §3.2)
- [ ] Date sanity (pickup ≤ delivery ≤ due date)
- [ ] Money sanity (total ≈ linehaul + fuel + accessorials, $0.02 tolerance)
- [ ] Load number cross-reference

### B3.4 Self-review checkpoint
- [ ] Zeus runs: `python -m pytest tests/test_extract.py tests/test_normalize.py tests/test_validate.py -v`
- [ ] Verify: extraction produces valid canonical JSON, normalization is deterministic

---

## PHASE 4: Pipeline — Match + Score + Review Queue (Zeus)

### B4.1 3-way match engine
- [ ] Pairwise comparison per line item category (BACKEND.md §5.6)
- [ ] Discrepancy flags: rate_delta, missing_accessorial, extra_accessorial, weight_variance, pieces_variance
- [ ] Write `match_results` rows

### B4.2 Confidence scoring
- [ ] Per-field: rule-extracted = 0.95–0.99 fixed; LLM-extracted = verification pass; OCR-capped at 0.85
- [ ] Per-document: weighted average of required fields, floored by classification confidence
- [ ] HITL routing: doc confidence < 0.80 OR any field < 0.70 OR any discrepancy → `review_queue`

### B4.3 Review queue state machine
- [ ] States: pending → in_review → resolved/escalated (BACKEND.md §5.8)
- [ ] Resolve endpoint: approved / corrected / escalated
- [ ] Corrections write-back to `extracted_fields`

### B4.4 Self-review checkpoint
- [ ] Zeus runs: `python -m pytest tests/test_match.py tests/test_confidence.py tests/test_review.py -v`
- [ ] E2E test: submit PDF → extract → match → score → review queue → resolve → complete

---

## PHASE 5: API Layer + Auth (Zeus)

### B5.1 All 18 endpoints
- [ ] `POST /v1/documents` (submit, 202)
- [ ] `GET /v1/jobs` (list, paginated, filterable)
- [ ] `GET /v1/jobs/{id}` (poll status)
- [ ] `GET /v1/jobs/{id}/result` (full structured output)
- [ ] `GET /v1/review-queue` (list, filterable by reason)
- [ ] `POST /v1/review-queue/{id}/resolve` (approved/corrected/escalated)
- [ ] `GET /v1/documents/{id}/pdf` (signed R2 URL, 5min TTL)
- [ ] `POST /v1/webhooks/test`
- [ ] `GET /v1/health`
- [ ] `GET /v1/api-keys` (list, masked)
- [ ] `POST /v1/api-keys` (create, raw key shown once)
- [ ] `DELETE /v1/api-keys/{id}` (revoke)
- [ ] `GET /v1/settings/webhook`
- [ ] `PUT /v1/settings/webhook`
- [ ] `GET /v1/analytics/usage` (7d/30d/90d)
- [ ] Webhook dispatch (events: job.completed, job.needs_review, job.failed, review.resolved)
- [ ] Error envelope (BACKEND.md §4.3)
- [ ] Rate limiting (Worker KV, 60/hour/account)

### B5.2 Auth
- [ ] X-Api-Key header validation (sha256 hash lookup)
- [ ] Account-scoped access (all queries filtered by account_id)

### B5.3 Self-review checkpoint
- [ ] Zeus runs: full `python -m pytest tests/ -v`
- [ ] Zeus runs: API integration tests against all 18 endpoints
- [ ] Verify: error codes match FRONTEND.md §9 exactly

---

## PHASE 6: Frontend — Design System + Components (Midas)

### F6.1 Design tokens + global styles
- [ ] tokens.css (all colours from FRONTEND.md §1.2, spacing §1.4)
- [ ] global.css (typography: Inter + JetBrains Mono, scale §1.3)
- [ ] Confidence rail CSS (3px left-edge bar, the signature element)

### F6.2 Core components (all from FRONTEND.md §4)
- [ ] ConfidenceBadge (green/amber/red + numeric + text label, WCAG)
- [ ] DiscrepancyFlag (enum synced to BACKEND.md §3.1)
- [ ] DocTypeIndicator (text labels, not icons)
- [ ] JobStatusPill (full enum, collapses 7 mid-pipeline to "Processing")
- [ ] ConfidenceRail (3px left-edge, the signature element)
- [ ] ReviewQueueCard
- [ ] FieldDetailRow (value + confidence + extraction method tag)
- [ ] MatchResultRow
- [ ] UploadZone (drag-drop, 25MB limit, PDF only)
- [ ] WebhookStatusIndicator
- [ ] ApiKeyCard
- [ ] PdfViewerWithOverlay (react-pdf + bbox highlight)

### F6.3 Self-review checkpoint
- [ ] Midas: visual review of each component in isolation (Storybook or dev server)
- [ ] Verify: all enums match BACKEND.md, all thresholds use CONFIDENCE_THRESHOLDS constant

---

## PHASE 7: Frontend — Pages + API Integration (Midas)

### F7.1 API client layer
- [ ] `api/client.ts` (fetch wrapper, X-Api-Key injection, error handling)
- [ ] `api/jobs.ts` (all job endpoints)
- [ ] `api/reviewQueue.ts`
- [ ] `api/webhooks.ts`
- [ ] `api/settings.ts` (API keys, webhook config)
- [ ] `api/analytics.ts`
- [ ] `types/backend.ts` (TS types mirroring BACKEND.md §3 exactly)
- [ ] `config/confidence.ts` (CONFIDENCE_THRESHOLDS constant)
- [ ] `hooks/useJobPolling.ts` (backoff schedule from FRONTEND.md §6)
- [ ] `hooks/useReviewResolve.ts`

### F7.2 Pages
- [ ] JobList (`/jobs`) — table, filters, confidence rails, status pills
- [ ] JobSubmit (`/jobs/new`) — upload zone, webhook field, idempotency key
- [ ] JobDetail (`/jobs/:id`) — stage progress track, cold-start advisory, polling
- [ ] JobResult (`/jobs/:id/result`) — document cards, field detail, match table
- [ ] ReviewQueueList (`/review-queue`) — oldest-first, reason filter, live count badge
- [ ] ReviewItemDetail (`/review-queue/:id`) — PDF+overlay left, editable fields right, approve/correct/escalate
- [ ] Analytics (`/analytics`) — Recharts: volume, accuracy, processing time, LLM usage
- [ ] ApiKeys (`/settings/api-keys`) — list, create (show once), revoke
- [ ] Webhooks (`/settings/webhooks`) — config, test button

### F7.3 Error + empty states
- [ ] All error codes from FRONTEND.md §9 implemented
- [ ] All empty states designed (no illustrations, no confetti)

### F7.4 Self-review checkpoint
- [ ] Midas: full user-flow walkthrough (submit → poll → review → resolve → result)
- [ ] Midas: responsive check at 768px (tablet stacking)
- [ ] Verify: polling backoff matches §6, all status enums correct

---

## PHASE 8: Integration + Deployment (Atom)

### B8.1 Backend deployment
- [ ] Push to Koyeb (free Instance, git-push-to-deploy)
- [ ] Verify: health endpoint returns 200
- [ ] Set up Neon Postgres (run migrations)
- [ ] Configure R2 bucket
- [ ] Set all env vars

### F8.1 Frontend deployment
- [ ] Build: `npm run build`
- [ ] Deploy to Cloudflare Pages
- [ ] Configure API base URL (point to Koyeb backend)
- [ ] Verify: full user flow works live

### A8.1 E2E verification
- [ ] Submit a test PDF → job completes → review queue populated → resolve → result view
- [ ] Verify webhook delivery
- [ ] Verify analytics populate
- [ ] Verify API key create/list/revoke

---

## Credentials Needed (Sandy provides)

| Credential | Used for | When needed |
|---|---|---|
| Neon Postgres connection string | Backend DB | Phase 1 |
| Cloudflare R2 credentials (account_id, access_key, secret, bucket) | PDF storage | Phase 2 |
| OpenRouter API key(s) | LLM router | Phase 1 |
| Google Gemini API key(s) | LLM router + vision OCR | Phase 1 |
| Groq API key(s) | LLM router fallback | Phase 1 |
| Koyeb account + deploy token | Backend hosting | Phase 8 |
| Cloudflare account (for Pages) | Frontend hosting | Phase 8 |
| Domain (optional) | Custom API URL | Phase 8 |

---

## Agent Routing

| Phase | Agent | Model | Notes |
|---|---|---|---|
| B0, F0 | Atom | — | Scaffolding, parallel |
| B1–B5 | Zeus | mimo v2.5 | Backend, sequential phases |
| F6–F7 | Midas | mimo v2.5 | Frontend, sequential phases |
| B8, F8, A8 | Atom | — | Deployment + E2E verification |

**Self-review rule:** After each phase, the agent runs all tests, verifies against the design doc, and reports PASS/FAIL for each checkpoint. Atom supervises and catches sync drift.
