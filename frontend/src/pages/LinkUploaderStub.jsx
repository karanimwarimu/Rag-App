import { useState } from 'react'

export default function LinkUploaderStub() {
  const [url, setUrl] = useState('')

  return (
    <div className="mx-auto my-auto w-full max-w-3xl p-4">
      <div className="rounded-2xl border border-yellow-300/40 bg-gray-950 p-8 shadow-xl">
        <div className="mb-4 inline-block rounded-full bg-yellow-300/10 px-3 py-1 text-xs font-bold text-yellow-300">
          Coming soon
        </div>
        <h1 className="text-3xl font-bold text-red-600">Web Link Ingestion</h1>
        <p className="mt-2 text-gray-400">
          Ingest knowledge from a URL and let the assistant ground answers in web
          content. This feature is not yet available.
        </p>

        <div className="mt-6 flex items-center space-x-2">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/article"
            disabled
            className="flex-1 rounded-lg border border-gray-800 bg-gray-900 p-3 text-white placeholder-gray-500 focus:outline-none"
          />
          <button
            type="button"
            disabled
            className="cursor-not-allowed rounded-lg bg-gray-700 px-6 py-3 font-semibold text-gray-400"
          >
            Ingest
          </button>
        </div>
      </div>
    </div>
  )
}
