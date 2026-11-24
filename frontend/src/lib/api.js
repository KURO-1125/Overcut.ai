const rawBase = import.meta.env.VITE_API_URL || ''
export const API_BASE = rawBase.replace(/\/+$/, '')
const API_KEY = import.meta.env.VITE_API_KEY || ''

export class ApiError extends Error {
  constructor(message, status, body) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

export async function apiFetch(path, { timeoutMs = 90000, ...options } = {}) {
  const headers = { ...(options.headers || {}) }
  if (API_KEY) headers['X-API-Key'] = API_KEY
  if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json'

  const signal = options.signal ?? AbortSignal.timeout(timeoutMs)
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers, signal })
  if (!res.ok) {
    let detail = ''
    try {
      const body = await res.json()
      detail = body?.detail || ''
    } catch {
      // non-JSON error body
    }
    throw new ApiError(detail || `Request failed (HTTP ${res.status})`, res.status)
  }
  return res
}

export function resolveImageUrl(url) {
  if (!url) return null
  if (/^https?:\/\//i.test(url) || url.startsWith('data:') || url.startsWith('blob:')) return url
  return `${API_BASE}${url.startsWith('/') ? '' : '/'}${url}`
}
