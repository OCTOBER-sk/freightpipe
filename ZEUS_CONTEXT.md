# Zeus Context — FreightPipe Backend Phases 1-2

## Project
FreightPipe — headless freight document normalization API.
Repo: /home/santhosh/projects/freight-doc-normalizer/backend/
Design truth: /home/santhosh/projects/freight-doc-normalizer/BACKEND.md

## Your task: Phases 1-2 from CODING_PLAN.md

### Phase 1: DB + LLM Router

**B1.1 Database layer:**
- Implement full schema from BACKEND.md §3.1 (9 tables: accounts, api_keys, jobs, documents, extracted_fields, match_results, review_queue, llm_cache, provider_usage_log)
- Use asyncpg for Neon Postgres connection (serverless, scale-to-zero compatible)
- Repository pattern: one repo module per table
- Alembic migration with initial schema

**B1.2 LLM Router:**
- Provider-agnostic router per BACKEND.md §2.1
- Key pool with round-robin + health state tracking per key
- 429/rate-limit backoff (exponential: 30s, 60s, 120s, cap 10min)
- Fallback chain: OpenRouter free → Gemini Flash → Groq → BYOK
- Response cache: sha256(prompt_template_id + normalized_text + schema_version), Postgres llm_cache table, 30-day TTL
- Daily budget tracker: 90% soft ceiling per provider
- Metering: provider_usage_log table, incremented per call

### Phase 2: Ingest + Classify + Split

**B2.1 Document ingestion:**
- R2 upload handler (boto3-compatible, Cloudflare R2 endpoint)
- PDF validation (magic bytes + parse attempt)
- Job creation (INSERT jobs, return 202)
- Idempotency check (UNIQUE account_id + idempotency_key)

**B2.2 Classification:**
- Rules-first: regex/keyword scoring against freight doc headers
- LLM escalation when score < 0.75 or top-2 within 0.1
- Prompt template from BACKEND.md §6.1

**B2.3 Merged-PDF page-split:**
- Header-repeat detection
- Font/layout discontinuity heuristics (pdfplumber)
- LLM fallback (summarized page digest)
- Split → individual R2 objects + documents rows

## Self-review requirement
After completing each phase, run all tests, verify against BACKEND.md, and report PASS/FAIL for each checkpoint. Fix any failures before reporting done.

## Key constraints
- Free tier only — no paid services
- All endpoints must match BACKEND.md §4.1 exactly
- Error codes must match BACKEND.md §4.3 exactly
- Status enums must match BACKEND.md §3.1 exactly
