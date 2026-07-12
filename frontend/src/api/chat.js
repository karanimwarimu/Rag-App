import { env } from '../config/env'

const CHAT_ENDPOINT = `${env.API_BASE_URL}/api/v1/chat`

/**
 * Sends a chat prompt and streams the answer.
 *
 * Forward-compatible with the Guide 2 Step 4 SSE contract: we request
 * `stream: true` and read the response body as a Server-Sent-Events stream.
 * If the backend does not stream (content-type application/json), we fall back
 * to the single buffered `{RESULT: "..."}` JSON shape used by the current
 * (and renamed) backend. The UI attaches no image/dead-endpoint calls.
 */
export async function sendChatMessage(
  prompt,
  { onToken, signal } = {}
) {
  const response = await fetch(CHAT_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, stream: true, user_id: null, job_id: null }),
    signal,
  })

  if (!response.ok) {
    throw new Error(`Chat request failed with status ${response.status}`)
  }

  const contentType = response.headers.get('content-type') || ''

  // --- Fallback: single buffered JSON ({RESULT: "..."}) ---
  if (contentType.includes('application/json')) {
    const data = await response.json()
    const text = data?.RESULT ?? ''
    if (onToken) onToken(text)
    return text
  }

  // --- Streaming: parse SSE frames. Each `data:` line is JSON {token}. ---
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let full = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let sep
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const frame = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)

      const dataLine = frame
        .split('\n')
        .find((l) => l.startsWith('data:'))
      if (!dataLine) continue

      const payload = dataLine.slice(5).trim()
      if (!payload || payload === '[DONE]') continue

      let chunk = ''
      try {
        const json = JSON.parse(payload)
        chunk = json.token ?? json.text ?? ''
      } catch {
        // Non-JSON frame: treat raw payload as a token chunk.
        chunk = payload
      }

      full += chunk
      if (onToken) onToken(chunk, full)
    }
  }

  return full
}
