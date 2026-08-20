#!/bin/bash
cd /home/santhosh/projects/freight-doc-normalizer/backend

opencode run --agent default --model opencode-go/mimo-v2.5-pro "
PHASE 4: API Routes — All 18 Endpoints

Read /home/santhosh/projects/freight-doc-normalizer/BACKEND.md section 4.1 for the full API contract.
The pipeline modules (classify, split, extract, normalize, validate, match, confidence, review) and DB repos are already complete.

Complete src/freightpipe/api/routes.py with ALL 18 endpoints:

1. POST /v1/documents - submit PDF (multipart/form-data), validate, create job, return 202
2. GET /v1/jobs - list jobs (paginated, filterable by status), cursor-based
3. GET /v1/jobs/{job_id} - poll job status
4. GET /v1/jobs/{job_id}/result - full structured output (documents + fields + match_results)
5. GET /v1/review-queue - list review items (filterable by state/reason, paginated)
6. POST /v1/review-queue/{item_id}/resolve - resolve (approved/corrected/escalated)
7. GET /v1/documents/{document_id}/pdf - signed R2 URL (5min TTL)
8. POST /v1/webhooks/test - test webhook delivery
9. GET /v1/health - liveness check (worker + processor status)
10. GET /v1/api-keys - list keys (masked)
11. POST /v1/api-keys - create key (raw key shown once in response)
12. DELETE /v1/api-keys/{key_id} - revoke key
13. GET /v1/settings/webhook - get account-level webhook config
14. PUT /v1/settings/webhook - set/update webhook config
15. GET /v1/analytics/usage - usage metrics (7d/30d/90d period)
16. Webhook dispatch (job.completed, job.needs_review, job.failed, review.resolved)
17. Error envelope (BACKEND.md section 4.3): invalid_pdf, file_too_large, unauthorized, rate_limited, job_not_found, job_not_complete, idempotency_conflict, internal_error, llm_capacity_exhausted
18. Rate limiting (60 submissions/hour per account)

Also create:
- src/freightpipe/api/auth.py - X-Api-Key header validation, account-scoped access
- src/freightpipe/api/webhooks.py - webhook dispatch with HMAC signing
- src/freightpipe/api/rate_limit.py - per-account rate limiting

Write tests/test_api.py with at least 20 test cases covering:
- All endpoint happy paths
- Error codes from BACKEND.md section 4.3
- Auth (valid key, invalid key, missing key)
- Idempotency (duplicate submission returns same job)
- Pagination (cursor-based)

SELF-REVIEW (mandatory):
- Run: python -m pytest tests/ -v --tb=short
- Verify ALL 18 endpoints exist and match BACKEND.md section 4.1 exactly
- Verify error codes match section 4.3 exactly
- Verify response schemas match section 4.1 exactly
- Report: files changed, test count, endpoint count

Do NOT modify pipeline/ or db/repos/ modules (already complete).
Do NOT add new pip dependencies.
" 2>&1 | tee /tmp/zeus-phase4.log
