# FreightPipe — Full Enhancement Plan

**Status:** Frontend and backend are live and connected. Now enhancing to production quality.
**Approach:** Research-backed changes. No fake claims, no generic SaaS look, no childish elements.

---

## 1. THEME CHANGE — From Generic Blue-Black to Distinctive

### Current (generic)
- Background: `#0E1013` (near-black with blue tint)
- Accent: `#4A7CFF` (generic SaaS blue)
- Problem: Looks like every other AI/dev tool dashboard

### New Palette — "Warm Operations"
Inspired by freight/logistics operational tools. Warm, professional, distinctive.

```
Background:    #000000     (warm near-black, no blue tint)
Surface:       #0A0A0A     (warm dark surface)
Surface-raised:#141414     (slightly lighter warm)
Border:        #1F1F1F     (warm gray border)
Text primary:  #E8E6E1     (warm off-white)
Text secondary:#9C9A94     (warm muted)
Text tertiary: #5E5C57     (warm disabled)
Accent:        #A07070     (amber/gold — freight, logistics, authority)
Accent hover:  #B88080     (lighter gold on hover)
Success:       #5B8A72     (muted sage green — not bright/neon)
Warning:       #C4953A     (warm amber, close to accent)
Error:         #B85450     (muted red — not harsh)
```

**Why amber/gold:** Freight is about movement, value, trust. Gold conveys authority and value without being childish. It's distinctive from every blue/black SaaS. The warm neutrals feel like a serious operations tool, not a startup demo.

### Landing Page Theme
Light theme with warm tones:
```
Background:    #F7F6F3     (warm off-white)
Surface:       #FFFFFF     (pure white cards)
Text:          #0A0A0A     (warm dark)
Accent:        #A07070     (same amber/gold)
```

---

## 2. LANDING PAGE — Remove Generic, Add Real

### Remove
- Unicode icon characters (⚙⚠◆↻☰▸) — replace with SVG icons or remove
- Generic "Start for Free" CTA without context
- The preview card with fake data (RC-48213, $1,850.00)

### Add
- **Real problem statement:** "Freight back-offices re-key the same numbers from PDFs by hand. 15% of carrier invoices contain errors. Manual keying runs 1-4% field error rate."
- **Real value prop:** "FreightPipe extracts structured data from freight documents and cross-checks them automatically. No TMS required."
- **How it actually works:** Submit PDF → classify → extract → validate → 3-way match → review queue → JSON output
- **API-first messaging:** "REST API with API key auth. Submit documents, poll for results, configure webhooks."
- **Honest pricing:** Free tier = 100 docs/month. No "AI-powered revolution."
- **Footer:** GitHub link, API docs link, no social proof fakery

---

## 3. DASHBOARD — Make It Useful

### Current issues
- Shows raw job count without context
- No onboarding guidance
- Quick actions are generic

### Enhancements
- **Stats cards:** Show meaningful metrics (documents processed, accuracy rate, items in review)
- **Recent activity feed:** Last 5 actions with timestamps
- **Getting started guide:** 3 steps for new users (1. Get API key, 2. Submit first document, 3. Review results)
- **API key quick-copy:** Show API key with copy button on dashboard for new users
- **Empty state:** "No documents yet. Upload your first freight document to get started."

---

## 4. DOCUMENTS PAGE — Real Workflow

### Enhancements
- **Upload zone:** Clear drag-drop area with file size limit (25MB) and supported types
- **Document table:** filename, status (with rail), document type, confidence score, submitted date
- **Click to expand:** Show extracted fields inline without navigating away
- **Download JSON:** Button to download the structured result
- **Status explanations:** Tooltip on each status explaining what it means

---

## 5. REVIEW QUEUE — The Core Workflow

### Enhancements
- **Priority sorting:** Oldest first (operational urgency)
- **Reason badges:** Clear labels (Low Confidence, Discrepancy, Classification Failed)
- **Inline correction:** Click a field to edit it directly
- **Side-by-side view:** PDF on left, extracted fields on right
- **Action buttons:** Approve, Correct, Escalate with clear descriptions

---

## 6. DOCUMENTATION — Real API Docs

### Current state
- Need to check if Docs page has real content

### What it needs
- **Quickstart:** 5 steps to first API call (register, get key, submit PDF, poll result, get JSON)
- **Authentication:** API key and JWT explained
- **API Reference:** All 18 endpoints with method, path, request/response examples
- **Code examples:** curl, Python, JavaScript for each endpoint
- **Error codes:** Complete list with descriptions
- **Rate limits:** Documented

---

## 7. SETTINGS — Complete

### Profile tab
- Edit email, phone, company name
- Change password
- Delete account (with confirmation)

### API Keys tab
- List with masked keys + created date
- Create new key (show once, copy button)
- Revoke key (with confirmation)

### Webhooks tab
- Configure webhook URL
- Test button (sends test payload)
- View recent deliveries

---

## 8. AUTH FLOW — Polish

### Login page
- Clean centered card
- Email + password fields
- "Forgot password?" link (future)
- "Don't have an account? Register"
- Backend URL field (configurable)

### Register page
- Email, phone, company name, password
- Validation: email format, password min 8 chars
- Auto-login after registration
- Redirect to dashboard

---

## 9. RESPONSIVE DESIGN

- Sidebar collapses on mobile (< 768px)
- Tables scroll horizontally on small screens
- Upload zone full-width on mobile
- Login/register centered on all screen sizes

---

## 10. COPY — Professional, No Fakery

### Rules
- No "AI-powered" or "revolutionary"
- No fake stats ("10,000+ companies trust us")
- No emoji in UI
- Use freight-specific language (rate con, BOL, POD, accessorial)
- Error messages explain what went wrong AND how to fix it
- Empty states guide users to next action

---

## Implementation Order

1. **Theme change** (tokens.css + all CSS files) — 15 min
2. **Landing page rewrite** — 20 min
3. **Dashboard enhancements** — 15 min
4. **Documents page polish** — 10 min
5. **Review queue polish** — 10 min
6. **Documentation page** — 15 min
7. **Settings completeness** — 10 min
8. **Auth flow polish** — 5 min
9. **Responsive fixes** — 10 min
10. **Copy audit** — 5 min

**Total: ~2 hours of agent work**

---

## What I Will NOT Do
- Add fake testimonials or stats
- Use emoji in navigation or status
- Add gradients or shadows
- Use generic blue/black theme
- Add "AI-powered" claims
- Add illustrations or mascots
- Add confetti or celebrations
