# Midas Context — FreightPipe Frontend Phase 6

## Project
FreightPipe — freight document review dashboard.
Repo: /home/santhosh/projects/freight-doc-normalizer/frontend/
Design truth: /home/santhosh/projects/freight-doc-normalizer/FRONTEND.md
Backend API: /home/santhosh/projects/freight-doc-normalizer/BACKEND.md

## Your task: Phase 6 from CODING_PLAN.md

### F6.1 Design tokens + global styles
- tokens.css: all colours from FRONTEND.md §1.2, spacing §1.4 (8px base: 4/8/12/16/24/32/48)
- global.css: Inter font (UI), JetBrains Mono (data), 13px base, dark theme
- Confidence rail CSS: 3px left-edge vertical bar (the signature element)

### F6.2 Core components (FRONTEND.md §4)
Build ALL of these with proper TypeScript interfaces, CSS Modules, and all visual states:

1. **ConfidenceBadge** — green (≥threshold), amber (≥threshold-0.10), red (below). Always shows numeric + text label. WCAG aria-label.
2. **DiscrepancyFlag** — enum: none|rate_delta|missing_accessorial|extra_accessorial|weight_variance|pieces_variance. Red rail for non-none.
3. **DocTypeIndicator** — text labels: "Rate Confirmation", "Bill of Lading", "Proof of Delivery", "Carrier Invoice", "Unclassified"
4. **JobStatusPill** — full enum from BACKEND.md §3.1. Collapses 7 mid-pipeline stages to "Processing" with stage name subtext.
5. **ConfidenceRail** — 3px left-edge bar. Green/amber/red/blue/gray by state.
6. **ReviewQueueCard** — reason, age, jobId, docType
7. **FieldDetailRow** — fieldName, value (monospace), confidence, sourcePage, extractionMethod tag
8. **MatchResultRow** — lineItem, rateConValue, bolPodValue, invoiceValue, discrepancyFlag, discrepancyAmount
9. **UploadZone** — drag-drop, 25MB limit, PDF only. States: idle/dragover/file-selected/uploading/error
10. **WebhookStatusIndicator** — delivered/pending/webhook_delivery_failed
11. **ApiKeyCard** — label, maskedKey, createdAt, revokedAt
12. **PdfViewerWithOverlay** — react-pdf + bbox highlight overlay

### F6.3 Key constants
```ts
// config/confidence.ts
export const CONFIDENCE_THRESHOLDS = {
  document: 0.80,
  field: 0.70,
} as const;
```

### F6.4 Types (types/backend.ts)
Mirror BACKEND.md §3.1 exactly:
- JobStatus enum (12 values)
- DocType enum (5 values)
- DiscrepancyFlag enum (6 values)
- ReviewReason enum (5 values)
- All API response shapes

## Self-review requirement
After building each component:
1. Verify all enums match BACKEND.md §3.1 exactly
2. Verify all thresholds use CONFIDENCE_THRESHOLDS constant (not hardcoded)
3. Verify WCAG: color never the only indicator, aria-labels present
4. Visual review: no gradients, no shadows, no emoji, no generic SaaS aesthetics

## Design philosophy (from FRONTEND.md §1)
- Dark base (#0E1013) — not for trend, but because operators review light-background scanned docs against dark chrome
- Monospace for all extracted values (JetBrains Mono) — character-level verification
- Confidence rail is the signature element — 3px left-edge bar at every scale
- No gradients, no card shadows, no rounded-everything, no emoji status, no confetti
- Status through color + typography + precise language, never decoration
