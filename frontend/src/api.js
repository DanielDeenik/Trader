/**
 * API client: fetch wrapper with error handling.
 * Base URL: /api (proxied to :8000 in dev, served from FastAPI in prod)
 */

const API_BASE = '/api'

// Token storage (in memory, not localStorage)
let authToken = null

export function setAuthToken(token) {
  authToken = token
}

export function getAuthToken() {
  return authToken
}

export function clearAuthToken() {
  authToken = null
}

export class ApiError extends Error {
  constructor(status, message, data) {
    super(message)
    this.status = status
    this.data = data
  }
}

function getHeaders(includeAuth = true) {
  const headers = { 'Content-Type': 'application/json' }
  if (includeAuth && authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
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
  async register(email, password, displayName) {
    const res = await fetch(`${API_BASE}/v1/auth/register`, {
      method: 'POST',
      headers: getHeaders(false),
      body: JSON.stringify({ email, password, display_name: displayName }),
    })
    const data = await handleResponse(res)
    if (data.token) {
      setAuthToken(data.token)
    }
    return data
  },

  async login(email, password) {
    const res = await fetch(`${API_BASE}/v1/auth/login`, {
      method: 'POST',
      headers: getHeaders(false),
      body: JSON.stringify({ email, password }),
    })
    const data = await handleResponse(res)
    if (data.token) {
      setAuthToken(data.token)
    }
    return data
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/v1/auth/me`, {
      headers: getHeaders(true),
    })
    return handleResponse(res)
  },

  async updateSettings(data) {
    const res = await fetch(`${API_BASE}/v1/auth/settings`, {
      method: 'PUT',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async getWatchlist() {
    const res = await fetch(`${API_BASE}/v1/auth/watchlist`, {
      headers: getHeaders(true),
    })
    return handleResponse(res)
  },

  async addToWatchlist(symbol) {
    const res = await fetch(`${API_BASE}/v1/auth/watchlist`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify({ symbol }),
    })
    return handleResponse(res)
  },

  async removeFromWatchlist(symbol) {
    const res = await fetch(`${API_BASE}/v1/auth/watchlist/${symbol}`, {
      method: 'DELETE',
      headers: getHeaders(true),
    })
    if (!res.ok) {
      const data = await res.json()
      throw new ApiError(res.status, data.detail || `HTTP ${res.status}`, data)
    }
    return { success: true }
  },

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
      headers: getHeaders(true),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async updateInstrument(id, data) {
    const res = await fetch(`${API_BASE}/v1/instruments/${id}`, {
      method: 'PATCH',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async deleteInstrument(id) {
    const res = await fetch(`${API_BASE}/v1/instruments/${id}`, {
      method: 'DELETE',
      headers: getHeaders(true),
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
      headers: getHeaders(true),
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
      headers: getHeaders(true),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  // Analysis / Engines
  async runAnalysis(data = {}) {
    const res = await fetch(`${API_BASE}/v1/analyze`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
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
      headers: getHeaders(true),
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
      headers: getHeaders(true),
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
      headers: getHeaders(true),
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
      headers: getHeaders(true),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  // Lattice Graph
  async getLattice(symbol) {
    const res = await fetch(`${API_BASE}/v1/lattice/${symbol}`)
    return handleResponse(res)
  },

  async addLatticeNode(symbol, data) {
    const res = await fetch(`${API_BASE}/v1/lattice/${symbol}/node`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  async addLatticeEdge(symbol, data) {
    const res = await fetch(`${API_BASE}/v1/lattice/${symbol}/edge`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  // Scheduler
  async getSchedulerStatus() {
    const res = await fetch(`${API_BASE}/v1/scheduler/status`)
    return handleResponse(res)
  },

  async triggerSchedule(data) {
    const res = await fetch(`${API_BASE}/v1/scheduler/trigger`, {
      method: 'POST',
      headers: getHeaders(true),
      body: JSON.stringify(data),
    })
    return handleResponse(res)
  },

  // Alerts
  async getAlerts(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/v1/alerts?${query}`)
    return handleResponse(res)
  },

  async getAlertThresholds() {
    const res = await fetch(`${API_BASE}/v1/alerts/thresholds`)
    return handleResponse(res)
  },

  async updateAlertThresholds(thresholds) {
    const res = await fetch(`${API_BASE}/v1/alerts/thresholds`, {
      method: 'PUT',
      headers: getHeaders(true),
      body: JSON.stringify({ thresholds }),
    })
    return handleResponse(res)
  },

  async clearAlerts() {
    const res = await fetch(`${API_BASE}/v1/alerts`, {
      method: 'DELETE',
      headers: getHeaders(true),
    })
    if (!res.ok) {
      const data = await res.json()
      throw new ApiError(res.status, data.detail || `HTTP ${res.status}`, data)
    }
    return { success: true }
  },
}
