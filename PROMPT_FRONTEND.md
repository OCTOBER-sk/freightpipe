# PROMPT — Claude: Ask Questions First, Then Draft the FRONTEND MD

> Paste this prompt into a **separate Claude account** alongside `PROJECT.md` and `BACKEND.md`.
> Tell Claude to read both files first, then follow the instructions below.
> **Output:** ONE markdown file (`FRONTEND.md`), nothing else.

---

You are a senior product designer and frontend architect with deep experience in
B2B SaaS tools for logistics and freight operations. You are designing the
**FRONTEND ONLY** of a project called **FreightPipe** — a freight document
normalization service with a review dashboard, job monitoring, and exception
management UI.

Read `PROJECT.md` first (the authoritative spec), then `BACKEND.md` (the API
contract and data model your frontend must be built against). Everything you
produce must obey the free-tier-only constraint from `PROJECT.md` and must be
a perfect sync with `BACKEND.md`'s API endpoints, data schemas, and async job
model.

## PHASE 1: ASK QUESTIONS FIRST (do NOT skip this)

Before writing a single line of `FRONTEND.md`, you MUST ask the owner (Sandy)
the following questions. Present them as a numbered list and wait for answers.
Do not assume defaults — the owner has strong opinions about design quality and
will reject generic-looking work.

### Questions to ask:

1. **Brand identity:** Do you have a company name, logo, or brand colours in
   mind for FreightPipe? Or should I propose a visual identity? (If proposing,
   I'll need to know: what feeling should the product convey — clinical
   precision, warm trust, technical authority, something else?)

2. **Primary users:** Who uses this dashboard day-to-day?
   - (a) A single operations person at a small brokerage (solo, self-serve)
   - (b) A small team (2–5 people: ops manager + processors)
   - (c) Both — starts as (a), scales to (b)
   This changes navigation complexity, multi-user features, and information
   density.

3. **Review workflow priority:** The backend has a human-in-the-loop review
   queue (low-confidence extractions, 3-way-match discrepancies). How central
   is this to the daily workflow?
   - (a) Primary — most time is spent reviewing/correcting extractions
   - (b) Secondary — most documents auto-process cleanly, review is occasional
   - (c) Unknown — we'll find out during eval harness testing

4. **Information density preference:** Freight people are used to dense data
   screens (TMS, ERP). Do you want:
   - (a) Dense — tables with many columns, minimal whitespace, maximum info
         per screen (like a Bloomberg terminal or freight TMS)
   - (b) Balanced — structured cards with expandable detail, comfortable
         whitespace (like Linear or Stripe Dashboard)
   - (c) Spacious — large type, generous spacing, fewer items per screen
         (like a modern SaaS landing-page-turned-app)

5. **Mobile requirement:** Will anyone use this on a phone or tablet?
   - (a) Desktop only — freight back-office sits at a desk
   - (b) Desktop-primary, tablet-occasional (e.g., checking status on the go)
   - (c) Mobile matters — field workers or brokers checking from phones

6. **Demo/MVP scope:** For the first version, which views/screens are
   essential vs. nice-to-have? My proposed essentials (confirm or cut):
   - **Essential:** Job submission (upload PDF), Job status + result view,
     Review queue, Document detail with field-level confidence overlay
   - **Nice-to-have:** Dashboard/analytics (volume, accuracy trends, SLA),
     Account settings, API key management, Bulk upload

7. **Design taste — what to AVOID:** I will not use these unless you
   explicitly ask for them:
   - Gradient-heavy "SaaS startup" hero sections
   - Rounded-corner-everything with drop shadows on every card
   - Emoji in navigation or status labels
   - Fake testimonials, made-up stats, or "Trusted by 10,000+ companies"
   - Animated illustrations or Lottie characters
   - Generic stock photos of trucks or shipping containers
   - "Dark mode as default" without a reason
   Is there anything else you specifically hate in B2B software UI?

8. **Competitor UI references:** Are there any products (freight or otherwise)
   whose UI you admire? Even a screenshot or a "I like how X does their
   table view" helps enormously. Conversely, any products whose UI you
   specifically want to NOT look like?

9. **Deployment target:** The frontend deploys to Cloudflare Pages (free,
   static). This means:
   - Pure static site (React/Vue/Svelte + client-side routing)
   - OR static site + Cloudflare Workers for BFF (backend-for-frontend) if
     needed for API key proxying
   - No server-side rendering (no Node.js server on a VPS)
   Do you have a framework preference, or should I choose based on the
   design requirements?

10. **Review UI correction workflow:** When a human corrects an extracted field
    (e.g., fixing a misread rate), should the UI:
    - (a) Allow inline editing of any field directly in the document view
    - (b) Open a correction modal/panel with the original document visible
          alongside the extracted data
    - (c) Both — inline for quick fixes, modal for complex corrections

**WAIT for answers to ALL 10 questions before proceeding to Phase 2.**

---

## PHASE 2: DRAFT `FRONTEND.md`

After receiving answers, draft a complete, detailed, implementation-ready
frontend design document. Output ONLY this one markdown file.

### `FRONTEND.md` must contain, in this order:

1. **Design philosophy & brand identity** — the visual language, colour palette
   (exact hex values, 4–6 colours max), typography (specific Google Fonts or
   system font stacks, with rationale), spacing system, and the ONE signature
   visual element that makes this product recognisable and not interchangeable
   with any other B2B dashboard. State what makes this NOT look like a
   template.

2. **Information architecture** — full sitemap/nav structure, screen inventory,
   user flow diagrams (ASCII), and how the async job model from `BACKEND.md`
   maps to UI states (queued → processing → complete/needs_review/failed).

3. **Screen-by-screen designs** — for EACH screen, provide:
   - Purpose (one sentence)
   - ASCII wireframe (detailed, showing actual layout, not rough boxes)
   - Component inventory (what UI elements exist on this screen)
   - Data bindings (which `BACKEND.md` API endpoints and response fields
     populate each component — be exact: `GET /v1/jobs/{id}/result` →
     `documents[].fields.{name}.confidence` → confidence badge colour)
   - State variations (loading, empty, error, populated)
   - Responsive behaviour (if applicable per the owner's answer to Q5)

4. **Component library specification** — every reusable component:
   - Confidence badge (colour scale: green ≥0.80, amber 0.70–0.79,
     red <0.70 — synced with `BACKEND.md` §5.7 thresholds)
   - Discrepancy flag indicator (synced with `BACKEND.md` §5.6 flag values)
   - Document type indicator (rate_con, bol, pod, invoice — icons or labels)
   - Job status pill (queued, classifying, splitting, extracting, normalizing,
     validating, matching, scoring, needs_review, complete, failed,
     needs_llm_capacity — synced with `BACKEND.md` §3.1 `jobs.status` enum)
   - Review queue item card
   - Field extraction detail row (field name, extracted value, confidence,
     source page + bbox highlight, extraction method badge)
   - 3-way match result row (line item, three source values, discrepancy flag)
   - Upload zone (drag-and-drop PDF, size limit from `BACKEND.md` §4.1: 25MB)
   - Webhook status indicator
   - API key management card
   Each component: props/inputs, visual states, accessibility notes.

5. **Review workflow UX** — the complete human-in-the-loop flow:
   - How review items appear in the queue (sorted, filtered, prioritised)
   - The review detail view (original PDF viewer + extracted data side-by-side
     + confidence overlay + correction interface)
   - Resolution flow (approve / correct / escalate — synced with
     `BACKEND.md` §5.8 state machine: pending → in_review → resolved/escalated)
   - How corrections write back via `POST /v1/review-queue/{item_id}/resolve`

6. **Real-time status & polling strategy** — how the UI handles the async job
   model from `BACKEND.md` §4:
   - Job submission → immediate 202 response → polling `GET /v1/jobs/{id}`
     (frequency: every 2s for first 30s, then every 5s, then every 15s after
     2min — exponential backoff matching realistic processing times)
   - Webhook-driven updates if the frontend has a WebSocket/SSE endpoint
     (flag as enhancement, not MVP)
   - Status transitions and what the user sees at each stage

7. **Data visualisation** (if dashboard/analytics is in scope):
   - Volume trends (jobs/day, documents/day)
   - Accuracy metrics (avg confidence, review rate, correction rate)
   - Processing time distribution
   - LLM usage vs. cache hit rate (from `BACKEND.md` §2.6
     `provider_usage_log`)
   All charts: specify library (Chart.js free / Recharts / lightweight
   alternatives), data source endpoint, and refresh strategy.

8. **Accessibility & keyboard navigation** — WCAG 2.1 AA minimum:
   - Focus management for the review workflow (keyboard-navigable field
     corrections)
   - Colour is never the only indicator (confidence badges have text labels
     too)
   - Screen reader labels for all data-heavy components
   - Reduced motion support

9. **Error & empty states** — every screen's error and empty state designed
   explicitly (synced with `BACKEND.md` §4.3 error codes):
   - `invalid_pdf` → clear message + re-upload prompt
   - `file_too_large` → show the 25MB limit + suggest splitting
   - `rate_limited` → show retry countdown
   - `llm_capacity_exhausted` → explain the free-tier limit, suggest BYOK
   - Empty review queue → "All clear — no items need review"
   - Empty job list → "Submit your first document" with upload CTA

10. **Tech stack & build** — framework choice (with rationale), CSS approach
    (Tailwind / CSS Modules / vanilla — justify based on the design, not
    habit), state management, build tool, and deployment to Cloudflare Pages.
    All free-tier. No paid dependencies.

11. **File tree** — the complete frontend directory structure to build.

12. **Sync contract with `BACKEND.md`** — a table mapping every frontend
    component/screen to its backend dependency (endpoint, field, status code).
    This is the integration checklist: if a row exists here, the frontend
    MUST consume that backend capability. If the backend doesn't provide it,
    flag it as a backend gap.

---

## Hard rules

- **Free tier only.** Same constraint as `PROJECT.md`. No paid UI libraries,
  no paid hosting, no paid analytics.
- **Synced with `BACKEND.md`, not independent.** Every API call, every status
  enum, every error code, every confidence threshold must match `BACKEND.md`
  exactly. If `BACKEND.md` says the confidence threshold for HITL routing is
  0.80, the frontend's confidence badge colour break must be at 0.80 — not
  0.75, not 0.85, not "approximately 0.8."
- **No generic SaaS aesthetics.** The design must feel like a tool built by
  someone who understands freight operations — not a Notion template reskinned
  with a truck logo. If a component looks like it could be from any AI-wrapper
  dashboard, redesign it.
- **No fake claims, no filler content.** No "AI-powered insights," no
  "revolutionary document processing," no "trusted by industry leaders."
  Every word in the UI must describe a real function the backend actually
  provides.
- **No childish UI patterns.** No emoji status indicators, no confetti on
  completion, no animated mascots, no "Great job!" messages. Status is
  communicated through colour, typography, and precise language — like a
  professional operations tool.
- **Be concrete.** Real hex values, real font names, real component props,
  real API endpoints, real ASCII wireframes. No hand-waving.
- **Cite design decisions.** If you choose a specific font, say why. If you
  pick a colour palette, explain what it communicates. Every choice should
  be traceable to either the owner's answers (Phase 1) or a deliberate
  design rationale.

Output exactly one markdown file titled `FRONTEND.md`. Begin it with a
one-paragraph executive summary, then the 12 sections above.
