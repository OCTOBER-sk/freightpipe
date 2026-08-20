#!/bin/bash
cd /home/santhosh/projects/freight-doc-normalizer/frontend

opencode run --agent default --model opencode-go/mimo-v2.5-pro "
PHASE 7: Route Page Implementations + Error/Empty States

Read /home/santhosh/projects/freight-doc-normalizer/FRONTEND.md for the full design spec.
Read /home/santhosh/projects/freight-doc-normalizer/BACKEND.md for the API contract.

Complete ALL 9 route page implementations. Each page must have:
- Full layout matching FRONTEND.md ASCII wireframes
- Data fetching via the API client (src/api/*.ts)
- Loading states (skeleton rows, no shimmer animation)
- Error states matching FRONTEND.md section 9
- Empty states matching FRONTEND.md section 9
- Responsive behaviour (tablet stacking at 768px where applicable)

STEP 1: src/routes/jobs/JobList.tsx
- Table with confidence rails, status pills, filter bar
- Data: GET /v1/jobs with pagination (cursor-based)
- Filters: All, Queued, Processing, Needs Review, Complete, Failed
- Empty: 'No jobs yet. Submit your first document to get started.' + upload CTA

STEP 2: src/routes/jobs/JobSubmit.tsx
- Upload zone (drag-drop, 25MB, PDF only)
- Webhook URL field + test button (POST /v1/webhooks/test)
- Idempotency key field (collapsed under 'advanced')
- On 202: redirect to /jobs/:job_id
- Error states: invalid_pdf, file_too_large, rate_limited

STEP 3: src/routes/jobs/JobDetail.tsx
- Stage progress track (horizontal, current stage highlighted)
- Cold-start advisory: 'If this is a cold-start pickup, initial polling may take longer than usual'
- Polling via useJobPolling hook (2s/5s/15s backoff)
- Auto-redirect to /jobs/:id/result on terminal status

STEP 4: src/routes/jobs/JobResult.tsx
- Document cards with field detail rows
- 3-way match table
- Review banner if review_required: true
- Data: GET /v1/jobs/:id/result

STEP 5: src/routes/review-queue/ReviewQueueList.tsx
- Oldest-first sort, reason filter
- Data: GET /v1/review-queue with pagination
- Empty: 'All clear — no items need review.'

STEP 6: src/routes/review-queue/ReviewItemDetail.tsx
- Two-pane: PDF viewer (left) + editable fields (right)
- Inline edit on pencil click
- Three actions: Approve, Correct, Escalate
- Data: GET /v1/documents/:id/pdf (signed URL), POST /v1/review-queue/:id/resolve

STEP 7: src/routes/analytics/Analytics.tsx
- Recharts: volume trends, accuracy metrics, processing time, LLM usage
- Data: GET /v1/analytics/usage?period=30d
- Empty: 'No data yet — analytics populate after your first completed job.'

STEP 8: src/routes/settings/ApiKeys.tsx
- List with masked keys, create (show once), revoke
- Data: GET/POST/DELETE /v1/api-keys

STEP 9: src/routes/settings/Webhooks.tsx
- Config form + test button
- Data: GET/PUT /v1/settings/webhook

STEP 10: SELF-REVIEW (mandatory):
- Verify all error codes match FRONTEND.md section 9 exactly
- Verify all empty states match FRONTEND.md section 9
- Verify polling backoff matches FRONTEND.md section 6
- Verify no gradients, no shadows, no emoji, no confetti
- Report: files changed, page count, any issues

Do NOT modify components (already complete from Phase 6).
Do NOT add new npm dependencies.
" 2>&1 | tee /tmp/midas-phase7.log
