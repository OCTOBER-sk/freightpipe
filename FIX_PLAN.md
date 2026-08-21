# FreightPipe — Production Fix Plan

**Problem:** Frontend is a collection of disconnected pages with no shell, no navigation, no auth, and wrong API URL. Backend Render deployment not responding.

**Goal:** A real, working product with login, navigation, proper API connection, and deployed backend.

---

## Phase 1: Fix the Frontend (Priority)

### 1.1 Create App Shell (Layout Component)
- Sidebar navigation (Jobs, Review Queue, Analytics, Settings)
- Header with app name + current user
- Content area that renders routes
- Responsive (sidebar collapses on mobile)
- Dark theme matching FRONTEND.md design tokens

### 1.2 Create Login Page
- API key input field
- "Connect" button
- Stores key in localStorage
- Redirects to /jobs after login
- Shows error if key is invalid (test against /v1/health)

### 1.3 Create Auth Context
- React context for API key state
- Protected routes (redirect to login if no key)
- Logout functionality (clear key from localStorage)

### 1.4 Fix API Client
- Set VITE_API_BASE to Render URL (or allow override via env)
- Add proper error handling for network failures
- Add loading states

### 1.5 Fix All Route Pages
- Ensure each page renders within the shell
- Fix any broken imports or missing components
- Add proper loading/error/empty states

### 1.6 Rebuild and Deploy
- npm run build
- Deploy to Cloudflare Pages via wrangler

---

## Phase 2: Fix the Backend

### 2.1 Verify Render Deployment
- Check if render.yaml is correct
- Check if env vars are set on Render
- Manual deploy if needed

### 2.2 Test All Endpoints
- Health, bootstrap, all CRUD endpoints
- Verify with real API calls

---

## Phase 3: Wire Frontend to Backend

### 3.1 Update Frontend API URL
- Point to Render backend URL
- Rebuild and redeploy

### 3.2 E2E Test
- Login with API key
- Submit a document
- View job list
- Check review queue
- View analytics

---

## Technical Decisions

- **No external UI library** — Custom CSS with design tokens (keeps bundle small)
- **Auth via API key** — Simple, no OAuth complexity
- **React Router v6** — Already installed
- **TanStack Query** — Already installed, handles caching/polling
- **Cloudflare Pages** — Frontend hosting (already set up)
- **Render** — Backend hosting (free tier)

---

## Timeline
- Phase 1: ~30 minutes (frontend fix)
- Phase 2: ~10 minutes (backend verification)
- Phase 3: ~10 minutes (wiring + E2E test)
