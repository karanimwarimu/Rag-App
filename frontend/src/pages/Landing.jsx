import { Link } from 'react-router-dom'

export default function Landing() {
  const features = [
    {
      title: 'Chat',
      desc: 'Ask questions grounded in your own documents.',
      to: '/app/chat',
      disabled: false,
    },
    {
      title: 'Document Upload',
      desc: 'Drag & drop PDFs, Word docs, text, and images.',
      to: '/app/upload',
      disabled: false,
    },
    {
      title: 'Web Link Ingestion',
      desc: 'Ingest knowledge from URLs.',
      to: '/app/links',
      disabled: true,
    },
  ]

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="flex items-center justify-between p-6">
        <span className="text-2xl font-extrabold tracking-wide text-red-600">
          MK1.3
        </span>
        <div className="space-x-3">
          <Link
            to="/login"
            className="rounded-full px-4 py-2 text-sm font-semibold text-gray-300 hover:bg-gray-800"
          >
            Log In
          </Link>
          <Link
            to="/signup"
            className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
          >
            Get Started
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-16 text-center">
        <h1 className="text-5xl font-extrabold tracking-tight">
          Your documents, answered.
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-gray-400">
          A Retrieval-Augmented Generation assistant that grounds every answer in
          the files you upload.
        </p>
        <div className="mt-8 flex justify-center space-x-4">
          <Link
            to="/signup"
            className="rounded-full bg-indigo-600 px-6 py-3 font-semibold text-white hover:bg-indigo-700"
          >
            Get Started
          </Link>
          <Link
            to="/login"
            className="rounded-full border border-gray-700 px-6 py-3 font-semibold text-gray-300 hover:bg-gray-800"
          >
            Log In
          </Link>
        </div>

        <div className="mt-16 grid gap-6 sm:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className={`rounded-2xl border border-gray-800 bg-gray-900 p-6 text-left ${
                f.disabled ? 'opacity-50' : ''
              }`}
            >
              <h3 className="text-xl font-bold text-red-600">{f.title}</h3>
              <p className="mt-2 text-sm text-gray-400">{f.desc}</p>
              {f.disabled ? (
                <span className="mt-3 inline-block text-xs font-bold text-gray-500">
                  Coming soon
                </span>
              ) : (
                <Link
                  to={f.to}
                  className="mt-3 inline-block text-sm font-bold text-indigo-400 hover:underline"
                >
                  Open →
                </Link>
              )}
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
