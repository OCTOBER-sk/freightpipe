# FreightPipe — Freight Document Normalizer

> **Codename:** FreightPipe (placeholder — rename anytime)
> **Status:** PLANNING ONLY — no code written. This file is the single source of truth both Claude prompts reference.
> **Owner:** Sandy · Orchestration/QA/memory: Atom · Build: Zeus (backend) + Midas (frontend)
> **Last updated:** 2026-08-20

---

## 1. What it is (one paragraph)

FreightPipe is a **headless, freight-specialized document-normalization API**. It ingests messy
freight documents — rate confirmations, Bills of Lading (BOL), Proof of Delivery (POD), and carrier
invoices — often arriving as a **single merged PDF**, and returns clean, validated JSON with a
**3-way match** (rate-con ↔ BOL/POD ↔ invoice), per-field confidence scores, source coordinates,
and a human-in-the-loop exception queue.

## 2. The problem (why anyone pays)

Freight back-offices re-key the same numbers from PDFs and emails into TMS/ERP systems by hand.
Cited facts:
- **15% of carrier invoices contain errors**; up to 80% of companies overpay freight.
- Only **2% of brokerages fully automate AR**; 43% still partly manual (FreightWaves).
- Manual keying runs a **1–4% field error rate** (spiking to 18–40% under load), **$50–150 per serious error**.
- A rate-con takes **15+ min to key manually**; automation cuts 5 hrs/day to ~20 min (Datatruck).

## 3. Competitive landscape (research summary — verified Aug 2026)

| Player | Position | What they miss |
|---|---|---|
| **Loop** | $160M raised, $95M Series C Apr 2026, $44M rev. Enterprise freight audit+pay | Shippers/3PLs only, enterprise pricing, NA-weighted |
| **Intelligent Audit** (1996) | 2B shipments/yr, ~20% Fortune 50 | Enterprise parcel/LTL, legacy |
| **TriumphPay** | Carrier payment network, POD detection | Payment rail, not normalizer-as-a-service |
| **Vektor (BillIQ + AI Agents)** | Broker-side invoice-vs-ratecon matching | Bundled into their TMS, broker-only |
| **Datatruck / TruckGPT** | Carrier-side rate-con → load record in <15s | Bundled into full TMS (rip-and-replace) |
| **Raft (ex-Vector.ai)** | Freight *forwarder* doc/email AI | Forwarders only, became a platform |
| **Cass, nVision, CTSI, Pando, Trimble** | Legacy freight audit+pay | Enterprise, managed services |
| **Sensible, Nanonets, Veryfi, ABBYY, Mindee** | Headless extraction APIs | **Generic IDP — no freight 3-way match, no accessorial domain logic** |

**The wedge:** every freight-specialized player forces adoption of a full TMS/audit suite. The only
headless APIs are generic OCR. Nobody owns **freight-specialized + headless + 3-way match + priced
for the long tail**. That is our lane.

## 4. Market decision (default, reversible)

- **Default: US long-tail first** — small brokers (< ~40 loads/wk), owner-operators, small carriers
  priced out of $700–$2,400/mo platforms (Tai $995+, Aljex $699+, McLeod). Proven willingness-to-pay.
- **Phase-2 module: India** — 85%+ unorganized trucking, near-zero automation, plus a defensible
  domain layer: e-way bill, IRN/e-invoice, TDS on freight.
- Flag now if you want India-first instead.

## 5. Core pipeline

```
Ingest (email / API / upload)
  → Document classification (rate-con? BOL? POD? invoice? merged PDF?)
  → Page-split (detect "1 PDF = 3 documents" boundaries)
  → Extraction (text for born-digital PDFs; OCR+LLM-vision for scans)
  → Normalization (canonical schema; units, dates, money, accessorials)
  → Validation (schema + freight-domain rules)
  → 3-way match engine (rate-con ↔ BOL ↔ POD ↔ invoice; line-item discrepancy flags)
  → Confidence scoring (0–1 per field + per document)
  → Human-in-the-loop queue (below threshold → review UI)
  → API return / webhook (JSON + per-field source coordinates)
```

## 6. Canonical document types & key fields

- **Rate Confirmation:** load#, broker, carrier, shipper/consignee, pickup/delivery (locations +
  dates/times), linehaul rate, fuel surcharge, accessorials (detention/layover/lumper/stop-off), total, payment terms.
- **Bill of Lading (BOL):** BOL#, load#, shipper/consignee, pickup/delivery, freight description,
  weight, pieces, trailer#, signature, dates.
- **Proof of Delivery (POD):** POD#, delivery date, recipient, signature, condition/damage notes.
- **Carrier Invoice:** invoice#, load#, carrier, line items (linehaul/fuel/accessorials), total, due date, remit-to.

**3-way match =** agreed (rate-con) ↔ delivered (BOL/POD) ↔ billed (invoice); flag any line-item
mismatch (rate delta, missing/extra accessorial, weight/pieces variance).

## 7. Free-tier-only architecture (HARD CONSTRAINT)

No paid services. Everything must run on free tiers, self-hosted infra, or BYOK. Requirements:

**LLM (multi-provider pooling / BYOK):**
- OpenRouter `:free` models (rate-limited, ~50 req/day per key — pool multiple keys).
- Google Gemini Flash via AI Studio free tier (generous; **has vision → doubles as OCR**).
- Groq free tier (fast Llama models).
- BYOK: any provider key the user plugs in.
- Design a **provider-agnostic router**: key pool, round-robin, 429/rate-limit backoff, model
  fallback chain. Never hard-code one provider.

**Hosting (FREE CLOUD ONLY — nothing runs on Sandy's VPS):**
- Backend: Cloudflare Workers (free: 100K req/day, 10ms CPU/invocation, no cold starts) for the
  API layer + lightweight orchestration. Heavy Python processing (PDF extraction, OCR) via a
  free Python host: Koyeb free (1 nano service, always-on) or Render free (spins down after
  15min idle, cold start ~30s). **VPS is NOT used for any backend service.**
- Frontend: Cloudflare Pages free (static + edge, unlimited bandwidth).
- DB: Neon free (Postgres, 0.5 GB, 24/7 compute) / Supabase free / Turso free — managed cloud
  only, never on VPS.
- File storage: PDFs stored directly in Postgres (Neon) as BYTEA — zero extra services, zero card needed. Freight PDFs are typically 1-5MB; Neon's 0.5GB free tier handles ~100-500 PDFs.
- Queue/jobs: Postgres-backed queue (pg-boss on Neon) or Upstash Redis free (10K cmd/day).
- DNS/CDN: Cloudflare free plan (DNS, SSL, CDN, DDoS protection).

**OCR:**
- Born-digital PDFs → direct text extraction (pdfplumber/pypdf) — no OCR cost.
- Scans/photos → Gemini Flash vision (free) primary, pytesseract/PaddleOCR fallback.

**Cost discipline:** LLM calls are the only variable cost; every extraction must be metered and
cached so we never burn the free tier on re-runs.

## 8. Hard problems (do NOT underestimate — these are the moat)

1. **Accuracy on messy freight PDFs** — blurred scans, handwritten POD signatures, watermarks.
   Honest benchmark (Tier2 Systems): 80–90% automation on clean docs; plan 70–75% conservative.
   Accuracy must be *measured* on a labeled corpus, never claimed from a demo.
2. **The merged-PDF split** — carriers send rate-con + POD + invoice as ONE file.
3. **Accessorial line-item logic** — detention/layover/fuel surcharge reconciliation.
4. **India domain layer** (Phase 2) — e-way bill, IRN/e-invoice, TDS.

## 9. Evaluation & verification standard (non-negotiable)

- Build a **labeled corpus** (20–50 real redacted freight PDFs + field-level ground-truth JSON)
  BEFORE feature code. This is the make-or-break input.
- Metrics: field-level F1 per doc type, 3-way-match accuracy, confidence calibration.
- Pipeline order: PLAN → BUILD → STATIC VERIFY → TEST → ATTACK → REAL E2E → REAL USER FLOW → PERF → SECURITY.
- Agent claims are never evidence; every accuracy number comes from the eval harness on real docs.
- Final deliverable = verification matrix (PASS / FAIL / NOT VERIFIED / PENDING-MANUAL).

## 10. Non-goals (do not build)

Full TMS. Payment network. Load board. Quoting engine. EDI/ELD integrations. Anything the
incumbents bundle. We sell the normalizer + matcher they refuse to unbundle.

## 11. Phases (high level)

0. Corpus + eval harness → 1. Classifier + page-split → 2. Rate-con extraction (hardest doc first)
→ 3. Normalization + domain validation → 4. 3-way match engine → 5. Confidence + HITL queue
→ 6. API + webhook + auth → 7. Frontend (review dashboard) → 8. Hardening.

---

## Decisions logged
- **2026-08-20** — Chose "Freight Document Normalizer" (idea C) over legal-deadline engine / vertical RAG / VRASP optimizer.
- **2026-08-20** — Free-tier-only constraint set for the whole build (LLM pooling/BYOK, free hosting, managed free DB).
- **2026-08-20** — Default market = US long-tail first; India as Phase-2 module (pending Sandy's confirmation).
