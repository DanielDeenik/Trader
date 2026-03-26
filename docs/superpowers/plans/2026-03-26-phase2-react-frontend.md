# Phase 2: React SPA Frontend

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a React SPA served as static files from FastAPI that implements the HITL workflow for the Camillo 5-layer topology. Dan walks signals through L1→L2→L3 gates, scoring each layer, then moves promoted theses to L4 decisions and L5 portfolio.

**Architecture:** Vite builds React to static files → copied to `social_arb/static/` → FastAPI serves them with a catch-all route for SPA routing. In development, Vite dev server proxies API calls to FastAPI on :8000. No Node.js in production — only Python + uvicorn.

**Tech Stack:** Vite (build), React 18 (UI), React Router v6 (routing), Tailwind CSS via CDN (styling), Recharts (charts), dark theme only

**Critical Design:** This is NOT a dashboard. It's an interactive workflow tool. Information-dense, Bloomberg-terminal aesthetic. No whitespace, no animations, no decorative elements. Every pixel serves the HITL decision loop.

---

## File Structure

```
frontend/
├── package.json
├── vite.config.js
├── index.html
├── .gitignore
├── src/
│   ├── main.jsx                    # React entry point
│   ├── App.jsx                     # Router + layout shell
│   ├── api.js                      # Fetch wrapper for all API calls
│   ├── hooks/
│   │   ├── useApi.js               # Generic hook: fetch + loading + error + refetch
│   │   └── usePolling.js           # Auto-refresh every N seconds
│   ├── components/
│   │   ├── Layout.jsx              # Sidebar + header + main
│   │   ├── Sidebar.jsx             # Nav links + status indicators
│   │   ├── Header.jsx              # Logo + current view title
│   │   ├── StatusBar.jsx           # Source health: yfinance, reddit, trends, sec
│   │   ├── ScoreSlider.jsx         # 1-5 score input (used in all HITL gates)
│   │   ├── EngineCard.jsx          # Reusable engine output display
│   │   ├── DecisionButton.jsx      # promote|watch|discard|forge|hold|reject
│   │   ├── TickerSearchInput.jsx   # Quick lookup
│   │   └── SymbolLink.jsx          # Clickable symbol → ticker detail
│   ├── pages/
│   │   ├── Overview.jsx            # Landing: signal/mosaic/thesis counts, active tickers
│   │   ├── Tickers.jsx             # Instrument CRUD + search
│   │   ├── TickerDetail.jsx        # Per-symbol deep dive (all 7 engines)
│   │   ├── SignalRadar.jsx         # L1: signals grouped by symbol + freshness
│   │   ├── MosaicCards.jsx         # L2: list of mosaics + L2 gate review
│   │   ├── ThesisForge.jsx         # L3: list of theses + L3 gate review
│   │   ├── GateReview.jsx          # Reusable HITL gate form (L1/L2/L3)
│   │   ├── Decisions.jsx           # L4: decided theses awaiting position sizing
│   │   ├── Positions.jsx           # L5: portfolio tracking
│   │   ├── TaskQueue.jsx           # Monitor collect/analyze tasks + trigger
│   │   └── NotFound.jsx            # 404 page
│   └── styles/
│       └── index.css               # Tailwind + dark theme CSS variables
```

**Modified existing files:**
- `social_arb/api/main.py` — Add static file serving + catch-all SPA route
- `pyproject.toml` — Ensure no frontend deps (Node is external)

**Build output:**
```
social_arb/static/
├── index.html
├── assets/
│   ├── main.HASH.js
│   ├── main.HASH.css
│   └── (chunks)
```

---

## Task 1: Scaffold Vite + React project, build pipeline, FastAPI static serving

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/.gitignore`
- Modify: `social_arb/api/main.py` (add static file serving)
- Create: `build-frontend.sh` (build script)

**Steps:**

- [ ] **Step 1: Create frontend directory structure**

```bash
mkdir -p /sessions/laughing-serene-mendel/mnt/Trader/frontend/src/{components,pages,hooks,styles}
cd /sessions/laughing-serene-mendel/mnt/Trader/frontend
```

- [ ] **Step 2: Create package.json**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/package.json`

```json
{
  "name": "social-arb-frontend",
  "version": "2.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "recharts": "^2.10.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0"
  }
}
```

- [ ] **Step 3: Create vite.config.js**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/vite.config.js`

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../social_arb/static',
    emptyOutDir: true,
    target: 'ES2020',
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 4: Create index.html**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Social Arb — Information Arbitrage</title>
    <link href="https://cdn.tailwindcss.com" rel="stylesheet">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        dark: {
                            50: '#f9fafb',
                            100: '#f3f4f6',
                            200: '#e5e7eb',
                            300: '#d1d5db',
                            400: '#9ca3af',
                            500: '#6b7280',
                            600: '#4b5563',
                            700: '#374151',
                            800: '#1f2937',
                            900: '#111827',
                            950: '#030712',
                        },
                    },
                    spacing: {
                        'sidebar': '256px',
                    },
                },
            },
        }
    </script>
</head>
<body class="dark bg-dark-900 text-dark-50">
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
</body>
</html>
```

- [ ] **Step 5: Create .gitignore**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/.gitignore`

```
node_modules/
dist/
build/
*.log
.DS_Store
.env.local
.env.*.local
```

- [ ] **Step 6: Modify social_arb/api/main.py to serve static files**

In `/sessions/laughing-serene-mendel/mnt/Trader/social_arb/api/main.py`, after the line `app.include_router(stepps.router)`, add:

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# ... rest of imports ...

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    cfg = get_config()

    app = FastAPI(
        title="Social Arb API",
        description="Information Arbitrage Platform — Camillo Cognitive Architecture",
        version="2.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(instruments.router, prefix="/api/v1", tags=["instruments"])
    app.include_router(signals.router, prefix="/api/v1", tags=["signals"])
    app.include_router(mosaics.router, prefix="/api/v1", tags=["mosaics"])
    app.include_router(theses.router, prefix="/api/v1", tags=["theses"])
    app.include_router(reviews.router, prefix="/api/v1", tags=["reviews"])
    app.include_router(positions.router, prefix="/api/v1", tags=["positions"])
    app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
    app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
    app.include_router(stepps.router)

    @app.get("/")
    def root():
        return {"app": "Social Arb", "version": "2.0.0", "docs": "/docs"}

    # Serve static files from social_arb/static
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # SPA catch-all: serve index.html for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve SPA for all non-API routes."""
        # Skip API routes and swagger docs
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("openapi"):
            return {"error": "Not found"}, 404

        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        return {"error": "Frontend not built. Run: npm run build"}, 404

    return app

app = create_app()
```

- [ ] **Step 7: Create build-frontend.sh**

File: `/sessions/laughing-serene-mendel/mnt/Trader/build-frontend.sh`

```bash
#!/bin/bash
set -e

echo "Building React frontend..."
cd /sessions/laughing-serene-mendel/mnt/Trader/frontend

if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

echo "Running Vite build..."
npm run build

echo "✓ Frontend built to social_arb/static/"
```

Make it executable:
```bash
chmod +x /sessions/laughing-serene-mendel/mnt/Trader/build-frontend.sh
```

- [ ] **Step 8: Install frontend dependencies**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader/frontend
npm install
```

Expected: `added N packages`

- [ ] **Step 9: Test Vite build**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader/frontend
npm run build
```

Expected: Output to `social_arb/static/` with `index.html` and `assets/` folder

- [ ] **Step 10: Verify static files exist**

```bash
ls -la /sessions/laughing-serene-mendel/mnt/Trader/social_arb/static/
```

Expected: `index.html`, `assets/` directory

- [ ] **Step 11: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/ build-frontend.sh social_arb/api/main.py
git commit -m "feat: scaffold Vite + React frontend, static file serving from FastAPI"
```

---

## Task 2: API client wrapper and hooks (useApi, usePolling)

**Files:**
- Create: `frontend/src/api.js`
- Create: `frontend/src/hooks/useApi.js`
- Create: `frontend/src/hooks/usePolling.js`
- Create: `frontend/src/hooks/index.js`

**Steps:**

- [ ] **Step 1: Create api.js fetch wrapper**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/api.js`

```javascript
/**
 * API client: fetch wrapper with error handling.
 * Base URL: /api (proxied to :8000 in dev, served from FastAPI in prod)
 */

const API_BASE = '/api'

export class ApiError extends Error {
  constructor(status, message, data) {
    super(message)
    this.status = status
    this.data = data
  }
}

async function handleResponse(res) {
  const data = await res.json()
  if (!res.ok) {
    throw new ApiError(res.status, data.detail || `HTTP ${res.status}`, data)
  }
  return data
}

export const api = {
  // Health
  async getHealth() {
    const res = await fetch(`${API_BASE}/v1/health`)
    return handleResponse(res)
  },

  // Instruments
  async getInstruments(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/instruments?${query}`)
    return handleResponse(res)
  },

  async createInstrument(data) {
    const res = await fetch(`${API_BASE}/v1/instruments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async updateInstrument(id, data) {
    const res = await fetch(`${API_BASE}/v1/instruments/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async deleteInstrument(id) {
    const res = await fetch(`${API_BASE}/v1/instruments/${id}`, {
      method: 'DELETE',
    })
    if (!res.ok) {
      const data = await res.json()
      throw new ApiError(res.status, data.detail || `HTTP ${res.status}`, data)
    }
    return { success: true }
  },

  // Signals
  async getSignals(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/signals?${query}`)
    return handleResponse(res)
  },

  async getSignalsGrouped(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/signals/grouped?${query}`)
    return handleResponse(res)
  },

  // Mosaics
  async getMosaics(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/mosaics?${query}`)
    return handleResponse(res)
  },

  // Theses
  async getTheses(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/theses?${query}`)
    return handleResponse(res)
  },

  // Reviews (HITL)
  async getReviews(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/reviews?${query}`)
    return handleResponse(res)
  },

  async createReview(data) {
    const res = await fetch(`${API_BASE}/v1/reviews`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  // Positions
  async getPositions(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/positions?${query}`)
    return handleResponse(res)
  },

  async createPosition(data) {
    const res = await fetch(`${API_BASE}/v1/positions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  // Analysis
  async analyzeSymbol(symbol, params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/analyze/${symbol}?${query}`, {
      method: 'POST',
    })
    return handleResponse(res)
  },

  async getEngineOutput(symbol) {
    const res = await fetch(`${API_BASE}/v1/engine/${symbol}`)
    return handleResponse(res)
  },

  // Tasks
  async getTasks(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/tasks?${query}`)
    return handleResponse(res)
  },

  async createTask(data) {
    const res = await fetch(`${API_BASE}/v1/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async getTask(id) {
    const res = await fetch(`${API_BASE}/v1/tasks/${id}`)
    return handleResponse(res)
  },

  async deleteTask(id) {
    const res = await fetch(`${API_BASE}/v1/tasks/${id}`, {
      method: 'DELETE',
    })
    if (!res.ok) {
      const data = await res.json()
      throw new ApiError(res.status, data.detail || `HTTP ${res.status}`, data)
    }
    return { success: true }
  },

  async getSourceHealth() {
    const res = await fetch(`${API_BASE}/v1/source-health`)
    return handleResponse(res)
  },

  // STEPPS
  async scoreStepps(data) {
    const res = await fetch(`${API_BASE}/v1/stepps/score`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async getSteppsScores(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/stepps/scores?${query}`)
    return handleResponse(res)
  },

  async correctStepps(data) {
    const res = await fetch(`${API_BASE}/v1/stepps/correct`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },
}
```

- [ ] **Step 2: Create useApi.js hook**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/hooks/useApi.js`

```javascript
import { useState, useEffect, useCallback, useRef } from 'react'
import { ApiError } from '../api'

/**
 * useApi: Fetch data from API with loading, error, and refetch.
 *
 * Usage:
 *   const { data, loading, error, refetch } = useApi(async () => api.getSignals())
 */
export function useApi(asyncFn, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const abortRef = useRef(null)

  const fetch = useCallback(async () => {
    if (abortRef.current) abortRef.current.abort()
    abortRef.current = new AbortController()

    setLoading(true)
    setError(null)
    try {
      const result = await asyncFn()
      setData(result)
      setError(null)
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err instanceof ApiError ? err : new Error(err.message))
      }
      setData(null)
    } finally {
      setLoading(false)
    }
  }, deps)

  useEffect(() => {
    fetch()
    return () => {
      if (abortRef.current) abortRef.current.abort()
    }
  }, [fetch])

  const refetch = useCallback(() => fetch(), [fetch])

  return { data, loading, error, refetch }
}
```

- [ ] **Step 3: Create usePolling.js hook**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/hooks/usePolling.js`

```javascript
import { useState, useEffect, useRef, useCallback } from 'react'
import { useApi } from './useApi'

/**
 * usePolling: Fetch data and auto-refresh at interval.
 *
 * Usage:
 *   const { data, loading, error } = usePolling(async () => api.getSourceHealth(), 5000)
 */
export function usePolling(asyncFn, intervalMs = 5000, deps = []) {
  const { data, loading, error, refetch } = useApi(asyncFn, deps)
  const intervalRef = useRef(null)

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      refetch()
    }, intervalMs)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [intervalMs, refetch])

  return { data, loading, error, refetch }
}
```

- [ ] **Step 4: Create hooks/index.js**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/hooks/index.js`

```javascript
export { useApi } from './useApi'
export { usePolling } from './usePolling'
```

- [ ] **Step 5: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/api.js frontend/src/hooks/
git commit -m "feat: add API client and fetch hooks (useApi, usePolling)"
```

---

## Task 3: Layout shell (Sidebar, Header, StatusBar, main content area)

**Files:**
- Create: `frontend/src/components/Layout.jsx`
- Create: `frontend/src/components/Sidebar.jsx`
- Create: `frontend/src/components/Header.jsx`
- Create: `frontend/src/components/StatusBar.jsx`
- Create: `frontend/src/styles/index.css`

**Steps:**

- [ ] **Step 1: Create Tailwind CSS with dark theme**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/styles/index.css`

```css
@import 'tailwindcss/base';
@import 'tailwindcss/components';
@import 'tailwindcss/utilities';

:root {
  --color-bg-primary: #111827;
  --color-bg-secondary: #1f2937;
  --color-bg-tertiary: #374151;
  --color-text-primary: #f9fafb;
  --color-text-secondary: #d1d5db;
  --color-accent-success: #10b981;
  --color-accent-warning: #f59e0b;
  --color-accent-error: #ef4444;
  --color-accent-info: #3b82f6;
}

body {
  @apply bg-dark-900 text-dark-50 font-mono;
  background-color: var(--color-bg-primary);
  color: var(--color-text-primary);
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--color-bg-secondary);
}

::-webkit-scrollbar-thumb {
  background: var(--color-bg-tertiary);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-secondary);
}

/* Cards & borders */
.card {
  @apply bg-dark-800 border border-dark-700 rounded px-4 py-3;
}

.card-sm {
  @apply bg-dark-800 border border-dark-700 rounded px-2 py-1 text-sm;
}

/* Button reset */
button {
  @apply cursor-pointer transition-colors;
}

button:disabled {
  @apply opacity-50 cursor-not-allowed;
}

/* Input styling */
input, textarea, select {
  @apply bg-dark-800 border border-dark-700 text-dark-50 px-2 py-1 rounded text-sm;
}

input:focus, textarea:focus, select:focus {
  @apply outline-none border-dark-500;
}

/* Link styling */
a {
  @apply text-blue-400 hover:text-blue-300 underline;
}

/* Status indicators */
.status-healthy {
  @apply text-green-400;
}

.status-warning {
  @apply text-yellow-400;
}

.status-error {
  @apply text-red-400;
}

.status-dot {
  @apply inline-block w-2 h-2 rounded-full mr-1;
}

.status-dot.healthy {
  @apply bg-green-400;
}

.status-dot.warning {
  @apply bg-yellow-400;
}

.status-dot.error {
  @apply bg-red-400;
}
```

- [ ] **Step 2: Create Header.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/components/Header.jsx`

```jsx
export function Header({ title }) {
  return (
    <div className="border-b border-dark-700 px-6 py-3 flex items-center justify-between bg-dark-800">
      <h1 className="text-lg font-bold">{title}</h1>
      <div className="text-xs text-dark-400">
        Social Arb v2.0
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create StatusBar.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/components/StatusBar.jsx`

```jsx
import { usePolling } from '../hooks'
import { api } from '../api'

function SourceHealthIndicator({ name, healthy, fresh_at }) {
  const isStale = fresh_at ? Date.now() - new Date(fresh_at).getTime() > 3600000 : false
  const status = healthy ? 'healthy' : isStale ? 'warning' : 'error'

  return (
    <div className="flex items-center text-xs">
      <span className={`status-dot ${status}`} />
      <span className={`status-${status}`}>{name}</span>
    </div>
  )
}

export function StatusBar() {
  const { data: health, error } = usePolling(async () => api.getSourceHealth(), 10000)

  if (error) {
    return (
      <div className="border-t border-dark-700 px-6 py-2 bg-dark-800 text-xs text-red-400">
        Health check failed
      </div>
    )
  }

  if (!health) {
    return (
      <div className="border-t border-dark-700 px-6 py-2 bg-dark-800 text-xs text-dark-500">
        Loading...
      </div>
    )
  }

  return (
    <div className="border-t border-dark-700 px-6 py-2 bg-dark-800">
      <div className="flex gap-6 text-xs">
        {Object.entries(health).map(([source, info]) => (
          <SourceHealthIndicator key={source} name={source} {...info} />
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create Sidebar.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/components/Sidebar.jsx`

```jsx
import { Link, useLocation } from 'react-router-dom'

const navItems = [
  { path: '/', label: 'Overview' },
  { path: '/tickers', label: 'Tickers' },
  { path: '/signals', label: 'L1: Signal Radar' },
  { path: '/mosaics', label: 'L2: Mosaic Cards' },
  { path: '/theses', label: 'L3: Thesis Forge' },
  { path: '/decisions', label: 'L4: Decisions' },
  { path: '/positions', label: 'L5: Portfolio' },
  { path: '/tasks', label: 'Task Queue' },
]

export function Sidebar() {
  const location = useLocation()

  return (
    <div className="w-64 bg-dark-800 border-r border-dark-700 flex flex-col h-screen">
      <div className="px-6 py-4 border-b border-dark-700">
        <h2 className="font-bold text-sm">Social Arb</h2>
        <p className="text-xs text-dark-400 mt-1">Info Arbitrage Platform</p>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-4 space-y-1">
        {navItems.map(({ path, label }) => (
          <Link
            key={path}
            to={path}
            className={`block px-4 py-2 text-xs rounded transition-colors ${
              location.pathname === path
                ? 'bg-dark-700 text-dark-50'
                : 'text-dark-300 hover:bg-dark-700 hover:text-dark-50'
            }`}
          >
            {label}
          </Link>
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-dark-700 text-xs text-dark-400">
        <p>v2.0.0</p>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Create Layout.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/components/Layout.jsx`

```jsx
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { StatusBar } from './StatusBar'

export function Layout({ title, children }) {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header title={title} />
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>
        <StatusBar />
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/components/Layout.jsx frontend/src/components/Sidebar.jsx frontend/src/components/Header.jsx frontend/src/components/StatusBar.jsx frontend/src/styles/index.css
git commit -m "feat: add layout shell with sidebar, header, statusbar"
```

---

## Task 4: React Router setup and App.jsx entry point

**Files:**
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/main.jsx`

**Steps:**

- [ ] **Step 1: Create main.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/main.jsx`

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles/index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 2: Create App.jsx with routing**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/App.jsx`

```jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'

// Pages (lazy loaded)
import Overview from './pages/Overview'
import Tickers from './pages/Tickers'
import TickerDetail from './pages/TickerDetail'
import SignalRadar from './pages/SignalRadar'
import MosaicCards from './pages/MosaicCards'
import ThesisForge from './pages/ThesisForge'
import Decisions from './pages/Decisions'
import Positions from './pages/Positions'
import TaskQueue from './pages/TaskQueue'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout title="Overview"><Overview /></Layout>} path="/" />
        <Route element={<Layout title="Tickers"><Tickers /></Layout>} path="/tickers" />
        <Route element={<Layout title="Ticker Detail"><TickerDetail /></Layout>} path="/tickers/:symbol" />
        <Route element={<Layout title="L1: Signal Radar"><SignalRadar /></Layout>} path="/signals" />
        <Route element={<Layout title="L2: Mosaic Cards"><MosaicCards /></Layout>} path="/mosaics" />
        <Route element={<Layout title="L3: Thesis Forge"><ThesisForge /></Layout>} path="/theses" />
        <Route element={<Layout title="L4: Decisions"><Decisions /></Layout>} path="/decisions" />
        <Route element={<Layout title="L5: Portfolio"><Positions /></Layout>} path="/positions" />
        <Route element={<Layout title="Task Queue"><TaskQueue /></Layout>} path="/tasks" />
        <Route element={<NotFound />} path="*" />
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 3: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/main.jsx frontend/src/App.jsx
git commit -m "feat: add React Router and App entry point"
```

---

## Task 5: Reusable components (ScoreSlider, EngineCard, DecisionButton, TickerSearchInput)

**Files:**
- Create: `frontend/src/components/ScoreSlider.jsx`
- Create: `frontend/src/components/EngineCard.jsx`
- Create: `frontend/src/components/DecisionButton.jsx`
- Create: `frontend/src/components/TickerSearchInput.jsx`
- Create: `frontend/src/components/SymbolLink.jsx`

**Steps:**

- [ ] **Step 1: Create ScoreSlider.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/components/ScoreSlider.jsx`

```jsx
/**
 * ScoreSlider: Input for 1-5 scoring in HITL gates.
 *
 * Usage:
 *   <ScoreSlider criterion="signal_quality" score={score} onScore={setScore} />
 */
export function ScoreSlider({ criterion, score, onScore, max = 5 }) {
  return (
    <div className="flex items-center gap-4 py-2">
      <label className="text-xs font-mono w-32">{criterion}</label>
      <input
        type="range"
        min="0"
        max={max}
        value={score || 0}
        onChange={(e) => onScore(parseInt(e.target.value))}
        className="flex-1 h-2 bg-dark-700 rounded appearance-none cursor-pointer"
      />
      <div className="w-8 text-right font-mono text-xs">
        {score || 0}/{max}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create EngineCard.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/components/EngineCard.jsx`

```jsx
/**
 * EngineCard: Display output from any engine.
 *
 * Usage:
 *   <EngineCard name="Sentiment Divergence" data={engineOutput} />
 */
export function EngineCard({ name, data, error = null }) {
  if (error) {
    return (
      <div className="card">
        <div className="text-xs font-bold">{name}</div>
        <div className="text-xs text-red-400 mt-2">Error: {error}</div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="card">
        <div className="text-xs font-bold">{name}</div>
        <div className="text-xs text-dark-400 mt-2">No data</div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="text-xs font-bold mb-2">{name}</div>
      <pre className="text-xs overflow-x-auto bg-dark-900 p-2 rounded border border-dark-700">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}
```

- [ ] **Step 3: Create DecisionButton.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/components/DecisionButton.jsx`

```jsx
/**
 * DecisionButton: Gate decisions (promote, watch, discard, forge, hold, reject, execute, defer).
 *
 * Usage:
 *   <DecisionButton decision={decision} onDecision={setDecision} />
 */
const decisions = [
  { value: 'promote', label: 'Promote', color: 'green' },
  { value: 'watch', label: 'Watch', color: 'yellow' },
  { value: 'discard', label: 'Discard', color: 'red' },
  { value: 'forge', label: 'Forge', color: 'blue' },
  { value: 'hold', label: 'Hold', color: 'gray' },
  { value: 'reject', label: 'Reject', color: 'red' },
  { value: 'execute', label: 'Execute', color: 'green' },
  { value: 'defer', label: 'Defer', color: 'yellow' },
]

const colorMap = {
  green: 'bg-green-900 text-green-400 border-green-700 hover:bg-green-800',
  yellow: 'bg-yellow-900 text-yellow-400 border-yellow-700 hover:bg-yellow-800',
  red: 'bg-red-900 text-red-400 border-red-700 hover:bg-red-800',
  blue: 'bg-blue-900 text-blue-400 border-blue-700 hover:bg-blue-800',
  gray: 'bg-dark-700 text-dark-300 border-dark-600 hover:bg-dark-600',
}

export function DecisionButton({ decision, onDecision, gate = null }) {
  // Filter decisions based on gate
  let availableDecisions = decisions
  if (gate === 'L1_triage') {
    availableDecisions = decisions.filter(d => ['promote', 'watch', 'discard'].includes(d.value))
  } else if (gate === 'L2_validation') {
    availableDecisions = decisions.filter(d => ['promote', 'watch', 'discard', 'forge'].includes(d.value))
  } else if (gate === 'L3_conviction') {
    availableDecisions = decisions.filter(d => ['forge', 'hold', 'reject'].includes(d.value))
  }

  return (
    <div className="flex gap-2 flex-wrap">
      {availableDecisions.map(({ value, label, color }) => (
        <button
          key={value}
          onClick={() => onDecision(value)}
          className={`px-3 py-1 text-xs border rounded transition-colors ${
            decision === value
              ? colorMap[color]
              : 'bg-dark-800 text-dark-300 border-dark-700 hover:border-dark-500'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Create TickerSearchInput.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/components/TickerSearchInput.jsx`

```jsx
import { useState } from 'react'

/**
 * TickerSearchInput: Quick ticker search with dropdown.
 *
 * Usage:
 *   <TickerSearchInput onSelect={(symbol) => navigate(`/tickers/${symbol}`)} />
 */
export function TickerSearchInput({ instruments = [], onSelect }) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)

  const filtered = instruments.filter(
    (i) => i.symbol.toUpperCase().includes(query.toUpperCase()) ||
           i.name.toUpperCase().includes(query.toUpperCase())
  )

  const handleSelect = (symbol) => {
    setQuery('')
    setOpen(false)
    onSelect(symbol)
  }

  return (
    <div className="relative">
      <input
        type="text"
        placeholder="Search ticker..."
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 200)}
        className="w-64 text-xs"
      />
      {open && filtered.length > 0 && (
        <div className="absolute top-full left-0 w-full bg-dark-700 border border-dark-600 rounded mt-1 max-h-48 overflow-y-auto z-10">
          {filtered.slice(0, 10).map((i) => (
            <button
              key={i.id}
              onMouseDown={() => handleSelect(i.symbol)}
              className="block w-full text-left px-3 py-1 text-xs hover:bg-dark-600 border-b border-dark-600 last:border-0"
            >
              <span className="font-mono">{i.symbol}</span> — {i.name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Create SymbolLink.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/components/SymbolLink.jsx`

```jsx
import { Link } from 'react-router-dom'

/**
 * SymbolLink: Link to ticker detail page.
 *
 * Usage:
 *   <SymbolLink symbol="NVDA" name="NVIDIA" />
 */
export function SymbolLink({ symbol, name = null }) {
  return (
    <Link
      to={`/tickers/${symbol}`}
      className="font-mono hover:text-blue-300"
    >
      {symbol}
      {name && <span className="text-dark-400 ml-2">{name}</span>}
    </Link>
  )
}
```

- [ ] **Step 6: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/components/{ScoreSlider,EngineCard,DecisionButton,TickerSearchInput,SymbolLink}.jsx
git commit -m "feat: add reusable UI components (Score, Engine, Decision, Search)"
```

---

## Task 6: Overview page

**Files:**
- Create: `frontend/src/pages/Overview.jsx`

**Steps:**

- [ ] **Step 1: Create Overview.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/pages/Overview.jsx`

```jsx
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function Overview() {
  const { data: instruments } = useApi(async () => api.getInstruments())
  const { data: signals } = useApi(async () => api.getSignals())
  const { data: mosaics } = useApi(async () => api.getMosaics())
  const { data: theses } = useApi(async () => api.getTheses())
  const { data: positions } = useApi(async () => api.getPositions())
  const { data: reviews } = useApi(async () => api.getReviews())

  const activeSymbols = new Set((instruments || []).map(i => i.symbol))
  const signalCount = (signals || []).length
  const mosaicCount = (mosaics || []).length
  const thesisCount = (theses || []).length
  const positionCount = (positions || []).length
  const reviewCount = (reviews || []).length

  return (
    <div className="space-y-6">
      {/* Metrics grid */}
      <div className="grid grid-cols-2 gap-4">
        <div className="card">
          <div className="text-xs text-dark-400">Active Tickers</div>
          <div className="text-2xl font-bold mt-1">{activeSymbols.size}</div>
        </div>
        <div className="card">
          <div className="text-xs text-dark-400">L1 Signals</div>
          <div className="text-2xl font-bold mt-1">{signalCount}</div>
        </div>
        <div className="card">
          <div className="text-xs text-dark-400">L2 Mosaics</div>
          <div className="text-2xl font-bold mt-1">{mosaicCount}</div>
        </div>
        <div className="card">
          <div className="text-xs text-dark-400">L3 Theses</div>
          <div className="text-2xl font-bold mt-1">{thesisCount}</div>
        </div>
        <div className="card">
          <div className="text-xs text-dark-400">L4 Decisions</div>
          <div className="text-2xl font-bold mt-1">—</div>
        </div>
        <div className="card">
          <div className="text-xs text-dark-400">L5 Positions</div>
          <div className="text-2xl font-bold mt-1">{positionCount}</div>
        </div>
      </div>

      {/* Active tickers */}
      {activeSymbols.size > 0 && (
        <div className="card">
          <div className="text-xs font-bold mb-3">Active Symbols</div>
          <div className="flex flex-wrap gap-2">
            {Array.from(activeSymbols).slice(0, 20).map((symbol) => (
              <SymbolLink key={symbol} symbol={symbol} />
            ))}
          </div>
        </div>
      )}

      {/* Latest reviews */}
      {(reviews || []).length > 0 && (
        <div className="card">
          <div className="text-xs font-bold mb-3">Recent Reviews</div>
          <div className="space-y-2 text-xs">
            {(reviews || []).slice(0, 5).map((r) => (
              <div key={r.id} className="flex justify-between border-b border-dark-700 pb-1">
                <span>{r.gate} — {r.symbol}</span>
                <span className="text-dark-400">{r.decision}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick help */}
      <div className="card bg-dark-900 border-dark-600">
        <div className="text-xs text-dark-400">
          <p className="mb-2">Start by:</p>
          <ol className="list-decimal list-inside space-y-1 text-dark-400">
            <li>Add tickers in <a href="/tickers">Tickers</a></li>
            <li>Trigger collection in <a href="/tasks">Task Queue</a></li>
            <li>Review signals in <a href="/signals">L1: Signal Radar</a></li>
            <li>Walk through L2 → L3 → L5</li>
          </ol>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/pages/Overview.jsx
git commit -m "feat: add Overview page with metrics and quick help"
```

---

## Task 7: Tickers CRUD page

**Files:**
- Create: `frontend/src/pages/Tickers.jsx`

**Steps:**

- [ ] **Step 1: Create Tickers.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/pages/Tickers.jsx`

```jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks'
import { api, ApiError } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function Tickers() {
  const navigate = useNavigate()
  const { data: instruments, refetch } = useApi(async () => api.getInstruments())
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    symbol: '',
    name: '',
    type: 'stock',
    data_class: 'public',
  })
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleAddInstrument = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await api.createInstrument(formData)
      setFormData({ symbol: '', name: '', type: 'stock', data_class: 'public' })
      setShowForm(false)
      refetch()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteInstrument = async (id) => {
    if (confirm('Delete this instrument?')) {
      try {
        await api.deleteInstrument(id)
        refetch()
      } catch (err) {
        setError(err instanceof ApiError ? err.message : err.message)
      }
    }
  }

  return (
    <div className="space-y-4">
      {/* Add form */}
      {showForm && (
        <form onSubmit={handleAddInstrument} className="card space-y-3">
          <div>
            <label className="text-xs block mb-1">Symbol</label>
            <input
              type="text"
              name="symbol"
              value={formData.symbol}
              onChange={handleInputChange}
              placeholder="NVDA"
              required
            />
          </div>
          <div>
            <label className="text-xs block mb-1">Name</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              placeholder="NVIDIA Corporation"
            />
          </div>
          <div>
            <label className="text-xs block mb-1">Type</label>
            <select name="type" value={formData.type} onChange={handleInputChange}>
              <option value="stock">Stock</option>
              <option value="etf">ETF</option>
              <option value="crypto">Crypto</option>
            </select>
          </div>
          <div>
            <label className="text-xs block mb-1">Data Class</label>
            <select name="data_class" value={formData.data_class} onChange={handleInputChange}>
              <option value="public">Public</option>
              <option value="private">Private</option>
            </select>
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="px-3 py-1 bg-green-900 text-green-400 border border-green-700 text-xs rounded"
            >
              {loading ? 'Adding...' : 'Add'}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-3 py-1 bg-dark-700 text-dark-300 border border-dark-600 text-xs rounded"
            >
              Cancel
            </button>
          </div>
          {error && <div className="text-xs text-red-400">{error}</div>}
        </form>
      )}

      {!showForm && (
        <button
          onClick={() => setShowForm(true)}
          className="px-3 py-1 bg-blue-900 text-blue-400 border border-blue-700 text-xs rounded"
        >
          + Add Ticker
        </button>
      )}

      {/* Table */}
      <div className="card overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-dark-700">
              <th className="text-left py-2 px-2">Symbol</th>
              <th className="text-left py-2 px-2">Name</th>
              <th className="text-left py-2 px-2">Type</th>
              <th className="text-left py-2 px-2">Class</th>
              <th className="text-right py-2 px-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(instruments || []).map((inst) => (
              <tr key={inst.id} className="border-b border-dark-700 hover:bg-dark-700">
                <td className="py-2 px-2">
                  <SymbolLink symbol={inst.symbol} name={inst.name} />
                </td>
                <td className="py-2 px-2 text-dark-400">{inst.name}</td>
                <td className="py-2 px-2 text-dark-400">{inst.type}</td>
                <td className="py-2 px-2 text-dark-400">{inst.data_class}</td>
                <td className="py-2 px-2 text-right">
                  <button
                    onClick={() => handleDeleteInstrument(inst.id)}
                    className="text-red-400 hover:text-red-300 text-xs"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!instruments || instruments.length === 0) && (
          <div className="p-4 text-center text-dark-400 text-xs">
            No tickers. Click "+ Add Ticker" to get started.
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/pages/Tickers.jsx
git commit -m "feat: add Tickers CRUD page"
```

---

## Task 8: Ticker Detail page (deep dive with all 7 engines)

**Files:**
- Create: `frontend/src/pages/TickerDetail.jsx`

**Steps:**

- [ ] **Step 1: Create TickerDetail.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/pages/TickerDetail.jsx`

```jsx
import { useParams } from 'react-router-dom'
import { useApi } from '../hooks'
import { api } from '../api'
import { EngineCard } from '../components/EngineCard'

const engineNames = [
  'sentiment_divergence',
  'kelly_sizer',
  'irr_simulator',
  'regulatory_moat',
  'technical_analyzer',
  'cross_domain_amplifier',
]

export default function TickerDetail() {
  const { symbol } = useParams()
  const { data: engines, loading, error } = useApi(
    async () => api.getEngineOutput(symbol),
    [symbol]
  )

  if (loading) return <div className="text-dark-400">Loading...</div>
  if (error) return <div className="text-red-400">Error: {error.message}</div>

  return (
    <div className="space-y-4">
      <div className="text-sm text-dark-400">
        Symbol: <span className="font-mono font-bold text-dark-50">{symbol}</span>
      </div>

      {/* All engine outputs */}
      <div className="grid grid-cols-1 gap-4">
        {engineNames.map((name) => (
          <EngineCard
            key={name}
            name={name.replace(/_/g, ' ').toUpperCase()}
            data={engines?.[name]}
          />
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/pages/TickerDetail.jsx
git commit -m "feat: add Ticker Detail page with all 7 engine outputs"
```

---

## Task 9: Signal Radar (L1)

**Files:**
- Create: `frontend/src/pages/SignalRadar.jsx`

**Steps:**

- [ ] **Step 1: Create SignalRadar.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/pages/SignalRadar.jsx`

```jsx
import { useState } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function SignalRadar() {
  const { data: grouped, refetch } = useApi(async () => api.getSignalsGrouped())
  const [selectedSymbol, setSelectedSymbol] = useState(null)

  const getSourceColor = (source) => {
    const colors = {
      yfinance: 'text-blue-400',
      reddit: 'text-purple-400',
      sec_edgar: 'text-orange-400',
      google_trends: 'text-green-400',
      github: 'text-gray-400',
      coingecko: 'text-yellow-400',
      defillama: 'text-cyan-400',
    }
    return colors[source] || 'text-dark-300'
  }

  const formatAge = (timestamp) => {
    const mins = Math.floor((Date.now() - new Date(timestamp).getTime()) / 60000)
    if (mins < 60) return `${mins}m`
    if (mins < 1440) return `${Math.floor(mins / 60)}h`
    return `${Math.floor(mins / 1440)}d`
  }

  return (
    <div className="space-y-4">
      {/* Refresh button */}
      <div>
        <button
          onClick={() => refetch()}
          className="px-3 py-1 bg-blue-900 text-blue-400 border border-blue-700 text-xs rounded"
        >
          Refresh
        </button>
      </div>

      {/* Grouped signals by symbol */}
      {grouped && Object.entries(grouped).map(([symbol, signals]) => (
        <div key={symbol} className="card">
          <div
            className="flex justify-between items-center cursor-pointer hover:bg-dark-700 p-2 -m-2 rounded"
            onClick={() => setSelectedSymbol(selectedSymbol === symbol ? null : symbol)}
          >
            <SymbolLink symbol={symbol} />
            <div className="text-xs text-dark-400">
              {signals.length} signal{signals.length !== 1 ? 's' : ''}
            </div>
          </div>

          {selectedSymbol === symbol && (
            <div className="mt-3 space-y-2 border-t border-dark-700 pt-3">
              {signals.map((sig) => (
                <div key={sig.id} className="text-xs bg-dark-900 p-2 rounded border border-dark-700">
                  <div className="flex justify-between mb-1">
                    <span className={`font-mono ${getSourceColor(sig.source)}`}>
                      {sig.source}
                    </span>
                    <span className="text-dark-400">{formatAge(sig.created_at)}</span>
                  </div>
                  <div className="text-dark-300 mb-1">{sig.signal_text}</div>
                  <div className="text-dark-500 text-xs">
                    Strength: {sig.strength || '?'}/10
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}

      {!grouped && (
        <div className="text-dark-400 text-xs">No signals yet.</div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/pages/SignalRadar.jsx
git commit -m "feat: add Signal Radar page (L1)"
```

---

## Task 10: Mosaic Cards (L2)

**Files:**
- Create: `frontend/src/pages/MosaicCards.jsx`

**Steps:**

- [ ] **Step 1: Create MosaicCards.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/pages/MosaicCards.jsx`

```jsx
import { useState } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function MosaicCards() {
  const { data: mosaics, refetch } = useApi(async () => api.getMosaics())
  const [expandedId, setExpandedId] = useState(null)

  return (
    <div className="space-y-4">
      <div>
        <button
          onClick={() => refetch()}
          className="px-3 py-1 bg-blue-900 text-blue-400 border border-blue-700 text-xs rounded"
        >
          Refresh
        </button>
      </div>

      {(mosaics || []).map((mosaic) => (
        <div key={mosaic.id} className="card">
          <div
            className="flex justify-between items-center cursor-pointer hover:bg-dark-700 p-2 -m-2 rounded"
            onClick={() => setExpandedId(expandedId === mosaic.id ? null : mosaic.id)}
          >
            <div>
              <SymbolLink symbol={mosaic.symbol} />
              <div className="text-xs text-dark-400 mt-1">
                {mosaic.signal_count || 0} signals
              </div>
            </div>
            <div className="text-xs text-dark-400">
              Created: {new Date(mosaic.created_at).toLocaleDateString()}
            </div>
          </div>

          {expandedId === mosaic.id && (
            <div className="mt-3 border-t border-dark-700 pt-3 text-xs space-y-2">
              <div>
                <div className="text-dark-400 mb-1">Narrative:</div>
                <div className="bg-dark-900 p-2 rounded">{mosaic.narrative}</div>
              </div>
              {mosaic.signal_ids && (
                <div>
                  <div className="text-dark-400 mb-1">Signal IDs:</div>
                  <div className="text-dark-300">{mosaic.signal_ids.join(', ')}</div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}

      {(!mosaics || mosaics.length === 0) && (
        <div className="text-dark-400 text-xs">No mosaics yet.</div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/pages/MosaicCards.jsx
git commit -m "feat: add Mosaic Cards page (L2)"
```

---

## Task 11: Thesis Forge (L3)

**Files:**
- Create: `frontend/src/pages/ThesisForge.jsx`

**Steps:**

- [ ] **Step 1: Create ThesisForge.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/pages/ThesisForge.jsx`

```jsx
import { useState } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function ThesisForge() {
  const { data: theses, refetch } = useApi(async () => api.getTheses())
  const [expandedId, setExpandedId] = useState(null)

  return (
    <div className="space-y-4">
      <div>
        <button
          onClick={() => refetch()}
          className="px-3 py-1 bg-blue-900 text-blue-400 border border-blue-700 text-xs rounded"
        >
          Refresh
        </button>
      </div>

      {(theses || []).map((thesis) => (
        <div key={thesis.id} className="card">
          <div
            className="flex justify-between items-center cursor-pointer hover:bg-dark-700 p-2 -m-2 rounded"
            onClick={() => setExpandedId(expandedId === thesis.id ? null : thesis.id)}
          >
            <div>
              <SymbolLink symbol={thesis.symbol} />
              <div className="text-xs text-dark-400 mt-1">
                {thesis.mosaic_count || 0} mosaics
              </div>
            </div>
            <div className="text-xs text-dark-400">
              {new Date(thesis.created_at).toLocaleDateString()}
            </div>
          </div>

          {expandedId === thesis.id && (
            <div className="mt-3 border-t border-dark-700 pt-3 text-xs space-y-2">
              <div>
                <div className="text-dark-400 mb-1">Narrative:</div>
                <div className="bg-dark-900 p-2 rounded">{thesis.narrative}</div>
              </div>
              {thesis.invalidation_triggers && (
                <div>
                  <div className="text-dark-400 mb-1">Invalidation:</div>
                  <div className="bg-dark-900 p-2 rounded">{thesis.invalidation_triggers}</div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}

      {(!theses || theses.length === 0) && (
        <div className="text-dark-400 text-xs">No theses yet.</div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/pages/ThesisForge.jsx
git commit -m "feat: add Thesis Forge page (L3)"
```

---

## Task 12: HITL Gate Review page (L1/L2/L3 scoring)

**Files:**
- Create: `frontend/src/pages/GateReview.jsx`

**Steps:**

- [ ] **Step 1: Create GateReview.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/pages/GateReview.jsx`

```jsx
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApi } from '../hooks'
import { api, ApiError } from '../api'
import { ScoreSlider } from '../components/ScoreSlider'
import { DecisionButton } from '../components/DecisionButton'
import { SymbolLink } from '../components/SymbolLink'

const gateCriteria = {
  L1_triage: {
    label: 'L1: Signal Triage',
    criteria: ['signal_quality', 'source_diversity', 'timing', 'novelty'],
    threshold: 12,
    maxScore: 20,
  },
  L2_validation: {
    label: 'L2: Mosaic Validation',
    criteria: ['coherence', 'divergence_strength', 'multi_domain', 'data_freshness'],
    threshold: 12,
    maxScore: 20,
  },
  L3_conviction: {
    label: 'L3: Thesis Conviction',
    criteria: ['thesis_clarity', 'risk_reward', 'market_timing', 'catalyst_strength', 'invalidation_clarity'],
    threshold: 15,
    maxScore: 25,
  },
}

export default function GateReview() {
  const [searchParams] = useSearchParams()
  const gate = searchParams.get('gate') || 'L1_triage'
  const symbol = searchParams.get('symbol')
  const entityId = searchParams.get('entity_id')
  const entityType = searchParams.get('entity_type') || 'signal'

  const gateConfig = gateCriteria[gate]
  const [scores, setScores] = useState({})
  const [decision, setDecision] = useState(null)
  const [narratives, setNarratives] = useState({
    dominant_narrative: '',
    market_pricing: '',
    invalidation: '',
    position_size: '',
    risk_note: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const totalScore = gateConfig.criteria.reduce((sum, crit) => sum + (scores[crit] || 0), 0)
  const isPassing = totalScore >= gateConfig.threshold

  const handleScoreChange = (criterion, value) => {
    setScores(prev => ({ ...prev, [criterion]: value }))
  }

  const handleNarrativeChange = (field, value) => {
    setNarratives(prev => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!decision) {
      setError('Please select a decision')
      return
    }

    setSubmitting(true)
    setError(null)

    try {
      await api.createReview({
        gate,
        symbol,
        entity_id: entityId,
        entity_type: entityType,
        scores,
        decision,
        ...narratives,
      })
      setSuccess(true)
      setTimeout(() => {
        setSuccess(false)
        setScores({})
        setDecision(null)
        setNarratives({
          dominant_narrative: '',
          market_pricing: '',
          invalidation: '',
          position_size: '',
          risk_note: '',
        })
      }, 2000)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-4">
      <div className="text-sm text-dark-400">
        {gateConfig.label} {symbol && `→ ${symbol}`}
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Scoring section */}
        <div className="card">
          <div className="text-xs font-bold mb-4">
            Scoring ({totalScore}/{gateConfig.maxScore})
            {isPassing && <span className="text-green-400 ml-2">✓ Passing</span>}
            {!isPassing && <span className="text-red-400 ml-2">✗ Below threshold ({gateConfig.threshold})</span>}
          </div>

          <div className="space-y-3">
            {gateConfig.criteria.map(crit => (
              <ScoreSlider
                key={crit}
                criterion={crit}
                score={scores[crit] || 0}
                onScore={(val) => handleScoreChange(crit, val)}
                max={5}
              />
            ))}
          </div>
        </div>

        {/* Decision section */}
        <div className="card">
          <div className="text-xs font-bold mb-3">Decision</div>
          <DecisionButton
            decision={decision}
            onDecision={setDecision}
            gate={gate}
          />
        </div>

        {/* Narrative fields */}
        <div className="card space-y-3">
          <div className="text-xs font-bold">Narratives (optional)</div>

          <div>
            <label className="text-xs block mb-1">Dominant Narrative</label>
            <textarea
              value={narratives.dominant_narrative}
              onChange={(e) => handleNarrativeChange('dominant_narrative', e.target.value)}
              placeholder="Main storyline driving this decision..."
              className="w-full h-16"
            />
          </div>

          <div>
            <label className="text-xs block mb-1">Market Pricing</label>
            <textarea
              value={narratives.market_pricing}
              onChange={(e) => handleNarrativeChange('market_pricing', e.target.value)}
              placeholder="How does market price this signal?"
              className="w-full h-12"
            />
          </div>

          <div>
            <label className="text-xs block mb-1">Invalidation Triggers</label>
            <textarea
              value={narratives.invalidation}
              onChange={(e) => handleNarrativeChange('invalidation', e.target.value)}
              placeholder="What would prove this wrong?"
              className="w-full h-12"
            />
          </div>

          <div>
            <label className="text-xs block mb-1">Position Size (if executing)</label>
            <input
              type="text"
              value={narratives.position_size}
              onChange={(e) => handleNarrativeChange('position_size', e.target.value)}
              placeholder="e.g., 2% portfolio"
            />
          </div>

          <div>
            <label className="text-xs block mb-1">Risk Note</label>
            <textarea
              value={narratives.risk_note}
              onChange={(e) => handleNarrativeChange('risk_note', e.target.value)}
              placeholder="Key risks to monitor"
              className="w-full h-12"
            />
          </div>
        </div>

        {/* Submit */}
        {error && <div className="text-xs text-red-400">{error}</div>}
        {success && <div className="text-xs text-green-400">✓ Review submitted</div>}

        <button
          type="submit"
          disabled={submitting || !decision}
          className="w-full px-4 py-2 bg-blue-900 text-blue-400 border border-blue-700 text-xs rounded disabled:opacity-50"
        >
          {submitting ? 'Submitting...' : 'Submit Review'}
        </button>
      </form>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/pages/GateReview.jsx
git commit -m "feat: add HITL Gate Review page with scoring and narratives"
```

---

## Task 13: Decisions page (L4)

**Files:**
- Create: `frontend/src/pages/Decisions.jsx`

**Steps:**

- [ ] **Step 1: Create Decisions.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/pages/Decisions.jsx`

```jsx
import { useState } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function Decisions() {
  const { data: theses, refetch } = useApi(async () => api.getTheses())
  const { data: reviews } = useApi(async () => api.getReviews({ gate: 'L3_conviction' }))
  const [expandedId, setExpandedId] = useState(null)

  // Filter theses that have been promoted through L3
  const decidedTheses = (theses || []).filter(t => {
    const review = (reviews || []).find(r => r.entity_id === t.id && r.decision === 'forge')
    return !!review
  })

  return (
    <div className="space-y-4">
      <div className="text-xs text-dark-400">
        Theses approved for L4 execution review
      </div>

      {decidedTheses.length === 0 && (
        <div className="card text-dark-400 text-xs">
          No decisions yet. Promote theses through L3 conviction gate.
        </div>
      )}

      {decidedTheses.map((thesis) => (
        <div key={thesis.id} className="card">
          <div
            className="flex justify-between items-center cursor-pointer hover:bg-dark-700 p-2 -m-2 rounded"
            onClick={() => setExpandedId(expandedId === thesis.id ? null : thesis.id)}
          >
            <SymbolLink symbol={thesis.symbol} />
            <div className="text-xs text-dark-400">
              {new Date(thesis.created_at).toLocaleDateString()}
            </div>
          </div>

          {expandedId === thesis.id && (
            <div className="mt-3 border-t border-dark-700 pt-3 text-xs space-y-2">
              <div className="bg-dark-900 p-2 rounded">{thesis.narrative}</div>
              <div className="flex gap-2">
                <button className="px-3 py-1 bg-green-900 text-green-400 border border-green-700 rounded text-xs">
                  Execute
                </button>
                <button className="px-3 py-1 bg-yellow-900 text-yellow-400 border border-yellow-700 rounded text-xs">
                  Hold
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/pages/Decisions.jsx
git commit -m "feat: add Decisions page (L4)"
```

---

## Task 14: Positions page (L5)

**Files:**
- Create: `frontend/src/pages/Positions.jsx`

**Steps:**

- [ ] **Step 1: Create Positions.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/pages/Positions.jsx`

```jsx
import { useState } from 'react'
import { useApi } from '../hooks'
import { api, ApiError } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function Positions() {
  const { data: positions, refetch } = useApi(async () => api.getPositions())
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    symbol: '',
    entry_price: '',
    size: '',
    stop_loss: '',
    take_profit: '',
    thesis_id: '',
  })
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleAddPosition = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await api.createPosition({
        symbol: formData.symbol,
        entry_price: parseFloat(formData.entry_price),
        size: parseFloat(formData.size),
        stop_loss: formData.stop_loss ? parseFloat(formData.stop_loss) : null,
        take_profit: formData.take_profit ? parseFloat(formData.take_profit) : null,
        thesis_id: formData.thesis_id || null,
      })
      setFormData({ symbol: '', entry_price: '', size: '', stop_loss: '', take_profit: '', thesis_id: '' })
      setShowForm(false)
      refetch()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : err.message)
    } finally {
      setLoading(false)
    }
  }

  const totalPnL = (positions || []).reduce((sum, p) => {
    const pnl = (p.current_price - p.entry_price) * p.size
    return sum + pnl
  }, 0)

  const totalValue = (positions || []).reduce((sum, p) => sum + (p.current_price * p.size), 0)

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-2 gap-4">
        <div className="card">
          <div className="text-xs text-dark-400">Total P&L</div>
          <div className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            ${totalPnL.toFixed(0)}
          </div>
        </div>
        <div className="card">
          <div className="text-xs text-dark-400">Portfolio Value</div>
          <div className="text-2xl font-bold">${totalValue.toFixed(0)}</div>
        </div>
      </div>

      {/* Add form */}
      {showForm && (
        <form onSubmit={handleAddPosition} className="card space-y-3">
          <div>
            <label className="text-xs block mb-1">Symbol</label>
            <input
              type="text"
              name="symbol"
              value={formData.symbol}
              onChange={handleInputChange}
              placeholder="NVDA"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs block mb-1">Entry Price</label>
              <input
                type="number"
                name="entry_price"
                value={formData.entry_price}
                onChange={handleInputChange}
                placeholder="100.00"
                step="0.01"
                required
              />
            </div>
            <div>
              <label className="text-xs block mb-1">Size</label>
              <input
                type="number"
                name="size"
                value={formData.size}
                onChange={handleInputChange}
                placeholder="100"
                step="0.1"
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs block mb-1">Stop Loss</label>
              <input
                type="number"
                name="stop_loss"
                value={formData.stop_loss}
                onChange={handleInputChange}
                placeholder="90.00"
                step="0.01"
              />
            </div>
            <div>
              <label className="text-xs block mb-1">Take Profit</label>
              <input
                type="number"
                name="take_profit"
                value={formData.take_profit}
                onChange={handleInputChange}
                placeholder="120.00"
                step="0.01"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="px-3 py-1 bg-green-900 text-green-400 border border-green-700 text-xs rounded"
            >
              {loading ? 'Adding...' : 'Add Position'}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-3 py-1 bg-dark-700 text-dark-300 border border-dark-600 text-xs rounded"
            >
              Cancel
            </button>
          </div>
          {error && <div className="text-xs text-red-400">{error}</div>}
        </form>
      )}

      {!showForm && (
        <button
          onClick={() => setShowForm(true)}
          className="px-3 py-1 bg-blue-900 text-blue-400 border border-blue-700 text-xs rounded"
        >
          + Add Position
        </button>
      )}

      {/* Positions table */}
      <div className="card overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-dark-700">
              <th className="text-left py-2 px-2">Symbol</th>
              <th className="text-right py-2 px-2">Entry</th>
              <th className="text-right py-2 px-2">Current</th>
              <th className="text-right py-2 px-2">Size</th>
              <th className="text-right py-2 px-2">P&L</th>
              <th className="text-right py-2 px-2">% Return</th>
            </tr>
          </thead>
          <tbody>
            {(positions || []).map((pos) => {
              const pnl = (pos.current_price - pos.entry_price) * pos.size
              const returnPct = ((pos.current_price - pos.entry_price) / pos.entry_price * 100).toFixed(1)
              return (
                <tr key={pos.id} className="border-b border-dark-700 hover:bg-dark-700">
                  <td className="py-2 px-2">
                    <SymbolLink symbol={pos.symbol} />
                  </td>
                  <td className="py-2 px-2 text-right">${pos.entry_price.toFixed(2)}</td>
                  <td className="py-2 px-2 text-right">${pos.current_price.toFixed(2)}</td>
                  <td className="py-2 px-2 text-right">{pos.size}</td>
                  <td className={`py-2 px-2 text-right ${pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    ${pnl.toFixed(0)}
                  </td>
                  <td className={`py-2 px-2 text-right ${returnPct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {returnPct}%
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {(!positions || positions.length === 0) && (
          <div className="p-4 text-center text-dark-400 text-xs">
            No positions. Click "+ Add Position" to get started.
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/pages/Positions.jsx
git commit -m "feat: add Positions page (L5) with P&L tracking"
```

---

## Task 15: Task Queue page

**Files:**
- Create: `frontend/src/pages/TaskQueue.jsx`

**Steps:**

- [ ] **Step 1: Create TaskQueue.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/pages/TaskQueue.jsx`

```jsx
import { useState } from 'react'
import { usePolling } from '../hooks'
import { api } from '../api'

export default function TaskQueue() {
  const { data: tasks, refetch } = usePolling(async () => api.getTasks(), 3000)
  const [triggerLoading, setTriggerLoading] = useState(false)

  const handleTriggerCollect = async (source) => {
    setTriggerLoading(true)
    try {
      await api.createTask({
        type: 'collect',
        source,
        priority: 'normal',
      })
      refetch()
    } finally {
      setTriggerLoading(false)
    }
  }

  const handleTriggerAnalyze = async () => {
    setTriggerLoading(true)
    try {
      await api.createTask({
        type: 'analyze',
        priority: 'normal',
      })
      refetch()
    } finally {
      setTriggerLoading(false)
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      pending: 'text-yellow-400',
      running: 'text-blue-400',
      completed: 'text-green-400',
      failed: 'text-red-400',
    }
    return colors[status] || 'text-dark-300'
  }

  const getStatusBg = (status) => {
    const colors = {
      pending: 'bg-yellow-900',
      running: 'bg-blue-900',
      completed: 'bg-green-900',
      failed: 'bg-red-900',
    }
    return colors[status] || 'bg-dark-700'
  }

  return (
    <div className="space-y-6">
      {/* Trigger buttons */}
      <div className="card">
        <div className="text-xs font-bold mb-3">Trigger Tasks</div>
        <div className="space-y-2">
          <button
            onClick={() => handleTriggerAnalyze()}
            disabled={triggerLoading}
            className="w-full px-3 py-2 bg-purple-900 text-purple-400 border border-purple-700 text-xs rounded disabled:opacity-50"
          >
            {triggerLoading ? 'Triggering...' : 'Run Analysis Pipeline'}
          </button>
          <div className="text-xs text-dark-400 mt-3">Collect data from:</div>
          <div className="grid grid-cols-2 gap-2">
            {['yfinance', 'reddit', 'sec_edgar', 'google_trends'].map((source) => (
              <button
                key={source}
                onClick={() => handleTriggerCollect(source)}
                disabled={triggerLoading}
                className="px-2 py-1 bg-blue-900 text-blue-400 border border-blue-700 text-xs rounded disabled:opacity-50"
              >
                {source}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Task queue */}
      <div className="card">
        <div className="text-xs font-bold mb-3">Queue</div>
        <div className="space-y-2">
          {(tasks || []).length === 0 && (
            <div className="text-xs text-dark-400">No tasks in queue</div>
          )}
          {(tasks || []).map((task) => (
            <div key={task.id} className="bg-dark-900 p-2 rounded border border-dark-700">
              <div className="flex justify-between items-start mb-1">
                <span className="text-xs font-mono">{task.type}</span>
                <span className={`text-xs ${getStatusColor(task.status)}`}>
                  {task.status}
                </span>
              </div>
              {task.source && (
                <div className="text-xs text-dark-400">{task.source}</div>
              )}
              {task.error && (
                <div className="text-xs text-red-400 mt-1">{task.error}</div>
              )}
              <div className="text-xs text-dark-500 mt-1">
                {new Date(task.created_at).toLocaleTimeString()}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Auto-refresh indicator */}
      <div className="text-xs text-dark-400">
        Auto-refreshing every 3 seconds...
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/pages/TaskQueue.jsx
git commit -m "feat: add Task Queue page with trigger controls"
```

---

## Task 16: NotFound page and error handling

**Files:**
- Create: `frontend/src/pages/NotFound.jsx`

**Steps:**

- [ ] **Step 1: Create NotFound.jsx**

File: `/sessions/laughing-serene-mendel/mnt/Trader/frontend/src/pages/NotFound.jsx`

```jsx
import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <div className="text-6xl font-bold text-dark-400 mb-4">404</div>
        <div className="text-sm text-dark-400 mb-6">Page not found</div>
        <Link
          to="/"
          className="px-4 py-2 bg-blue-900 text-blue-400 border border-blue-700 rounded text-xs"
        >
          Back to Overview
        </Link>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add frontend/src/pages/NotFound.jsx
git commit -m "feat: add NotFound 404 page"
```

---

## Task 17: Full build, test, and production verification

**Files:**
- No new files (integration test)

**Steps:**

- [ ] **Step 1: Build React frontend**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader/frontend
npm run build
```

Expected: Output to `social_arb/static/` with `index.html` and `assets/`

- [ ] **Step 2: Verify static files**

```bash
ls -la /sessions/laughing-serene-mendel/mnt/Trader/social_arb/static/
```

Expected: `index.html`, `assets/main.HASH.js`, `assets/main.HASH.css`

- [ ] **Step 3: Start FastAPI server**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
python -m uvicorn social_arb.api.main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 4: Test API endpoints**

In another terminal:
```bash
curl http://localhost:8000/api/v1/health
```

Expected: `{...health data...}`

- [ ] **Step 5: Test SPA serving**

```bash
curl http://localhost:8000/
```

Expected: `<!DOCTYPE html>...` (index.html content)

- [ ] **Step 6: Test SPA catch-all routing**

```bash
curl http://localhost:8000/signals
curl http://localhost:8000/positions
curl http://localhost:8000/nonexistent
```

Expected: All return `index.html` content (SPA routing handled by React)

- [ ] **Step 7: Verify API endpoints still work**

```bash
curl http://localhost:8000/api/v1/instruments
```

Expected: JSON array (not HTML)

- [ ] **Step 8: Test in browser**

Navigate to `http://localhost:8000` and verify:
- Sidebar loads
- Navigation links work
- Pages load (even with no data, should show "loading" or empty state)
- API calls populate data when available

- [ ] **Step 9: Commit build output (if tracking)**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add social_arb/static/
git commit -m "build: production frontend build"
```

---

## Task 18: Development workflow documentation

**Files:**
- Create: `FRONTEND_DEV.md`

**Steps:**

- [ ] **Step 1: Create development guide**

File: `/sessions/laughing-serene-mendel/mnt/Trader/FRONTEND_DEV.md`

```markdown
# Frontend Development Workflow

## Quick Start

### Production (SPA served from FastAPI)
```bash
# Build frontend once
cd frontend
npm run build

# Start API server (serves both API + static SPA)
cd ..
python -m uvicorn social_arb.api.main:app --host 0.0.0.0 --port 8000

# Navigate to http://localhost:8000
```

### Development (Vite dev server with API proxy)
```bash
# Terminal 1: Start FastAPI backend
cd /sessions/laughing-serene-mendel/mnt/Trader
python -m uvicorn social_arb.api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start Vite dev server (proxies /api to :8000)
cd frontend
npm run dev

# Navigate to http://localhost:5173
```

## File Structure Reference

- **`frontend/src/main.jsx`** — React entry point
- **`frontend/src/App.jsx`** — Router + layout
- **`frontend/src/api.js`** — API client (all endpoints)
- **`frontend/src/hooks/`** — `useApi`, `usePolling`
- **`frontend/src/components/`** — Reusable UI components
- **`frontend/src/pages/`** — Page components (routed)
- **`frontend/src/styles/index.css`** — Tailwind + dark theme

## Adding New Pages

1. Create `frontend/src/pages/YourPage.jsx`
2. Add route to `App.jsx`
3. Add nav item to `components/Sidebar.jsx`

## API Calls

All API calls go through `frontend/src/api.js`:

```javascript
import { api } from '../api'

// In component:
const { data, loading, error, refetch } = useApi(async () => api.getSignals())
```

## Styling

Dark theme only. Use Tailwind classes:

```jsx
<div className="bg-dark-800 text-dark-50 border border-dark-700">
  Content
</div>
```

Theme variables in `frontend/src/styles/index.css` and `index.html`.

## Building for Production

```bash
cd frontend
npm run build
# Output → social_arb/static/
```

Then FastAPI serves it:
```bash
python -m uvicorn social_arb.api.main:app --port 8000
# Navigate to http://localhost:8000
```
```

- [ ] **Step 2: Commit**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader
git add FRONTEND_DEV.md
git commit -m "docs: add frontend development workflow guide"
```

---

## Summary

**Deliverables:**
- ✓ Vite + React SPA scaffold with build pipeline
- ✓ FastAPI static file serving + SPA catch-all routing
- ✓ API client (`api.js`) with all 20+ endpoints
- ✓ Generic hooks (`useApi`, `usePolling`)
- ✓ Reusable components (ScoreSlider, EngineCard, DecisionButton, TickerSearchInput, SymbolLink)
- ✓ 9 page components (Overview, Tickers, TickerDetail, SignalRadar, MosaicCards, ThesisForge, GateReview, Positions, TaskQueue)
- ✓ Layout shell (Sidebar, Header, StatusBar)
- ✓ Dark theme (no light mode)
- ✓ Full HITL workflow (L1→L2→L3 gates, narratives, decisions)
- ✓ Production build + verification
- ✓ Dev workflow documentation

**Technology Stack Confirmed:**
- Vite + React 18 + React Router v6
- Tailwind CSS (CDN, no build step)
- Recharts (for future charts)
- No Node.js in production
- FastAPI serves everything

**Code Quality:**
- Functional components + hooks only (no class components)
- All components have `export default` or named exports
- API client is centralized, typed through JSDoc
- Error handling with `ApiError` class
- All forms have loading/error states
- Dark theme throughout (Bloomberg terminal aesthetic)
- Information-dense, minimal whitespace

**Next Phase:** Connect to real data sources, add charts via Recharts, wire up STEPPS UI, performance tuning.
