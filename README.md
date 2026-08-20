# FreightPipe

**Headless freight document normalization API.**

Ingests messy freight PDFs (rate confirmations, BOLs, PODs, carrier invoices — often merged into one file) → returns clean, validated JSON with 3-way match, per-field confidence scores, and a human-in-the-loop review queue.

## Status

**PLANNING + DESIGN** — no production code yet. Design documents are the source of truth.

## Design Documents

| File | Purpose |
|---|---|
| [`PROJECT.md`](PROJECT.md) | Authoritative spec — what we build, why, constraints |
| [`BACKEND.md`](BACKEND.md) | Complete backend design — API contract, data model, pipeline, LLM router, deployment |
| [`FRONTEND.md`](FRONTEND.md) | Complete frontend design — screens, components, review UX, sync contract with backend |
| [`PROMPT_BACKEND.md`](PROMPT_BACKEND.md) | Claude prompt that produced BACKEND.md |
| [`PROMPT_FRONTEND.md`](PROMPT_FRONTEND.md) | Claude prompt that produced FRONTEND.md |

## Architecture (Free Tier Only)

- **API edge:** Cloudflare Workers (free)
- **Processing:** Koyeb free Instance (Python/FastAPI)
- **DB:** Neon Postgres (free)
- **Storage:** Cloudflare R2 (free)
- **LLM:** OpenRouter free + Gemini Flash + Groq + BYOK (provider-agnostic router)
- **Frontend:** React + Vite → Cloudflare Pages (free)

## License

TBD
