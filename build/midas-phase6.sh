#!/bin/bash
cd /home/santhosh/projects/freight-doc-normalizer/frontend

opencode run --agent default --model opencode-go/mimo-v2.5-pro "
PHASE 6: Design System + All Components + API Client

You are working on FreightPipe, a freight document review dashboard.
Read /home/santhosh/projects/freight-doc-normalizer/FRONTEND.md for the full design spec.
Read /home/santhosh/projects/freight-doc-normalizer/BACKEND.md for the API contract.

STEP 1: Fix the design tokens.
Update src/styles/tokens.css with ALL tokens from FRONTEND.md section 1.2:
- --bg-base: #0E1013
- --surface: #16191D
- --surface-raised: #1D2126
- --border: #2A2F36
- --text-primary: #E8EAED
- --text-secondary: #9AA1AC
- --text-tertiary: #5C636E
- --accent: #4A7CFF
- --confidence-high: #3FB68B
- --confidence-mid: #D9A441
- --confidence-low: #E55A4E
- --discrepancy: #E55A4E
Spacing: 4/8/12/16/24/32/48px base-8 system.

STEP 2: Fix global styles.
Update src/styles/global.css:
- Import Inter (400/500/600) and JetBrains Mono (400) from @fontsource
- 13px base UI text, 12px monospace data
- Dark theme (bg-base background, text-primary color)
- Confidence rail base: 3px left border on rail elements

STEP 3: Fix TypeScript types.
Update src/types/backend.ts to match BACKEND.md section 3.1 EXACTLY:
- JobStatus enum: queued | classifying | splitting | extracting | normalizing | validating | matching | scoring | needs_review | complete | failed | needs_llm_capacity (12 values, NOT 5)
- DocType enum: rate_con | bol | pod | invoice | unknown (5 values)
- DiscrepancyFlag enum: none | rate_delta | missing_accessorial | extra_accessorial | weight_variance | pieces_variance (6 values)
- ReviewReason enum: low_confidence | discrepancy | classification_failed | needs_llm_capacity | validation_failed (5 values)
- ReviewState enum: pending | in_review | resolved | escalated (4 values)
- Full interfaces for: Job, Document, ExtractedField, MatchResult, ReviewQueueItem, Account, ApiKey
- API response types: JobListResponse, JobResultResponse, ReviewQueueListResponse, AnalyticsUsageResponse, ApiKeyCreateResponse

STEP 4: Build ALL 12 components fully (not stubs).
Each component needs: TypeScript props interface, CSS Module, all visual states.
Use the CONFIDENCE_THRESHOLDS constant from src/config/confidence.ts (document: 0.80, field: 0.70).

1. ConfidenceBadge - green/amber/red by threshold, numeric + text label, aria-label
2. DiscrepancyFlag - all 6 enum values, red rail for non-none
3. DocTypeIndicator - text labels for all 5 types
4. JobStatusPill - all 12 values, collapses 7 mid-pipeline to Processing with stage subtext
5. ConfidenceRail - 3px left-edge bar, color by state (green/amber/red/blue/gray)
6. ReviewQueueCard - reason, age, jobId, docType
7. FieldDetailRow - monospace value, confidence badge, extraction method tag
8. MatchResultRow - 5 columns + discrepancy flag
9. UploadZone - drag-drop, 25MB limit, PDF only, 5 states (idle/dragover/file-selected/uploading/error)
10. WebhookStatusIndicator - 3 states
11. ApiKeyCard - masked key, create/revoke
12. PdfViewerWithOverlay - react-pdf wrapper with bbox highlight support

STEP 5: Complete API client layer.
- src/api/client.ts: fetch wrapper with X-Api-Key header injection, error handling, base URL from env
- src/api/jobs.ts: POST /documents, GET /jobs, GET /jobs/{id}, GET /jobs/{id}/result
- src/api/reviewQueue.ts: GET /review-queue, POST /review-queue/{id}/resolve
- src/api/settings.ts: GET/POST /api-keys, DELETE /api-keys/{id}, GET/PUT /settings/webhook
- src/api/analytics.ts: GET /analytics/usage
- src/api/webhooks.ts: POST /webhooks/test

STEP 6: SELF-REVIEW (mandatory):
- Verify ALL enums match BACKEND.md section 3.1 exactly (grep for each enum value)
- Verify ALL thresholds use CONFIDENCE_THRESHOLDS constant, not hardcoded numbers
- Check WCAG: color never the only indicator, aria-labels on all interactive elements
- Verify: no gradients, no box-shadows, no emoji in status, no rounded-everything
- Report: files changed, component count, any issues

Do NOT touch package.json or add new dependencies.
Do NOT create route page implementations yet (stubs are fine for routes).
Focus ONLY on design system, components, API client, and types.
" 2>&1 | tee /tmp/midas-phase6.log
