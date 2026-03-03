const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Normalize trailing slash to avoid double slashes in requests.
export const API_BASE = rawBaseUrl.replace(/\/+$/, '')
