# Freight Document Normalizer — Product & Build Plan

> **Status:** PLANNING ONLY (no code written yet). Awaiting Sandy's go + infra.
> **Owner:** Atom (orchestration + QA + memory + env) · Build via Zeus (backend) + Midas (frontend)
> **Date:** 2026-08-20

---

## 1. Goal (one sentence)

Build a **freight-specialized, headless document-normalization API** that turns any messy
freight document (rate confirmation, BOL, POD, carrier invoice — often merged into one PDF)
into clean, validated JSON with a **3-way match** (rate-con ↔ BOL ↔ POD ↔ invoice),
confidence scoring, and a human-in-the-loop exception queue.

## 2. The Wedge (why this wins)

The entire market is bundled platforms for mid-to-enterprise buyers. The whitespace:

1. **API-first, headless** — no forced TMS adoption. Devs/ISVs embed it.
2. **Freight-domain specialized** — not general OCR. We do the 3-way match + accessorial
   logic + line-item reconciliation that generic IDP (Sensible/Veryfi/ABBYY) does NOT.
3. **Long-tail buyers** — small brokers (under ~40 loads/wk), owner-operators, small
   carriers priced out of $700–$2,400/mo platforms (Tai $995+, Aljex $699+, McLeod).
4. **India market** — 85%+ unorganized trucking, near-zero automation, paperwork-heavy.
   Native India-angle (e.g. e-way bill, IRN/e-invoice, TDS on freight) is a defensible moat.

**What we explicitly do NOT build:** a full TMS, a payment network, a load board, a quoting
engine. Those are the incumbent's turf. We sell the normalizer + matcher they bundle away.

## 3. Competitive reality (honest)

- **Loop** ($160M, $95M Series C Apr 2026): enterprise audit+pay. Not our buyer.
- **Vektor BillIQ**: broker-side matching, bundled in their TMS.
- **Datatruck TruckGPT**: carrier-side extraction, bundled in their TMS.
- **Sensible/Nanonets/Veryfi/ABBYY/Mindee**: headless but generic — no 3-way match, no
  freight accessorial domain logic.
- **Gap we own:** freight-specialized + headless + 3-way match + priced for long tail.

**Conclusion:** not a monopoly play; a wedge play. We win on *domain accuracy + API
distribution*, not on being the biggest.

## 4. Architecture

```
Ingest (email/API/upload) 
  → Document Classification (rate-con? BOL? POD? invoice? merged PDF?)
  → Page-split (detect "one PDF = 3 documents" boundary)
  → Extraction (OCR for scans + LLM for structured field extraction)
  → Normalization (canonical schema: load#, dates, rates, accessorials, weights, line items)
  → Validation (schema + freight-domain rules: units, date coherence, money)
  → 3-way Match engine (rate-con ↔ BOL ↔ POD ↔ invoice; flag line-item discrepancies)
  → Confidence scoring (0–1 per field + per document)
  → Human-in-the-loop queue (below threshold → review UI)
  → Webhook / API return (JSON + source coordinates per field)
```

**Stack (provisional, confirmed at build time):**
- Backend: Python (FastAPI) — reuses Majestan `classify → extract → normalize → act` pattern
- OCR: pytesseract/paddleOCR for scans; LLM (OpenRouter key) for semantic extraction + field typing
- Matching: deterministic rule engine first, LLM as escalation (same philosophy as Majestan:
  rules for determinism, LLM for the fuzzy 20%)
- Store: Postgres (managed cloud per Sandy's standing rule — Neon/Supabase/Turso; conn string in .env)
- Queue/state: redislite in dev, managed later
- Eval harness: pytest + a labeled freight-document corpus with field-level ground truth

## 5. Phased build plan (TDD, bite-sized, verify each phase)

> Each phase ends with a **verification gate** (tests green + real-sample demo + Atom's own
> independent check). No phase starts until the previous gate passes.

### Phase 0 — Corpus & eval harness (THE make-or-break)
- **Blocked on Sandy:** 20–50 real freight PDFs (rate-cons, BOLs, PODs, invoices; redact PII).
- Build `tests/fixtures/` + `eval/` with field-level ground-truth JSON per doc.
- Define the canonical schema + accuracy metrics (field-level F1, match accuracy).
- **Gate:** corpus loads, eval runs on a baseline (empty/naive) extractor, metrics reported.

### Phase 1 — Document classifier + page-splitter
- Classify doc type; detect merged "3-in-1" PDFs and split at document boundaries.
- **Gate:** >95% classification accuracy on corpus; merged-PDF split correct on all fixtures.

### Phase 2 — Extraction (OCR + LLM) for rate-con (single hardest doc first)
- Extract rate-con fields → canonical schema, with per-field source coordinates.
- **Gate:** field-level F1 target on rate-con subset (set target in Phase 0, e.g. ≥90%).

### Phase 3 — Normalization + freight-domain validation
- Canonical units, date coherence, money parsing, accessorial classification.
- **Gate:** validation rules pass on clean + deliberately-broken fixtures (attack cases).

### Phase 4 — 3-way match engine
- Rate-con ↔ BOL ↔ POD ↔ invoice reconciliation; line-item + accessorial discrepancy flags.
- **Gate:** matches correct on corpus; known-bad cases correctly flagged.

### Phase 5 — Confidence scoring + human-in-the-loop queue
- Per-field/per-doc confidence; review UI for below-threshold docs.
- **Gate:** queue routes correctly; review can correct + re-submit (learning loop).

### Phase 6 — API + webhook + auth
- REST API (X-Api-Key), async webhook on completion, idempotent ingest.
- **Gate:** end-to-end API round-trip on a real merged PDF returns matched JSON + coords.

### Phase 7 — Frontend (Midas): ingest + review dashboard
- Upload/inbox view, extraction preview, 3-way-match diff, review queue, settings.
- **Gate:** full user flow on real samples, screenshot-proven (ui-proof-screenshots skill).

### Phase 8 — Hardening
- Attack own code (malformed PDFs, obfuscated text, adversarial JSON), perf on batches,
  security (secrets in .env only, injection-scan), regression suite.

## 6. What's genuinely hard (do not underestimate)

1. **Accuracy on messy freight PDFs** — blurred scans, handwritten POD signatures, watermarks.
   This is the whole moat. Tier2 Systems' honest benchmark: 80–90% automation on clean docs,
   plan for 70–75% conservative. We must *measure*, not claim.
2. **The merged-PDF split** — carriers send rate-con + POD + invoice as ONE file.
3. **Accessorial logic** — detention/layover/fuel surcharge line-item reconciliation.
4. **India domain layer** (if we go India-first): e-way bill, IRN/e-invoice, TDS — real moat,
   real research effort.

## 7. Infra I need from Sandy (explicit)

1. **LLM key** — one OpenRouter key (or two, spare fallback) for extraction LLM calls.
2. **Compute** — a VPS/environment to run FastAPI + workers (or confirm current VPS is fine).
3. **Managed Postgres** — Neon/Supabase/Turso conn string (per standing no-VPS-DB rule).
4. **Real freight PDFs** — 20–50 redacted samples. *This is the single highest-leverage input.*
5. **Decide the market angle** — US long-tail first, or India-first (Section 8, Q1).

## 8. Open questions for Sandy (need decisions before Phase 1)

1. **Market:** US long-tail brokers/carriers first, or **India-first** (unorganized trucking)?
   This changes the domain layer (accessorials vs e-way bill/IRN/TDS) and pricing.
2. **Distribution model:** pure headless API (sell to devs/ISVs) vs. self-serve web app vs. both?
3. **Pricing hypothesis** (to test later, not invent now): per-document vs. monthly tier.
4. **Self-hostable** (on-prem for brokers) or cloud-only MVP?

## 9. Verification standard (non-negotiable, from opencode-workflow)

- PLAN → BUILD → STATIC VERIFY → TEST → ATTACK → REAL E2E → REAL USER FLOW → PERF → SECURITY.
- Agent claims are never evidence — Atom physically verifies files/diffs/tests/runtime.
- Every accuracy claim must come from the eval harness on real docs, never from a demo.
- Final deliverable = verification matrix (PASS / FAIL / NOT VERIFIED / PENDING-MANUAL).

## 10. First 3 actions (once Sandy says go + provides corpus)

1. Create repo `OCTOBER-sk/freight-doc-normalizer` (private), scaffold, commit.
2. Build Phase 0 eval harness against the corpus; establish baseline + accuracy targets.
3. Phase 1 classifier/splitter (Zeus), verified by Atom, before anything else.
