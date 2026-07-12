// Centralized, typed access to build-time environment variables.
// Vite exposes env vars prefixed with VITE_ via import.meta.env.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
const ENABLE_WEBSOCKET_CHAT = import.meta.env.VITE_ENABLE_WEBSOCKET_CHAT === 'true'
const ENABLE_LINK_UPLOADER = import.meta.env.VITE_ENABLE_LINK_UPLOADER === 'true'
const SKIP_AUTH = import.meta.env.VITE_SKIP_AUTH === 'true'

if (!API_BASE_URL) {
  throw new Error(
    '[env] VITE_API_BASE_URL is not set. Copy .env.example to .env and set it ' +
      '(e.g. http://localhost:5000).'
  )
}

export const env = {
  API_BASE_URL,
  ENABLE_WEBSOCKET_CHAT,
  ENABLE_LINK_UPLOADER,
  SKIP_AUTH,
}
