import { env } from '../config/env'

const UPLOAD_ENDPOINT = `${env.API_BASE_URL}/api/v1/upload`

/**
 * Uploads a single file to the ingestion endpoint.
 *
 * The backend accepts the file and processes (chunk/embed/store) in a
 * background task, so this resolves as soon as the server acknowledges receipt
 * ({ message: "..." }). Real per-file progress isn't streamed by the backend
 * yet, so the UI animates an indeterminate bar until this resolves.
 *
 * NOTE: there is no DELETE endpoint on the backend yet (Guide 1 integration
 * spec: `DELETE /api/v1/documents/{id}` is not implemented), so callers must
 * not attempt server-side deletes from here.
 */
export async function uploadFile(file, { signal } = {}) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(UPLOAD_ENDPOINT, {
    method: 'POST',
    body: formData,
    signal,
  })

  if (!response.ok) {
    throw new Error(`Upload failed with status ${response.status}`)
  }

  return response.json()
}
