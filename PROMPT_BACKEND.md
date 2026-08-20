# PROMPT — Claude: Deep-Research + Draft the BACKEND MD only

> Paste this prompt into Claude ALONGSIDE the `PROJECT.md` file. Tell Claude to read
> `PROJECT.md` first, then follow the instructions below. Output: ONE markdown file
> (`BACKEND.md`), nothing else.

---

You are a senior backend architect and freight/AP-automation domain expert. You are designing
the BACKEND ONLY of a project called **FreightPipe** — a headless, freight-specialized
document-normalization API. Read the attached `PROJECT.md` first; it is the authoritative spec.
Everything you produce must obey its constraints, especially the **free-tier-only** rule.

## Your task

1. **Deep web research** (do not rely only on what I give you — verify and deepen it):
   - Current reality of free-tier LLM access (OpenRouter `:free` model list, Google Gemini Flash
     free-tier limits + vision capability, Groq free limits) — cite what's live *now*, not stale blog posts.
   - Free-tier hosting that actually supports a Python backend — **NOT self-hosted on a VPS**.
     Evaluate: Cloudflare Workers free (100K req/day, JS/TS only — use for API gateway +
     lightweight orchestration), Koyeb free (1 nano service, always-on, Python OK), Render free
     (spins down after 15min idle, cold start ~30s), Fly.io free. Compare cold-start behaviour,
     request limits, and which is best for a document-processing workload. The VPS is NOT used.
   - Free managed Postgres options (Neon/Supabase/Turso) — limits, and which is best for a job queue.
   - Free object storage (Cloudflare R2 vs Backblaze B2) for PDF blobs.
   - State-of-the-art document extraction for messy freight PDFs: OCR (pytesseract/PaddleOCR) vs
     multimodal LLM extraction, and honest accuracy expectations on scanned BOL/POD docs.
   - Anything that changes the design: OpenRouter free-tier request/day limits, Gemini free quota,
     multi-key pooling legality/ToS, rate-limit patterns.

2. **Draft `BACKEND.md`** — a complete, detailed, implementation-ready backend design document.
   Output ONLY this one markdown file. Do NOT write frontend, and do NOT write production code —
   design documents, schemas, API contracts, pseudo-code, and prompt templates are what's wanted.

## `BACKEND.md` must contain, in this order

1. **Scope & architecture overview** — what the backend does, system-context diagram (ASCII), the
   pipeline stages, and the tech stack with a one-line rationale per choice.
2. **Free-tier strategy** — exactly how the LLM layer, hosting, DB, storage, and queue stay free;
   the provider-agnostic LLM router design (key pool, round-robin, 429 backoff, fallback chain);
   metering + caching to protect the free tier. Include the specific free limits you verified.
3. **Data model** — full DB schema (tables, columns, indexes, relations) AND the canonical JSON
   schema for each document type (rate-con, BOL, POD, invoice) with field types and required-ness.
4. **API contract** — every endpoint (method, path, request body, response body, status codes),
   auth (X-Api-Key), idempotency, webhook design, error envelope. This section will be the
   contract the frontend is built against, so make it exact and complete.
5. **Pipeline stage designs** — one subsection per stage: document classification, merged-PDF
   page-split, extraction (text vs OCR/vision path), normalization, domain validation, 3-way match
   engine (with the exact reconciliation rules + discrepancy flags), confidence scoring
   (how 0–1 per-field and per-doc is computed), human-in-the-loop queue (state machine).
6. **LLM & OCR design** — prompt templates for extraction, structured-output approach (JSON schema
   enforcement), OCR/vision fallback logic, and the deterministic-rules-first / LLM-escalation
   philosophy (rules handle the deterministic 80%, LLM the fuzzy 20%).
7. **Security** — secrets handling (.env only), PII redaction, prompt-injection defense on
   document text, rate limiting, input validation.
8. **Error handling & reliability** — retry/backoff, partial-failure semantics, idempotency,
   dead-letter handling.
9. **Evaluation harness & accuracy targets** — how to build the labeled corpus, the exact metrics
   (field-level F1, 3-way-match accuracy, confidence calibration), and target thresholds per stage.
10. **Testing strategy** — unit/integration/e2e layers, attack cases (malformed PDFs, obfuscated
    text, adversarial JSON), fixtures.
11. **Deployment & config** — free-tier cloud-only infra map (NO VPS — Cloudflare Workers for API,
    Koyeb/Render free for Python processing, Cloudflare Pages for frontend, Neon/Supabase for DB,
    Cloudflare R2 for storage), required environment variables (.env keys), CI notes.
12. **Risks, assumptions, open questions** — call out what's genuinely hard and what needs a
    decision from the owner.

## Hard rules

- **Free tier only.** If a design choice needs a paid service, you MUST name a free alternative or
  flag it explicitly as a blocker — never silently assume a paid dependency.
- **Measured accuracy, not claimed accuracy.** Any accuracy number must be a *target to verify on
  a corpus*, never an assertion that the system "is 99% accurate."
- **Deterministic rules first, LLM escalation second** — the pattern that wins in production.
- **Cite sources** for every free-tier limit, model, or benchmark you rely on (URL + date).
- **Be concrete** — real endpoint paths, real JSON, real column names, real prompt templates.
  No hand-waving.

Output exactly one markdown file titled `BACKEND.md`. Begin it with a one-paragraph executive
summary, then the 12 sections above.
