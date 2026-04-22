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

function getHeaders() {
  const headers = { 'Content-Type': 'application/json' }
  const token = sessionStorage.getItem('sa_token')
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

async function handleResponse(res) {
  const data = await res.json()
  if (!res.ok) {
    throw new ApiError(res.status, data.detail || `HTTP ${res.status}`, data)
  }
  return data
}

export const api = {
  // Auth
  async login(email, password) {
    const res = await fetch(`${API_BASE}/v1/auth/login`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ email, password }),
    })
    return handleResponse(res)
  },

  async register(email, password, displayName) {
    const res = await fetch(`${API_BASE}/v1/auth/register`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ email, password, display_name: displayName }),
    })
    return handleResponse(res)
  },

  async googleLogin(credential) {
    const res = await fetch(`${API_BASE}/v1/auth/google`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ credential }),
    })
    return handleResponse(res)
  },

  // Health
  async getHealth() {
    const res = await fetch(`${API_BASE}/v1/health`, { headers: getHeaders() })
    return handleResponse(res)
  },

  // Instruments
  async getInstruments(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/instruments?${query}`, { headers: getHeaders() })
    return handleResponse(res)
  },

  async getInstrumentFacets() {
    const res = await fetch(`${API_BASE}/v1/instruments/facets`, { headers: getHeaders() })
    return handleResponse(res)
  },

  async createInstrument(data) {
    const res = await fetch(`${API_BASE}/v1/instruments`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async updateInstrument(id, data) {
    const res = await fetch(`${API_BASE}/v1/instruments/${id}`, {
      method: 'PATCH',
      headers: getHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async deleteInstrument(id) {
    const res = await fetch(`${API_BASE}/v1/instruments/${id}`, {
      method: 'DELETE',
      headers: getHeaders(),
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
    const res = await fetch(`${API_BASE}/v1/signals?${query}`, { headers: getHeaders() })
    return handleResponse(res)
  },

  async createSignal(data) {
    const res = await fetch(`${API_BASE}/v1/signals`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async getSignalsGrouped(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/signals/grouped?${query}`, { headers: getHeaders() })
    return handleResponse(res)
  },

  // Mosaics
  async getMosaics(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/mosaics?${query}`, { headers: getHeaders() })
    return handleResponse(res)
  },

  // Theses
  async getTheses(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/theses?${query}`, { headers: getHeaders() })
    return handleResponse(res)
  },

  async createThesis(data) {
    const res = await fetch(`${API_BASE}/v1/theses`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  // Reviews (HITL)
  async getReviews(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/reviews?${query}`, { headers: getHeaders() })
    return handleResponse(res)
  },

  async createReview(data) {
    const res = await fetch(`${API_BASE}/v1/reviews`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  // Positions
  async getPositions(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/positions?${query}`, { headers: getHeaders() })
    return handleResponse(res)
  },

  async createPosition(data) {
    const res = await fetch(`${API_BASE}/v1/positions`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async closePosition(positionId, data) {
    const res = await fetch(`${API_BASE}/v1/positions/${positionId}`, {
      method: 'PATCH',
      headers: getHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  // Analysis / Engines
  async runAnalysis(data = {}) {
    const res = await fetch(`${API_BASE}/v1/analyze`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async getEngineOutput(symbol) {
    const res = await fetch(`${API_BASE}/v1/engine/${symbol}`, { headers: getHeaders() })
    return handleResponse(res)
  },

  // Tasks
  async getTasks(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/tasks?${query}`, { headers: getHeaders() })
    return handleResponse(res)
  },

  async createTask(data) {
    const res = await fetch(`${API_BASE}/v1/tasks`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async getTask(id) {
    const res = await fetch(`${API_BASE}/v1/tasks/${id}`, { headers: getHeaders() })
    return handleResponse(res)
  },

  async deleteTask(id) {
    const res = await fetch(`${API_BASE}/v1/tasks/${id}`, {
      method: 'DELETE',
      headers: getHeaders(),
    })
    if (!res.ok) {
      const data = await res.json()
      throw new ApiError(res.status, data.detail || `HTTP ${res.status}`, data)
    }
    return { success: true }
  },

  async getSourceHealth() {
    const res = await fetch(`${API_BASE}/v1/source-health`, { headers: getHeaders() })
    return handleResponse(res)
  },

  // STEPPS
  async scoreStepps(data) {
    const res = await fetch(`${API_BASE}/v1/stepps/score`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async getSteppsScores(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/stepps/scores?${query}`, { headers: getHeaders() })
    return handleResponse(res)
  },

  async correctStepps(data) {
    const res = await fetch(`${API_BASE}/v1/stepps/correct`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  // Lattice Graph
  async getLattice(symbol) {
    const res = await fetch(`${API_BASE}/v1/lattice/${symbol}`, { headers: getHeaders() })
    return handleResponse(res)
  },

  async addLatticeNode(symbol, data) {
    const res = await fetch(`${API_BASE}/v1/lattice/${symbol}/node`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async addLatticeEdge(symbol, data) {
    const res = await fetch(`${API_BASE}/v1/lattice/${symbol}/edge`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  // Scheduler
  async getSchedulerStatus() {
    const res = await fetch(`${API_BASE}/v1/scheduler/status`, { headers: getHeaders() })
    return handleResponse(res)
  },

  async triggerSchedule(data) {
    const res = await fetch(`${API_BASE}/v1/scheduler/trigger`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  // Alerts
  async getAlerts(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/alerts?${query}`, { headers: getHeaders() })
    return handleResponse(res)
  },

  async getAlertThresholds() {
    const res = await fetch(`${API_BASE}/v1/alerts/thresholds`, { headers: getHeaders() })
    return handleResponse(res)
  },

  async updateAlertThresholds(thresholds) {
    const res = await fetch(`${API_BASE}/v1/alerts/thresholds`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify({ thresholds }),
    })
    return handleResponse(res)
  },

  async clearAlerts() {
    const res = await fetch(`${API_BASE}/v1/alerts`, {
      method: 'DELETE',
      headers: getHeaders(),
    })
    if (!res.ok) {
      const data = await res.json()
      throw new ApiError(res.status, data.detail || `HTTP ${res.status}`, data)
    }
    return { success: true }
  },

  // User Settings
  async getSettings() {
    const res = await fetch(`${API_BASE}/v1/auth/settings`, {
      headers: getHeaders(),
    })
    return handleResponse(res)
  },

  async updateSettings(settings) {
    const res = await fetch(`${API_BASE}/v1/auth/settings`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify(settings),
    })
    return handleResponse(res)
  },

  // Watchlist
  async getWatchlist() {
    const res = await fetch(`${API_BASE}/v1/auth/watchlist`, {
      headers: getHeaders(),
    })
    return handleResponse(res)
  },

  async addToWatchlist(symbol) {
    const res = await fetch(`${API_BASE}/v1/auth/watchlist`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ symbol }),
    })
    return handleResponse(res)
  },

  async removeFromWatchlist(symbol) {
    const res = await fetch(`${API_BASE}/v1/auth/watchlist/${symbol}`, {
      method: 'DELETE',
      headers: getHeaders(),
    })
    if (!res.ok) {
      const data = await res.json()
      throw new ApiError(res.status, data.detail || `HTTP ${res.status}`, data)
    }
    return { success: true }
  },

  // Sentiment
  async getSentiment(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/sentiment?${query}`, {
      headers: getHeaders(),
    })
    return handleResponse(res)
  },
}
