# FreightPipe Frontend Guide

**Purpose:** Reference document for building the FreightPipe frontend. Every page, component, and style decision must follow this guide.

---

## Design System

### Colors (tokens.css — use these EXACT values)
```
--bg-base: #0E1013          /* App background */
--surface: #16191D          /* Card/panel backgrounds */
--surface-raised: #1D2126   /* Hover, active states */
--border: #2A2F36           /* All borders */
--text-primary: #E8EAED     /* Headings, body text */
--text-secondary: #9AA1AC   /* Labels, metadata */
--text-tertiary: #5C636E    /* Disabled, placeholders */
--accent: #4A7CFF           /* Primary actions, links */
--confidence-high: #3FB68B  /* Green — good */
--confidence-mid: #D9A441   /* Amber — caution */
--confidence-low: #E55A4E   /* Red — needs attention */
```

### Typography
- **UI text:** Inter (400, 500, 600 weights)
- **Data/monospace:** JetBrains Mono (400)
- **Base size:** 13px
- **Scale:** 11px / 12px / 13px / 15px / 18px / 20px / 24px

### Spacing (8px base)
4px / 8px / 12px / 16px / 24px / 32px / 48px

### Border Radius
Maximum 4px — no rounded-everything

### What NOT to do
- No gradients on backgrounds or buttons
- No box-shadows on cards (use borders instead)
- No emoji in status indicators or navigation
- No confetti or celebration animations
- No stock photos or illustrations
- No "AI-powered" or "revolutionary" copy
- No rounded pill buttons (max 4px radius)

---

## Page Structure

### Public Pages (no auth required)
1. **Landing** (`/`) — marketing page
2. **Login** (`/login`) — email + password
3. **Register** (`/register`) — email, phone, company, password
4. **Docs** (`/docs`) — API documentation

### Protected Pages (require auth, inside Layout)
5. **Dashboard** (`/dashboard`) — overview
6. **Documents** (`/documents`) — upload + list
7. **Review Queue** (`/review-queue`) — items needing review
8. **Analytics** (`/analytics`) — charts + metrics
9. **Settings** (`/settings`) — profile, API keys, webhooks

---

## Layout Component

### Sidebar (240px, left)
```
┌──────────────────────────┐
│  FreightPipe             │
│  Document Normalizer     │
├──────────────────────────┤
│                          │
│  ○ Dashboard             │
│  ○ Documents             │
│  ○ Review Queue    [3]   │
│  ○ Analytics             │
│  ○ Settings              │
│                          │
│  ────────────────────    │
│  Company Name            │
│  user@email.com          │
│  [Logout]                │
└──────────────────────────┘
```

- Active item: accent color (#4A7CFF), light background
- Badge on Review Queue: count of pending items
- User info at bottom

### Header (48px, top)
- Page title (left)
- User avatar/name (right)

### Content Area
- Scrollable
- 24px padding
- Max-width: 1200px centered

---

## Page Specifications

### 1. Landing Page (`/`)
**Purpose:** Convert visitors to registered users

**Sections:**
1. **Nav bar:** Logo | Features | Pricing | Docs | Login | [Get Started]
2. **Hero:** "Turn messy freight PDFs into clean, validated JSON" + subtitle + CTA
3. **Features:** 6 cards (icon + title + description)
4. **How it works:** 4 steps with numbers
5. **Pricing:** Free tier highlighted, Pro/Enterprise "Coming Soon"
6. **FAQ:** 5-6 questions
7. **Footer:** Links, GitHub, copyright

**Design:** Can use lighter background for hero section. Rest follows dark theme.

### 2. Login (`/login`)
**Purpose:** Authenticate existing users

**Layout:** Centered card (380px wide)
**Fields:**
- Email (text input)
- Password (password input)
- [Login] button
- "Don't have an account? Register" link

**Validation:**
- Email format check
- Show error if invalid credentials
- Loading state on submit

### 3. Register (`/register`)
**Purpose:** Create new account

**Layout:** Centered card (420px wide)
**Fields:**
- Email (text input)
- Phone (text input, optional)
- Company Name (text input)
- Password (password input, min 8 chars)
- Confirm Password (password input)
- [Create Account] button
- "Already have an account? Login" link

**On success:** Auto-login, redirect to /dashboard

### 4. Dashboard (`/dashboard`)
**Purpose:** Overview of user's activity

**Layout:**
```
┌─────────────────────────────────────────┐
│  Welcome back, Company Name             │
│                                         │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │
│  │ Total  │ │Proces- │ │ Review │ │Accuracy│ │
│  │ Docs   │ │ sed    │ │ Queue  │ │   %    │ │
│  │  142   │ │  120   │ │   18   │ │  91%   │ │
│  └────────┘ └────────┘ └────────┘ └────────┘ │
│                                         │
│  Recent Documents                       │
│  ┌─────────────────────────────────────┐ │
│  │ rate_con_RC48213.pdf  ● Complete    │ │
│  │ BOL_merged.pdf        ● Processing  │ │
│  │ invoice_001.pdf       ● Needs Review│ │
│  └─────────────────────────────────────┘ │
│                                         │
│  Quick Actions                          │
│  [Upload Document] [View API Keys]      │
└─────────────────────────────────────────┘
```

### 5. Documents (`/documents`)
**Purpose:** Upload and manage freight documents

**Layout:**
- Upload zone at top (drag-drop, 25MB limit, PDF only)
- Filter bar: All | Queued | Processing | Complete | Failed
- Document table: filename, status, type, confidence, date, actions

### 6. Review Queue (`/review-queue`)
**Purpose:** Review flagged documents

**Layout:**
- Filter: All Reasons | Low Confidence | Discrepancy | Classification Failed
- Queue list: job ID, reason, age, doc type
- Click to expand: PDF viewer + extracted fields + approve/correct/escalate

### 7. Analytics (`/analytics`)
**Purpose:** View usage and accuracy metrics

**Layout:**
- Period selector: 7d | 30d | 90d
- Stats cards: total docs, avg confidence, review rate, correction rate
- Chart: documents over time (bar chart)
- LLM usage breakdown

### 8. Settings (`/settings`)
**Purpose:** Manage account and integrations

**Tabs:**
- **Profile:** email, phone, company name (editable)
- **API Keys:** list (masked), create (show once), revoke
- **Webhooks:** URL input, test button, delivery log

### 9. Documentation (`/docs`)
**Purpose:** Help users integrate with the API

**Layout:**
- Sidebar: table of contents
- Content sections:
  - Quickstart (5 steps to first API call)
  - Authentication (API key and JWT)
  - API Reference (all endpoints)
  - Code Examples (curl, Python, JavaScript)
  - FAQ

---

## Component Standards

### Confidence Badge
- Green: >= threshold (0.80 for doc, 0.70 for field)
- Amber: >= threshold - 0.10
- Red: below that
- Always show numeric value + text label
- Never color alone (WCAG)

### Status Pills
- Queued: gray
- Processing: blue
- Complete: green
- Needs Review: amber
- Failed: red
- Always with text label

### Data Values
- Always in JetBrains Mono (monospace)
- Money: $1,850.00
- Dates: 2026-08-21
- Load numbers: RC-48213

### Forms
- Labels above inputs
- Error messages below inputs in red
- Disabled state: reduced opacity
- Focus state: accent border color

### Tables
- Header row: surface background, bold text
- Rows: alternating subtle backgrounds
- Hover: surface-raised background
- Clickable rows: cursor pointer

---

## API Integration

### Base URL
```
VITE_API_BASE=""  (empty for relative paths, or full URL for external backend)
```

### Auth Headers
```
Authorization: Bearer <jwt-token>  (for web sessions)
X-Api-Key: <api-key>              (for programmatic access)
```

### Error Handling
- 401 → redirect to /login
- 429 → show rate limit message with countdown
- 500 → show generic error with retry button
- Network error → show "cannot reach server" message

---

## Quality Checklist

Before considering any page done, verify:
- [ ] Uses exact design tokens from tokens.css
- [ ] Loading state (skeleton or spinner)
- [ ] Error state (clear message + action)
- [ ] Empty state (helpful message + CTA)
- [ ] Responsive (works on 768px+)
- [ ] Keyboard accessible (tab order, enter to submit)
- [ ] No gradients, shadows, or emoji
- [ ] Data values in monospace
- [ ] Professional copy (no filler, no hype)
