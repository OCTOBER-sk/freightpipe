#!/bin/bash
cd /home/santhosh/projects/freight-doc-normalizer/backend

opencode run --agent default --model opencode-go/mimo-v2.5-pro "
PHASE 1: Database Layer + LLM Router

You are working on FreightPipe, a freight document normalization API.
Read /home/santhosh/projects/freight-doc-normalizer/BACKEND.md for the full spec.

STEP 1: Create the database repository layer.
Create these files in src/freightpipe/db/repos/:

1. src/freightpipe/db/repos/__init__.py - exports all repos
2. src/freightpipe/db/repos/base.py - BaseRepo class with asyncpg pool, common CRUD helpers
3. src/freightpipe/db/repos/jobs.py - JobsRepo: create, get_by_id, list_paginated (with status filter), update_status, get_by_idempotency_key
4. src/freightpipe/db/repos/documents.py - DocumentsRepo: create, get_by_job_id, get_by_id
5. src/freightpipe/db/repos/extracted_fields.py - ExtractedFieldsRepo: create_many, get_by_document_id
6. src/freightpipe/db/repos/match_results.py - MatchResultsRepo: create_many, get_by_shipment_id
7. src/freightpipe/db/repos/review_queue.py - ReviewQueueRepo: create, list_paginated (with state/reason filter), get_by_id, resolve (approved/corrected/escalated)
8. src/freightpipe/db/repos/api_keys.py - ApiKeysRepo: create, list_by_account, get_by_hash, revoke
9. src/freightpipe/db/repos/accounts.py - AccountsRepo: create, get_by_id
10. src/freightpipe/db/repos/llm_cache.py - LlmCacheRepo: get_by_key, set, cleanup_expired
11. src/freightpipe/db/repos/provider_usage.py - ProviderUsageRepo: increment, get_by_date_range

All repos use asyncpg. Pool comes from src/freightpipe/db/connection.py (already exists).
All queries filter by account_id where applicable (security).
Use parameterized queries (never string interpolation for SQL).

STEP 2: Create the Alembic initial migration.
Create alembic/versions/001_initial.py with the FULL schema from BACKEND.md section 3.1.
All 9 tables: accounts, api_keys, jobs, documents, extracted_fields, match_results, review_queue, llm_cache, provider_usage_log.
All indexes listed in the spec.

STEP 3: Implement the LLM Router.
Complete src/freightpipe/llm/router.py with:
- KeyState dataclass: key, provider, requests_today, requests_this_minute, last_used_at, cooldown_until, is_healthy property
- LLMRouter class:
  - load_keys() - reads comma-separated keys from env vars (OPENROUTER_API_KEYS, GEMINI_API_KEYS, GROQ_API_KEYS)
  - get_healthy_key(provider) - returns least-recently-used healthy key
  - complete(task_type, prompt, schema, requires_vision) - routes through fallback chain: openrouter -> gemini -> groq -> byok
  - handle_429(key, retry_after) - marks key cooldown with exponential backoff (30s, 60s, 120s, cap 10min)
  - check_cache(cache_key) - queries llm_cache table, returns cached response if not expired
  - store_cache(cache_key, provider, model, response, ttl_days=30) - inserts into llm_cache
  - track_usage(provider, model) - increments provider_usage_log
  - check_budget(provider) - returns True if requests_today < daily_limit * 0.9
  - static cache_key(prompt_template_id, text_hash, schema_version) - sha256 hash

STEP 4: Create tests.
Write tests/test_db.py and tests/test_llm_router.py with:
- Test all repo CRUD operations (mock asyncpg)
- Test LLM router key selection, fallback, cache, budget tracking
- At least 15 test cases total

STEP 5: SELF-REVIEW (mandatory):
- Run: cd /home/santhosh/projects/freight-doc-normalizer/backend && python -m pytest tests/ -v --tb=short
- Re-read your changes against BACKEND.md section 3.1 - verify ALL table columns match exactly
- Verify ALL enum values match (JobStatus has 12 values, DocType has 5, DiscrepancyFlag has 6, ReviewReason has 5)
- Report: files changed, test count, any risks

Do NOT touch any files outside backend/src/freightpipe/db/, backend/src/freightpipe/llm/, backend/alembic/, and backend/tests/.
Do NOT add any new pip dependencies.
Do NOT create placeholder/stub files - write real working code.
" 2>&1 | tee /tmp/zeus-phase1.log
