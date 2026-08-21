# FreightPipe — Production Rebuild Plan

**Status:** Complete rebuild needed — current frontend is disconnected stubs, backend has no user auth.
**Goal:** A real, deployable SaaS product with proper user flow, dashboard, documentation, and trust signals.

---

## What a Real SaaS Needs (researched)

### Pages Required
1. **Landing Page** — Hero, features, how-it-works, pricing, FAQ, footer
2. **Registration** — Email, phone, company name, password (stored in Postgres, hashed with bcrypt)
3. **Login** — Email + password → JWT token
4. **Dashboard** — Job overview, recent activity, quick actions, stats
5. **Documents** — Upload, list, view results, download JSON
6. **Review Queue** — Items needing human review, inline corrections
7. **Analytics** — Usage charts, accuracy metrics, processing stats
8. **Settings** — Profile, API keys, webhooks, team (future)
9. **Documentation** — API reference, quickstart, examples
10. **Pricing** — Plans (free tier highlighted)

### Trust Signals (B2B SaaS research)
- Professional landing page with clear value proposition
- "Free tier" prominently displayed (reduces friction)
- API documentation (shows technical credibility)
- Security: "Your data is encrypted", "SOC2-ready", "No data sharing"
- Social proof: "Built for freight brokerages", use cases
- Clean, dark theme (developer/technical audience)

---

## Backend Changes Required

### 1. User Authentication System
**New table: `users`**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    company_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

**New endpoints:**
- `POST /v1/auth/register` — email, phone, company_name, password → creates user + account + API key
- `POST /v1/auth/login` — email + password → returns JWT token
- `GET /v1/auth/me` — returns current user profile (requires JWT)
- `PUT /v1/auth/profile` — update profile (requires JWT)

**Auth flow:**
- Registration creates a `users` row + `accounts` row + `api_keys` row
- Login returns a JWT token (valid 24h)
- JWT contains `user_id` and `account_id`
- All `/v1/*` endpoints accept either `X-Api-Key` OR `Authorization: Bearer <jwt>`
- Password hashing: bcrypt via `passlib`

### 2. Database Migration
- Add `users` table
- Add `user_id` column to `accounts` table (link user to account)
- Update `api_keys` to support JWT-based auth

### 3. New Dependencies
- `passlib[bcrypt]` — password hashing
- `python-jose[cryptography]` — JWT tokens

---

## Frontend Rebuild

### Architecture
- React 18 + TypeScript + Vite
- React Router v6 (nested routes with layout)
- TanStack Query (data fetching/caching)
- CSS Modules with design tokens (already have)
- No external UI library (keep it lean)

### Page Breakdown

#### 1. Landing Page (`/`)
- Hero: "Turn messy freight PDFs into clean JSON"
- Features grid: 6 key features with icons
- How it works: 4-step visual flow
- Pricing: Free tier highlighted, "Coming soon" for paid
- FAQ: 5-6 common questions
- Footer: Links, GitHub, legal

#### 2. Register (`/register`)
- Form: email, phone, company name, password, confirm password
- Validation: email format, password strength, match
- On success: auto-login, redirect to dashboard
- Error handling: "Email already registered"

#### 3. Login (`/login`)
- Form: email, password
- "Forgot password?" link (future)
- "Don't have an account? Register"
- On success: redirect to dashboard

#### 4. Dashboard (`/dashboard`)
- Welcome message with user/company name
- Stats cards: Total documents, Processed, Needs Review, Accuracy %
- Recent jobs table (last 5)
- Quick actions: Upload document, View API keys
- Getting started checklist (for new users)

#### 5. Documents (`/documents`)
- Upload zone (drag-drop, 25MB limit)
- Document list table with filters (status, type)
- Click to view result: full JSON, field-by-field confidence, 3-way match
- Download JSON button

#### 6. Review Queue (`/review-queue`)
- List of items needing review
- Click to review: PDF viewer + extracted fields + inline editing
- Approve / Correct / Escalate actions

#### 7. Analytics (`/analytics`)
- Usage chart (documents over time)
- Accuracy metrics
- Processing time stats
- LLM usage breakdown

#### 8. Settings (`/settings`)
- Profile tab: edit email, phone, company name
- API Keys tab: list, create (show once), revoke
- Webhooks tab: configure URL, test, view delivery log

#### 9. Documentation (`/docs`)
- Quickstart guide
- API reference (all 18 endpoints with examples)
- Code examples (Python, JavaScript, curl)
- FAQ

#### 10. Pricing (`/pricing`)
- Free tier: 100 documents/month, 1 user, community support
- Pro (coming soon): unlimited, team, priority support
- Enterprise (coming soon): custom, SLA, dedicated support

---

## Implementation Order

### Step 1: Backend Auth (30 min)
- Add users table + migration
- Add auth endpoints (register, login, me, profile)
- Add JWT middleware
- Update existing endpoints to accept JWT
- Test with curl

### Step 2: Frontend Core (45 min)
- Create Layout component (sidebar + header + content)
- Create Auth context (JWT state, login/logout)
- Create Login page
- Create Register page
- Create ProtectedRoute component
- Update App.tsx with proper routing

### Step 3: Frontend Pages (60 min)
- Landing page (hero, features, how-it-works, pricing, FAQ)
- Dashboard (stats, recent jobs, quick actions)
- Documents (upload, list, view result)
- Review Queue (list, review detail)
- Analytics (charts)
- Settings (profile, API keys, webhooks)
- Documentation (API reference, quickstart)

### Step 4: Integration + Deploy (30 min)
- Wire frontend to backend API
- Test full flow: register → login → upload → view result
- Build frontend
- Deploy to Cloudflare Pages
- Test live

---

## Design Tokens (already defined)
- Background: #0E1013
- Surface: #16191D
- Border: #2A2F36
- Text: #E8EAED / #9AA1AC / #5C636E
- Accent: #4A7CFF
- Confidence: #3FB68B / #D9A441 / #E55A4E
- Font: Inter (UI) + JetBrains Mono (data)

---

## Key Technical Decisions
1. **JWT + API Key dual auth** — JWT for web sessions, API key for programmatic access
2. **No OAuth/social login** — Simple email/password, add OAuth later if needed
3. **No email verification** — Sandy's request: just register and go
4. **Postgres for users** — Already have Neon, no extra service
5. **bcrypt for passwords** — Industry standard, no external service
6. **CSS Modules** — Already in use, keeps styles scoped
7. **No external UI library** — Custom components, smaller bundle

---

## Success Criteria
- [ ] User can register with email + password
- [ ] User can login and see dashboard
- [ ] User can upload a PDF and see it in the document list
- [ ] User can view extracted results with confidence scores
- [ ] User can manage API keys
- [ ] Landing page looks professional with trust signals
- [ ] Documentation page has API reference
- [ ] Full flow works end-to-end on live deployment
