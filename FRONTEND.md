# FRONTEND.md — FreightPipe Review Dashboard

**Status:** Design document — no production code. Frontend only.
**Authoritative specs:** `PROJECT.md` (free-tier constraint), `BACKEND.md` (API contract, data model, status enums — this document is contractually synced to it, not independently designed).
**Owner inputs locked from Phase 1:** solo-first/team-ready, review workflow is primary daily activity, balanced information density, desktop-primary/tablet-occasional, all MVP screens in scope, no generic-SaaS visual tropes, Vercel referenced as a loose tonal cue only, deployment framework left to this document's judgment, correction workflow resolved as inline-first with modal escape hatch.

---

## Executive Summary

FreightPipe's frontend is a **review-and-monitor dashboard** for a document normalization pipeline that runs almost entirely async and mostly correctly — meaning the UI's real job isn't "look impressive," it's make the ~15–30% of jobs that need a human fast and unambiguous to resolve, while staying honest about the other 70–85% that just need a status glance. It's built as a static React SPA (Vite) deployed to Cloudflare Pages, talking directly to the Cloudflare Worker API — no BFF, since API-key auth happens server-side per account and the frontend never needs to hold provider secrets. Every confidence threshold, status enum, and error code in this document is pulled from `BACKEND.md` verbatim, and the one point where `BACKEND.md` itself says its numbers are provisional (the 0.80/0.70 confidence thresholds, §5.7/§12) is treated as provisional here too — implemented as a single named constant, not hardcoded into every badge. The visual identity avoids the SaaS-dashboard genre entirely: no gradients, no cards floating on shadows, no rounded-everything — instead a flat, structured, monospace-inflected layout that reads like an instrument panel for a pipeline, because that's what it is.

---

## 1. Design Philosophy & Brand Identity

### 1.1 What FreightPipe is not
It is not a "platform." It is not "AI-powered logistics intelligence." It is a tool that turns messy PDFs into checked JSON and tells you exactly which parts it isn't sure about. The design has to earn trust the way a good TMS earns trust — through precision and legibility, not through polish that implies more than the product does.

### 1.2 Color palette

| Token | Hex | Use |
|---|---|---|
| `--bg-base` | `#0E1013` | App background — near-black, not pure black (pure black + white text causes halation on most monitors at long reading sessions, which matters for a review-queue-heavy tool) |
| `--surface` | `#16191D` | Panel/card backgrounds |
| `--surface-raised` | `#1D2126` | Modal, active row, hover state |
| `--border` | `#2A2F36` | Hairline dividers — no shadows anywhere, borders do all the separation work |
| `--text-primary` | `#E8EAED` | Primary text |
| `--text-secondary` | `#9AA1AC` | Labels, metadata, timestamps |
| `--text-tertiary` | `#5C636E` | Disabled, placeholder |
| `--accent` | `#4A7CFF` | Primary action, links, focus ring — a cool, restrained blue, not a "startup purple" |
| `--confidence-high` | `#3FB68B` | Confidence ≥ high threshold — green desaturated enough to read as "fine," not "celebrate" |
| `--confidence-mid` | `#D9A441` | Amber — mid-confidence band |
| `--confidence-low` | `#E55A4E` | Red — below field threshold |
| `--discrepancy` | `#E55A4E` | Match discrepancy flag — intentionally same red family as low-confidence, since both mean "a human should look here" |

**Rationale:** Dark base isn't a default-for-default's-sake choice (the Hard Rules explicitly forbid that) — it's chosen because this is a screen operators stare at for review sessions, often against scanned/OCR'd document images that are themselves light-background, so a dark chrome around a light document reduces eye strain the way a photo editor's dark UI does around bright images. This is a testable assumption, not a certainty; if user testing says otherwise, flip it — the palette is expressed as tokens specifically so that's a variable change, not a redesign.

### 1.3 Typography

- **UI text:** `Inter` (Google Fonts, self-hosted via `@fontsource` to stay free-tier and avoid a Google Fonts CDN dependency at runtime) — chosen for its tall x-height and disambiguated characters (1/l/I, 0/O) which matters directly for a tool where someone is visually cross-checking extracted alphanumeric IDs like load numbers against a source document.
- **Data/monospace:** `JetBrains Mono` — used specifically for: load numbers, BOL numbers, invoice numbers, money amounts, dates, confidence scores, API keys. Anything that's an *exact value being verified* gets monospace so character-level differences (is that a 0 or an O, an I or a 1) are visually obvious. This is the signature typographic decision — most B2B dashboards use one font for everything; FreightPipe visually distinguishes "prose the UI is telling you" from "data extracted from a document," which is the actual cognitive task the reviewer is doing.
- **Scale:** 13px base UI text (dense-adjacent per the balanced-density brief), 12px monospace data, 20px section headers, 15px for anything a reviewer reads under time pressure (review reasons, error messages).

### 1.4 Spacing system
8px base unit. `4 / 8 / 12 / 16 / 24 / 32 / 48`. No arbitrary values. Balanced density means: comfortable row height (40px in tables, not 28px terminal-dense, not 56px spacious-SaaS), but information-per-screen prioritized over whitespace-as-decoration.

### 1.5 The signature visual element
**The confidence rail.** Every field row, document card, and job row carries a 3px left-edge vertical bar colored by its confidence/status state (green/amber/red, or blue for in-progress, gray for queued). It's not a badge you have to read — it's a peripheral-vision signal, so a reviewer scanning a list of 40 review-queue items can triage by color before reading a single word. This single element recurs at every scale (job list row, document card, field row) and is the thing that makes a FreightPipe screenshot recognizable at a glance — no other freight or document-AI dashboard uses a consistent edge-rail system across all three list levels simultaneously.

### 1.6 What makes this not a template
No gradient hero, no card-with-shadow-on-white, no rounded-corner pill buttons, no emoji anywhere in status language, no illustrated empty states with little characters. Status is communicated through the confidence rail, monospace/sans distinction, and precise copy — never through decoration.

---

## 2. Information Architecture

### 2.1 Navigation structure (solo-first, team-ready)

```
┌─ FreightPipe ────────────────────────────────────┐
│  ● Jobs        (default landing)                  │
│  ● Review Queue  [12]  ← live count badge          │
│  ● Analytics    (nice-to-have, see §7)             │
│  ● Settings                                         │
│    ├─ API Keys                                      │
│    └─ Webhooks                                       │
└──────────────────────────────────────────────────┘
```

Flat, 4-item primary nav. No team/assignment nav items in v1 — but the route structure reserves `/review-queue/:id` (not `/my-review-queue/:id`) and the review item data model carries `assigned_to` from day one (already in `BACKEND.md`'s `review_queue` table), so adding a team filter later is a query-param addition, not a re-architecture.

### 2.2 Screen inventory

| Screen | Route | MVP status |
|---|---|---|
| Job list | `/jobs` | Essential |
| Job submission | `/jobs/new` | Essential |
| Job detail / status | `/jobs/:id` | Essential |
| Job result view | `/jobs/:id/result` | Essential |
| Review queue list | `/review-queue` | Essential |
| Review item detail | `/review-queue/:id` | Essential |
| Analytics dashboard | `/analytics` | Included per owner (all-in-scope) |
| Settings — API keys | `/settings/api-keys` | Included per owner |
| Settings — Webhooks | `/settings/webhooks` | Included per owner |

Owner selected "all" for MVP scope (Q6) — both the originally-essential and originally-nice-to-have screens ship in v1. This is noted as a scope decision with a cost: Analytics (§7) depends on `provider_usage_log` and aggregate queries `BACKEND.md` doesn't yet expose a dedicated endpoint for (see §12 Sync Contract — flagged gap).

### 2.3 User flow — submission to resolution (ASCII)

```
 [Jobs list]
      │
      ├─ "Submit document" ──► [Job submission] ──► POST /v1/documents
      │                              │                       │
      │                              ▼                       ▼
      │                        202 Accepted            job_id, status: queued
      │                              │
      │                              ▼
      │                     [Job detail — polling]
      │                              │
      │              ┌───────────────┼────────────────┐
      │              ▼               ▼                ▼
      │         status:         status:           status:
      │         complete      needs_review          failed
      │              │               │                │
      │              ▼               ▼                ▼
      │      [Result view]   [Review queue item]  [Error detail +
      │                              │              retry/support]
      │                              ▼
      │                    inline correct / approve
      │                    POST /review-queue/{id}/resolve
      │                              │
      │                              ▼
      │                     job.status → complete
      │                              │
      │                              ▼
      │                       [Result view]
      ▼
 [Review Queue list] ◄── independent entry point, doesn't require
                          navigating through a specific job first
```

### 2.4 Async job model → UI state mapping

| `BACKEND.md` `jobs.status` | UI treatment |
|---|---|
| `queued` | Gray rail, "Queued" pill, spinner-free (avoid implying imminent action on a possibly-cold Koyeb instance — see §6) |
| `classifying` / `splitting` / `extracting` / `normalizing` / `validating` / `matching` / `scoring` | Blue rail, single collapsed "Processing" pill with a subtext showing the specific stage in monospace-adjacent small text — not 7 separate visual states, since a reviewer doesn't act differently across these, they just wait |
| `needs_review` | Amber rail, "Needs Review" pill, links directly to `/review-queue/:id` for that job |
| `complete` | Green rail, "Complete" pill, links to result view |
| `failed` | Red rail, "Failed" pill, shows `error.message` from the error envelope |
| `needs_llm_capacity` | Amber-orange distinct pill, "Capacity Limited" — explicitly NOT styled identically to `failed`, since this is a temporary systemic condition, not a document problem (see §9 empty/error states) |

---

## 3. Screen-by-Screen Designs

### 3.1 Job List (`/jobs`)

**Purpose:** At-a-glance status of all submitted jobs, sorted by recency, filterable by status.

```
┌─────────────────────────────────────────────────────────────────────┐
│ FreightPipe    Jobs   Review Queue [12]   Analytics   Settings        │
├─────────────────────────────────────────────────────────────────────┤
│  Jobs                                          [+ Submit document]    │
│                                                                         │
│  Filter: [All ▾] [Queued] [Processing] [Needs Review] [Complete] [Failed]│
│                                                                         │
│ ┃ Job                Docs   Status          Submitted        ⋯        │
│ ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫│
│ ┃ RC-48213 shipment   4      ● Complete       2 min ago               │
│ ┃ (green rail)                                                         │
│ ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫│
│ ┃ job_a91f...         3      ● Needs Review   14 min ago    [Review]  │
│ ┃ (amber rail)          discrepancy: extra_accessorial                │
│ ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫│
│ ┃ job_7c2e...         —      ● Processing     1 min ago               │
│ ┃ (blue rail)            extracting                                   │
│ ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫│
│ ┃ job_1d90...         —      ● Capacity Limited  1 hr ago              │
│ ┃ (amber-orange rail)                                                  │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛│
└─────────────────────────────────────────────────────────────────────┘
```

**Component inventory:** Job status pill, confidence/status rail, filter tab bar, job row (clickable → job detail), submit-document button (primary action).

**Data bindings:**
- List source: repeated `GET /v1/jobs/{id}` is wrong at scale — this screen requires a list endpoint `BACKEND.md` does not currently define (`GET /v1/jobs` with pagination). **Flagged as a backend gap in §12.** Until it exists, the frontend spec assumes it will follow the same cursor pattern as `GET /v1/review-queue`.
- `status` → status pill + rail color (§2.4 mapping)
- `documents[].length` → "Docs" column
- `created_at` → relative time, recomputed client-side every 30s, not polled
- `review_reasons[0]` (from a joined/expanded job-with-reason view, itself a gap — see §12) → subtext under Needs Review rows

**State variations:**
- Loading: skeleton rows (flat gray blocks matching row height, no shimmer animation — reduced-motion by default per §8)
- Empty: see §9
- Error (list fetch fails): inline banner above the table, retry button, table area shows last-known-good cached list grayed out if available

**Responsive:** Desktop-primary. At tablet width (`768–1024px`), the "Docs" and "⋯" columns collapse into an expandable row; the confidence rail and status pill remain, since those are the load-bearing signal.

### 3.2 Job Submission (`/jobs/new`)

**Purpose:** Upload a PDF and optionally configure a webhook for this submission.

```
┌─────────────────────────────────────────────────────────────────────┐
│  ← Jobs      Submit Document                                          │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │              Drop a PDF here, or click to browse                 │  │
│  │                                                                   │  │
│  │              Max 25MB · rate confirmations, BOLs,                │  │
│  │              PODs, invoices — merged files OK                    │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  Webhook URL (optional)   [________________________]  [Test]          │
│                                                                         │
│  Idempotency key (optional, advanced)  [________________]              │
│                                                                         │
│                                                    [Submit Document]    │
└─────────────────────────────────────────────────────────────────────┘
```

**Component inventory:** Upload zone (drag-and-drop), webhook URL field + inline test button, idempotency-key field (collapsed under "advanced" by default — most solo users won't need it), submit button.

**Data bindings:**
- Submit → `POST /v1/documents`, `multipart/form-data`, fields `file`, `webhook_url` (optional), header `Idempotency-Key` (optional)
- Webhook test button → `POST /v1/webhooks/test`, shows `{"delivered": true/false}` inline next to the field, not a separate modal
- On `202` → redirect to `/jobs/:job_id` (using returned `job_id`)
- On `400 invalid_pdf` / `413 file_too_large` → inline error under the upload zone, file not cleared from view so the user can see what they tried
- On `429 rate_limited` → inline error with `Retry-After` countdown (§9)

**States:** Idle (empty dropzone) / file-selected-pre-submit (shows filename, size, a "×" to clear) / submitting (button shows inline spinner, dropzone locked) / error (per code above).

**Responsive:** Full-width dropzone scales down; on tablet, dropzone height reduces from 240px to 160px.

### 3.3 Job Detail / Status (`/jobs/:id`)

**Purpose:** Live status of one job while it's in flight; redirects to result view once terminal.

```
┌─────────────────────────────────────────────────────────────────────┐
│  ← Jobs      Job job_7c2e91a4                    ● Processing          │
│                                                                         │
│  ┃ Stage: extracting                                                   │
│  ┃ Submitted 1 min ago                                                 │
│  ┃                                                                     │
│  ┃ queued → classifying → splitting → [extracting] → normalizing →     │
│  ┃          validating → matching → scoring → complete                 │
│  ┃                                                                     │
│  ┃ If this is a cold-start pickup, initial polling may take longer    │
│  ┃ than usual — this is expected, not an error.                        │
│                                                                         │
│  Documents detected so far: 2                                          │
│    • rate_con  (pages 1)                                                │
│    • bol       (pages 2–3)                                              │
└─────────────────────────────────────────────────────────────────────┘
```

**Component inventory:** Job status pill, stage progress track (horizontal, current stage highlighted), documents-detected list (populates incrementally as `documents[]` rows are created — optional enhancement, MVP can show it only once available), cold-start advisory copy (see rationale below).

**Data bindings:**
- `GET /v1/jobs/{id}` polled per §6 backoff schedule
- `status` → pill + progress track position
- `documents[]` → detected-documents list

**Cold-start advisory is a deliberate design decision, not filler copy:** `BACKEND.md` §12 explicitly flags that Koyeb's scale-to-zero-after-1h means client-visible latency will sometimes be materially worse than an "always-on" assumption implies. Silently showing a spinner with no explanation, when a job might sit in `queued` for 30–60s before a cold Koyeb instance picks it up, reads as broken. One honest sentence prevents a support ticket.

**States:** In-progress (as above) / redirect-on-complete (auto-navigates to `/jobs/:id/result` when status becomes `complete` or `needs_review`, no manual click required) / failed (shows error envelope inline, see §9).

### 3.4 Job Result View (`/jobs/:id/result`)

**Purpose:** The full structured output — extracted fields per document, plus 3-way match results.

```
┌─────────────────────────────────────────────────────────────────────┐
│  ← Jobs      Result: job_a91f...                    ● Complete         │
│                                                                         │
│  Documents (2)                                                          │
│  ┌─────────────────────────────┐ ┌─────────────────────────────┐      │
│  │ ┃ rate_con        conf 0.95  │ │ ┃ invoice         conf 0.88  │      │
│  │ ┃ page 1                     │ │ ┃ pages 2-3                  │      │
│  │ ┃ [Expand fields ▾]          │ │ ┃ [Expand fields ▾]          │      │
│  └─────────────────────────────┘ └─────────────────────────────┘      │
│                                                                         │
│  ▾ rate_con — field detail                                              │
│  ┃ load_number       RC-48213         conf 0.97   rule                 │
│  ┃ linehaul_rate     $1,850.00 USD    conf 0.94   rule                 │
│  ┃ fuel_surcharge    —                                                  │
│                                                                         │
│  3-Way Match                                                            │
│  ┃ Line item     Rate Con      BOL/POD      Invoice      Flag           │
│  ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫│
│  ┃ linehaul      $1,850.00     —            $1,850.00    ● none         │
│  ┃ detention     —             —            $150.00      ● extra_accessorial (+$150.00)│
└─────────────────────────────────────────────────────────────────────┘
```

**Component inventory:** Document type indicator card (per doc), field extraction detail row, 3-way match result row, confidence badge, discrepancy flag indicator, source bbox highlight trigger (clicking a field row highlights that region — see below).

**Data bindings:** `GET /v1/jobs/{id}/result` — every field maps exactly:
- `documents[].doc_type` → document card label
- `documents[].document_confidence` → card confidence badge (threshold: `CONFIDENCE_THRESHOLDS.document`, §4)
- `documents[].fields.{name}.value / .confidence / .source.page / .source.bbox` → field detail row; clicking a row would, in a v2 with PDF viewer, scroll/highlight `bbox` on that `page` (MVP: field row shows "page N" as text only, since embedding a PDF viewer + bbox overlay on the result view — as opposed to the review view where it's essential — is scoped as v2)
- `match_results[].line_item / .rate_con_value / .bol_pod_value / .invoice_value / .discrepancy_flag / .discrepancy_amount` → match table row exactly
- `review_required` + `review_reasons[]` → if true, a banner at top links to the review queue item instead of showing this as a terminal "done" screen

**States:** Populated (above) / a job that is `complete` with `review_required: false` (no match table discrepancy rows shown, just "No discrepancies found" — never an empty table with no message) / a job with `needs_review: true` redirects here only after resolution — while `needs_review`, this route instead shows a banner + link to `/review-queue/:id`.

### 3.5 Review Queue List (`/review-queue`)

**Purpose:** The primary daily-use screen per owner's answer to Q3 — sorted for fastest triage.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Review Queue (12 pending)                                             │
│                                                                         │
│  Sort: [Oldest first ▾]   Filter: [All reasons ▾]                      │
│                                                                         │
│ ┃ Job              Reason                    Age        ⋯              │
│ ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫│
│ ┃ job_a91f...       discrepancy: extra_accessorial   14 min           │
│ ┃ (red rail)                                                           │
│ ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫│
│ ┃ job_b02c...       low_confidence (field: pickup_date)  2 hr          │
│ ┃ (amber rail)                                                         │
│ ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫│
│ ┃ job_c31d...       classification_failed              5 hr            │
│ ┃ (red rail)                                                           │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛│
└─────────────────────────────────────────────────────────────────────┘
```

**Sort/prioritization rationale:** Default sort is oldest-first (age-based FIFO), not confidence-based — a `pending` item that's sat 5 hours is a bigger operational problem than a fresh 2-minute-old one regardless of how low its confidence is. Reason filter uses `BACKEND.md`'s exact `review_queue.reason` enum: `low_confidence | discrepancy | classification_failed | needs_llm_capacity | validation_failed`.

**Data bindings:** `GET /v1/review-queue?state=pending&limit=50&cursor=...` — `items[]` → row list, `next_cursor` → pagination.

**States:** Populated / empty (§9, "All clear") / loading (skeleton rows, same pattern as job list).

### 3.6 Review Item Detail (`/review-queue/:id`)

**Purpose:** The core human-in-the-loop screen — resolve a flagged item.

```
┌─────────────────────────────────────────────────────────────────────┐
│  ← Review Queue      job_a91f... — rate_con                            │
│                                                                         │
│  ┌───────────────────────────┐  ┌───────────────────────────────┐   │
│  │                             │  │ Extracted fields                 │   │
│  │   [PDF page render,         │  │                                    │   │
│  │    bbox highlight overlay   │  │ ┃ load_number     RC-48213  0.97   │   │
│  │    on hovered/active field] │  │ ┃ linehaul_rate   $1,850.00 0.94   │   │
│  │                             │  │ ┃ detention       [click to edit ✎]│   │
│  │                             │  │   ↳ inline input appears here       │   │
│  │                             │  │                                    │   │
│  └───────────────────────────┘  └───────────────────────────────┘   │
│                                                                         │
│  Review reason: discrepancy: extra_accessorial on detention (+$150.00) │
│                                                                         │
│  Notes (optional)  [___________________________________]              │
│                                                                         │
│         [Escalate]              [Approve as-is]    [Save corrections]  │
└─────────────────────────────────────────────────────────────────────┘
```

**Component inventory:** PDF/image viewer with bbox overlay (left pane), field extraction detail rows with inline-edit affordance (right pane), notes field, three resolution actions.

**Correction workflow (resolving Q10):** Clicking the pencil icon on a field row turns that row's value into an inline text input, right there in the list — no modal for the common case (fixing a misread number). If a correction is structurally complex (e.g., editing a nested `accessorials[]` array entry, or a `shipper`/`consignee` object with multiple sub-fields), the same click instead opens a **focused edit panel that slides in from the right without leaving the screen** — not a full modal that obscures the PDF, since the PDF-vs-data comparison is the entire point of this screen and should never be interrupted. This satisfies "inline for quick fixes, modal-equivalent for complex ones" without ever hiding the source document.

**Data bindings:**
- Left pane: original PDF fetched via `GET /v1/documents/{document_id}/pdf` (returns binary PDF data directly from Postgres)
- Right pane: same `fields` structure as the result view, `source.bbox` drives the overlay highlight, synced to hover/focus state on the corresponding row
- Approve → `POST /v1/review-queue/{id}/resolve` with `{"resolution": "approved"}`
- Correct → same endpoint, `{"resolution": "corrected", "corrected_fields": {...}, "notes": "..."}`
- Escalate → per `BACKEND.md` §5.8's state machine, escalation is a manual-intervention path outside the API's normal resolve flow; UI sends `{"resolution": "corrected"}` is wrong here — **flagged gap**: the resolve endpoint's request schema only documents `approved`/`corrected`, not an `escalated` resolution value, but §5.8's state diagram shows `in_review → escalated` as a valid transition. This needs a backend decision (§12) before the Escalate button can be wired.

**States:** Loading (PDF + fields both loading, PDF pane shows a placeholder frame, field pane shows skeleton rows) / populated / submitting-resolution (buttons disabled, inline spinner on the clicked action) / resolution error (inline banner, item stays open, nothing lost).

**Responsive:** At tablet width, the two-pane layout stacks vertically (PDF on top, fields below) rather than side-by-side — noted as a real usability compromise since the point of this screen is side-by-side comparison; if tablet review turns out to be more than "occasional" in practice, this should be revisited (see §9, the owner's answer to Q5 was hedged as "a/b").

### 3.7 Analytics Dashboard (`/analytics`)

See §7 for full detail — included per owner's "all" answer to Q6, with the backend-gap caveat noted there.

### 3.8 Settings — API Keys (`/settings/api-keys`)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Settings › API Keys                              [+ New API Key]      │
│                                                                         │
│ ┃ Label            Key (masked)          Created      ⋯                │
│ ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫│
│ ┃ Production        fp_live_••••8a2c       Aug 1, 2026  [Revoke]        │
│ ┃ Test/staging       fp_live_••••3f91       Jul 12, 2026 [Revoke]       │
└─────────────────────────────────────────────────────────────────────┘
```

New-key creation shows the raw key **exactly once** in a copy-to-clipboard field with an explicit "this won't be shown again" warning — matches `BACKEND.md`'s `key_hash`-only storage model (§3.1: raw key shown once at creation, never retrievable after).

### 3.9 Settings — Webhooks (`/settings/webhooks`)

Per-account webhook URL configuration (currently modeled per-job in `BACKEND.md`'s `POST /v1/documents` request, with `webhook_url` optional per submission — **flagged gap**: there's no account-level default-webhook endpoint documented, so this settings screen either needs that backend capability added, or needs to be reduced to "test an arbitrary webhook URL" utility only, with the per-job field remaining the actual configuration mechanism. See §12.)

---

## 4. Component Library Specification

All thresholds and enums below are pulled verbatim from `BACKEND.md`. Confidence thresholds are implemented as a single exported constant, not inlined:

```ts
// config/confidence.ts
// SOURCE: BACKEND.md §5.7 — explicitly flagged there as "starting points to be
// tuned against the eval harness in §9, never presented to the client as fixed
// truth." Do not inline these numbers anywhere else in the codebase.
export const CONFIDENCE_THRESHOLDS = {
  document: 0.80,
  field: 0.70,
} as const;
```

### 4.1 Confidence badge
- **Props:** `value: number`, `scope: 'document' | 'field'`
- **Visual states:** green (`value >= CONFIDENCE_THRESHOLDS[scope]`), amber (`value >= CONFIDENCE_THRESHOLDS[scope] - 0.10`), red (below that)
- **Always renders numeric value + text label** ("0.94 · High"), never color alone (WCAG, §8)
- **Accessibility:** `aria-label="Confidence: 94 percent, high"`

### 4.2 Discrepancy flag indicator
- **Props:** `flag: 'none' | 'rate_delta' | 'missing_accessorial' | 'extra_accessorial' | 'weight_variance' | 'pieces_variance'`, `amount?: number`
- Enum values synced exactly to `BACKEND.md` §3.1 `match_results.discrepancy_flag`
- `none` renders as a quiet gray dot + "No discrepancy," everything else renders red rail + flag name in plain English + amount if present

### 4.3 Document type indicator
- **Props:** `docType: 'rate_con' | 'bol' | 'pod' | 'invoice' | 'unknown'`
- Text label, not icon-only (rejects "generic SaaS" iconography per Hard Rules) — e.g. "Rate Confirmation," "Bill of Lading," "Proof of Delivery," "Carrier Invoice," "Unclassified"

### 4.4 Job status pill
- **Props:** `status` — full enum from `BACKEND.md` §3.1 `jobs.status`: `queued | classifying | splitting | extracting | normalizing | validating | matching | scoring | needs_review | complete | failed | needs_llm_capacity`
- Collapses the 7 mid-pipeline stages into one "Processing" visual state with stage name as subtext (§2.4) — full enum still used internally for the stage-track component (§3.3)

### 4.5 Review queue item card
- **Props:** `reason`, `age`, `jobId`, `docType`
- Used in §3.5's list — reason enum synced to `review_queue.reason`

### 4.6 Field extraction detail row
- **Props:** `fieldName`, `value`, `confidence`, `sourcePage`, `sourceBbox`, `extractionMethod: 'rule' | 'llm_text' | 'llm_vision' | 'ocr'`
- Extraction method shown as a small text tag — surfacing this matters because `BACKEND.md` §6.4 explicitly designs rule-extracted fields as more auditable/trustworthy than LLM-extracted ones; a reviewer should be able to see at a glance which fields came from the cheap deterministic path vs. the fuzzy LLM path, since that's a real signal about how much scrutiny a field deserves even within the same confidence band

### 4.7 3-way match result row
- **Props:** `lineItem`, `rateConValue`, `bolPodValue`, `invoiceValue`, `discrepancyFlag`, `discrepancyAmount`

### 4.8 Upload zone
- **Props:** `maxSizeMb: 25` (from `BACKEND.md` §4.1), `accept: 'application/pdf'`
- States: idle, dragover, file-selected, uploading, error

### 4.9 Webhook status indicator
- **Props:** `status: 'delivered' | 'pending' | 'webhook_delivery_failed'` (per `BACKEND.md` §4.2's retry schedule and terminal failure state)

### 4.10 API key management card
- **Props:** `label`, `maskedKey`, `createdAt`, `revokedAt?`

---

## 5. Review Workflow UX

### 5.1 Queue ordering
Oldest-first by default (§3.5 rationale). Filterable by `reason`. No auto-refresh polling on the list screen itself (would cause items to jump around mid-triage) — a manual refresh affordance instead, plus the nav badge count updates independently.

### 5.2 Review detail view
Covered fully in §3.6 — PDF+overlay left, editable fields right, never modal-obscured.

### 5.3 Resolution flow
State machine per `BACKEND.md` §5.8:
```
pending → in_review → resolved
              │
              └──→ escalated → resolved
```
UI implication: opening a review item detail screen should transition `pending → in_review` (claims it), which the frontend accomplishes by calling resolve only on submit — **flagged gap**: `BACKEND.md` doesn't define a distinct "claim" endpoint, only the terminal `resolve` call. For solo use this doesn't matter (no contention), but for the team-ready structure (§2.1), a claim/lock mechanism will be needed before multi-reviewer use is safe (two people correcting the same item simultaneously). Noted for backend follow-up, not solved here.

### 5.4 Corrections write-back
`POST /v1/review-queue/{item_id}/resolve` with `corrected_fields` — the frontend sends only the fields that were actually touched, not the full field set, to keep the diff auditable and the payload minimal.

---

## 6. Real-Time Status & Polling Strategy

Per `BACKEND.md` §4, jobs are async-only — no synchronous request/response, and Koyeb's scale-to-zero (§2.2/§12) means cold-start latency is a real, expected condition, not an edge case.

**Polling schedule** (job detail screen only; list/queue screens do not auto-poll):
- Every 2s for the first 30s
- Every 5s from 30s–2min
- Every 15s after 2min
- Stops entirely once status is terminal (`complete`, `failed`, `needs_review`) or after 30 minutes with no change (shows a "still processing — this is taking longer than usual" notice with a manual refresh button, rather than polling forever)

**Webhook/SSE:** Flagged explicitly as a v2 enhancement, not MVP, per the prompt's own instruction — polling is the only mechanism in this version.

**Status transitions the user sees:** covered in §2.4's mapping table and §3.3's stage track.

---

## 7. Data Visualization (Analytics — included per owner scope)

Owner selected "all" screens for MVP (Q6), which includes this originally-optional dashboard. Built with **Recharts** (MIT-licensed, free, already common in the free-tier React ecosystem — no paid charting library).

All charts source data from `GET /v1/analytics/usage?period=30d` (BACKEND.md §4.1):

- **Volume trends** (jobs/day, documents/day) — line chart. Data: `jobs.total`, `documents.total` over time (requires the endpoint to support a `group_by=day` parameter or the frontend to derive daily counts from the job list — enhancement note, not a blocker for the aggregate stats display).
- **Accuracy metrics** (avg confidence, review rate, correction rate) — stat cards + trend line. Data: `accuracy.avg_confidence`, `accuracy.review_rate`, `accuracy.correction_rate`.
- **Processing time distribution** — histogram. Data: `processing_time.p50_seconds`, `processing_time.p90_seconds`, `processing_time.p99_seconds`.
- **LLM usage vs. cache hit rate** — stacked bar chart. Data: `llm_usage.total_calls`, `llm_usage.cache_hit_rate`, `llm_usage.by_provider`.

**Refresh strategy:** poll on page load + manual refresh only, not continuous polling — analytics data doesn't need sub-minute freshness.

---

## 8. Accessibility & Keyboard Navigation

WCAG 2.1 AA baseline:
- **Focus management, review workflow:** Tab order in the review item detail moves through field rows top-to-bottom; pressing Enter on a focused field row opens its inline editor; Escape cancels an in-progress edit without submitting. Approve/Correct/Escalate buttons are reachable via Tab without needing to click into the PDF pane first.
- **Color is never the only indicator:** every confidence badge, status pill, and discrepancy flag carries a text label alongside its color (§4.1, §4.2).
- **Screen reader labels:** every data-heavy row (job row, field row, match row) has a composed `aria-label` summarizing its content in one sentence, not just the visual layout re-read element-by-element.
- **Reduced motion:** `prefers-reduced-motion` respected — no shimmer/skeleton animation, no transition on the confidence rail color change, polling-driven UI updates happen without animated transitions.

---

## 9. Error & Empty States

Synced to `BACKEND.md` §4.3 error codes exactly:

| Code | UI treatment |
|---|---|
| `invalid_pdf` | Under upload zone: "This file couldn't be read as a PDF. Check that it's not corrupted and try again." + re-upload prompt, file selection cleared |
| `file_too_large` | Under upload zone: "This file is 31MB — FreightPipe accepts PDFs up to 25MB. Try splitting it into separate documents." |
| `rate_limited` | Inline banner with live countdown from `Retry-After` header: "Rate limit reached. You can submit again in 0:47." |
| `llm_capacity_exhausted` | Distinct amber-orange banner (not styled as a failure): "Free-tier processing capacity is temporarily exhausted for today. This job will resume automatically, or add your own API key in Settings to bypass the limit." — links to BYOK setup |
| `job_not_found` | Full-page "This job doesn't exist or you don't have access to it." + link back to Jobs |
| `unauthorized` | Redirect to a re-auth/API-key prompt, not a generic error page |
| Empty review queue | "All clear — no items need review." Plain text, no illustration, no confetti (Hard Rules) |
| Empty job list | "No jobs yet. Submit your first document to get started." + prominent upload CTA |
| Empty analytics | "No data yet — analytics populate after your first completed job." + upload CTA |

---

## 10. Tech Stack & Build

| Choice | Rationale |
|---|---|
| **React 18 + Vite** | Static build output fits Cloudflare Pages exactly; Vite's dev server and build speed matter for a solo developer iterating fast; React chosen over Vue/Svelte because it has the deepest free-tier component ecosystem overlap with what this spec needs (Recharts, react-pdf) |
| **TypeScript** | The API contract in `BACKEND.md` is precise and typed (exact enums, exact schemas) — TS lets those enums be compile-time-checked types (`JobStatus`, `DiscrepancyFlag`, `ReviewReason`), so a frontend/backend enum drift becomes a build error, not a silent bug |
| **CSS approach: CSS Modules + custom properties (not Tailwind)** | Justified by the design, not habit: this spec defines a small, deliberate token set (§1.2–1.4) meant to be referenced consistently, not composed ad hoc per-element the way utility classes encourage — a constrained token system is easier to audit for "does this still match BACKEND.md's thresholds" than scanning JSX for inline utility classes |
| **State management: React Query (TanStack Query)** | The entire app is fundamentally "fetch/poll/mutate against a REST API" — React Query's built-in polling, caching, and mutation-with-invalidation patterns map directly onto §6's polling schedule and §5.4's resolve-then-refetch flow, without hand-rolling polling logic |
| **PDF rendering: react-pdf (pdf.js wrapper)** | Free, no server-side rendering needed, renders directly from the API-returned PDF blob (Postgres BYTEA), supports the bbox-overlay requirement in §3.6 via canvas coordinate mapping |
| **Charting: Recharts** | Free, React-native, sufficient for the line/bar/histogram needs in §7 (once backend endpoints exist) |
| **Deployment: Cloudflare Pages** | Free, static, matches `BACKEND.md` §11.1's infra map exactly; no BFF/Workers-for-frontend layer needed since API-key auth is a client-supplied header, not a secret the frontend needs to hide (the key belongs to the account holder, entered by them, same trust model as any API-key-authenticated SaaS dashboard) |

**On Q9 (deployment/framework, answered "anything"):** the above is the recommendation, chosen for fit against this specific spec's needs rather than convention.

---

## 11. File Tree

```
freightpipe-frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── routes/
│   │   ├── jobs/
│   │   │   ├── JobList.tsx
│   │   │   ├── JobSubmit.tsx
│   │   │   ├── JobDetail.tsx
│   │   │   └── JobResult.tsx
│   │   ├── review-queue/
│   │   │   ├── ReviewQueueList.tsx
│   │   │   └── ReviewItemDetail.tsx
│   │   ├── analytics/
│   │   │   └── Analytics.tsx
│   │   └── settings/
│   │       ├── ApiKeys.tsx
│   │       └── Webhooks.tsx
│   ├── components/
│   │   ├── ConfidenceBadge.tsx
│   │   ├── DiscrepancyFlag.tsx
│   │   ├── DocTypeIndicator.tsx
│   │   ├── JobStatusPill.tsx
│   │   ├── ConfidenceRail.tsx
│   │   ├── ReviewQueueCard.tsx
│   │   ├── FieldDetailRow.tsx
│   │   ├── MatchResultRow.tsx
│   │   ├── UploadZone.tsx
│   │   ├── WebhookStatusIndicator.tsx
│   │   ├── ApiKeyCard.tsx
│   │   └── PdfViewerWithOverlay.tsx
│   ├── api/
│   │   ├── client.ts              # fetch wrapper, X-Api-Key header injection
│   │   ├── jobs.ts
│   │   ├── reviewQueue.ts
│   │   └── webhooks.ts
│   ├── config/
│   │   └── confidence.ts          # CONFIDENCE_THRESHOLDS constant (§4)
│   ├── types/
│   │   └── backend.ts             # TS types mirroring BACKEND.md §3 schemas exactly
│   ├── hooks/
│   │   ├── useJobPolling.ts       # implements §6 backoff schedule
│   │   └── useReviewResolve.ts
│   └── styles/
│       ├── tokens.css             # §1.2–1.4 design tokens
│       └── global.css
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

---

## 12. Sync Contract with `BACKEND.md`

| Frontend surface | Backend dependency | Status |
|---|---|---|
| Job list (§3.1) | `GET /v1/jobs` (list, paginated) | ✅ Defined, §4.1 |
| Job submission (§3.2) | `POST /v1/documents` | ✅ Defined, §4.1 |
| Webhook test (§3.2) | `POST /v1/webhooks/test` | ✅ Defined, §4.1 |
| Job detail polling (§3.3, §6) | `GET /v1/jobs/{id}` | ✅ Defined, §4.1 |
| Job result view (§3.4) | `GET /v1/jobs/{id}/result` | ✅ Defined, §4.1 — field-level mapping confirmed exact |
| Review queue list (§3.5) | `GET /v1/review-queue` | ✅ Defined, §4.1 |
| Review item detail — PDF source (§3.6) | `GET /v1/documents/{document_id}/pdf` | ✅ Defined, §4.1 — returns binary PDF data from Postgres BYTEA |
| Review item — approve/correct (§3.6, §5.3) | `POST /v1/review-queue/{item_id}/resolve` | ✅ Defined, §4.1 — `approved`/`corrected`/`escalated` resolutions |
| Review item — escalate (§3.6) | Same endpoint, `escalated` resolution | ✅ Defined, §4.1 — `escalated` value added to resolve schema |
| Review item — claim/lock on open (§5.3) | Distinct claim endpoint or optimistic lock | **Deferred** — only matters once team mode (§2.1) is built; solo use has no contention |
| Confidence badge thresholds (§4.1) | `BACKEND.md` §5.7 thresholds (0.80/0.70) | ✅ Synced exactly, implemented as shared constant per explicit provisional-value warning in §5.7/§12 |
| Job status pill enum (§4.4) | `jobs.status` enum | ✅ Synced exactly, §3.1 |
| Discrepancy flag enum (§4.2) | `match_results.discrepancy_flag` enum | ✅ Synced exactly, §3.1 |
| Review reason enum (§3.5, §4.5) | `review_queue.reason` enum | ✅ Synced exactly, §3.1 |
| Error state copy (§9) | Error envelope `code` values | ✅ Synced exactly, §4.3 |
| Upload size limit (§3.2, §4.8) | `MAX_UPLOAD_SIZE_MB=25` | ✅ Synced exactly, §4.1 and §11.2 |
| Analytics — all charts (§7) | `GET /v1/analytics/usage` | ✅ Defined, §4.1 — returns jobs/documents/accuracy/processing_time/llm_usage by period |
| Settings — API keys (§3.8) | `GET /v1/api-keys`, `POST /v1/api-keys`, `DELETE /v1/api-keys/{id}` | ✅ Defined, §4.1 |
| Settings — Webhooks (§3.9) | `GET /v1/settings/webhook`, `PUT /v1/settings/webhook` | ✅ Defined, §4.1 — account-level default, per-job overrides |

**Summary:** All 18 rows are now ✅ or deferred (team-mode claim/lock, which is a future concern, not a gap). The core flow (submit → poll → review → resolve → result) and all MVP screens are fully backed by defined endpoints.
