import { useRef, useState } from 'react'
import { uploadFile } from '../api/upload'
import { ALLOWED_EXTENSIONS } from '../config/constants'

const genId = () => `file-${Date.now()}-${Math.floor(Math.random() * 1000)}`

function isValidFileType(file) {
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()
  return ALLOWED_EXTENSIONS.includes(ext)
}

export default function UploadWorkspace() {
  const [items, setItems] = useState([])
  const [toasts, setToasts] = useState([])
  const [showApp, setShowApp] = useState(true)

  const queueRef = useRef([])
  const processingRef = useRef(false)
  const fileInputRef = useRef(null)

  const pushToast = (message) => {
    const id = genId()
    setToasts((prev) => [...prev, { id, message }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 3000)
  }

  const setItem = (id, patch) =>
    setItems((prev) => prev.map((it) => (it.id === id ? { ...it, ...patch } : it)))

  const handleDelete = (id) => {
    queueRef.current = queueRef.current.filter((q) => q.id !== id)
    setItems((prev) => prev.filter((it) => it.id !== id))
    pushToast('Removed from queue')
  }

  const uploadOne = async (id, file) => {
    setItem(id, { status: 'uploading' })
    const interval = setInterval(() => {
      setItems((prev) =>
        prev.map((it) =>
          it.id === id ? { ...it, progress: Math.min(it.progress + 10, 90) } : it
        )
      )
    }, 100)

    try {
      const result = await uploadFile(file)
      clearInterval(interval)
      setItem(id, { status: 'success', progress: 100 })
      pushToast(`Successfully sent: ${file.name}`)
      if (result?.message) pushToast(result.message)
    } catch (err) {
      clearInterval(interval)
      console.error('Upload failed:', err)
      setItem(id, { status: 'error', progress: 0 })
      pushToast(`Error uploading: ${file.name}`)
    }
  }

  const processQueue = async () => {
    if (processingRef.current) return
    processingRef.current = true
    while (queueRef.current.length) {
      const next = queueRef.current.shift()
      // eslint-disable-next-line no-await-in-loop
      await uploadOne(next.id, next.file)
    }
    processingRef.current = false
  }

  const enqueue = (fileList) => {
    const incoming = Array.from(fileList || [])
    const newItems = []
    for (const file of incoming) {
      if (!isValidFileType(file)) {
        pushToast(`Unsupported file type: ${file.name}`)
        continue
      }
      const id = genId()
      queueRef.current.push({ id, file })
      newItems.push({ id, name: file.name, status: 'queued', progress: 0 })
    }
    if (newItems.length) {
      setItems((prev) => [...prev, ...newItems])
      processQueue()
    }
  }

  const onInputChange = (e) => {
    enqueue(e.target.files)
    e.target.value = ''
  }

  const onDrop = (e) => {
    e.preventDefault()
    enqueue(e.dataTransfer.files)
  }

  return (
    <div className="mx-auto my-auto w-full p-4 md:max-w-7xl">
      <div
        className="flex cursor-pointer items-center justify-between rounded-2xl border border-gray-800 bg-gray-950 p-6"
        onClick={() => setShowApp((s) => !s)}
      >
        <h1 className="text-3xl font-extrabold tracking-wider text-red-600 sm:text-4xl">
          MK1.3!
        </h1>
        <svg
          className={`h-6 w-6 text-yellow-300 transition-transform duration-300 ${
            showApp ? 'rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {showApp && (
        <div className="mt-2 flex flex-1 overflow-hidden md:flex md:h-auto">
          <div className="mr-0 min-w-[200px] max-w-[500px] w-1/4 overflow-y-auto rounded-2xl border border-gray-800 bg-gray-950 p-6 md:mr-2">
            <h2 className="mb-4 text-2xl font-bold text-red-600">Uploader Manual</h2>
            <ul className="space-y-4 text-sm text-gray-400">
              <li>
                <p className="font-semibold text-white">1. Select Files</p>
                <p>Click browse or drag and drop one or more files.</p>
                <p className="mt-2 text-xs text-gray-500">
                  Accepted: {ALLOWED_EXTENSIONS.join(', ')}.
                </p>
              </li>
              <li>
                <p className="font-semibold text-white">2. View Queue</p>
                <p>Files appear below, processed sequentially.</p>
              </li>
              <li>
                <p className="font-semibold text-white">3. Monitor Progress</p>
                <p>Green checkmark + toast on success.</p>
              </li>
            </ul>
          </div>

          <div className="flex min-w-[300px] flex-1 flex-col overflow-y-auto rounded-2xl border border-gray-800 bg-gray-950 p-8 shadow-xl">
            <h1 className="mb-6 text-center text-3xl font-bold text-red-600">
              Ironclad Uploader
            </h1>

            <label
              className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-yellow-300 p-8 transition-colors duration-200 hover:bg-gray-800 focus-within:bg-gray-800"
              onDragOver={(e) => e.preventDefault()}
              onDragLeave={(e) => e.preventDefault()}
              onDrop={onDrop}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                multiple
                onChange={onInputChange}
              />
              <span className="mt-4 text-center font-semibold text-gray-300">
                Drag & Drop files here or{' '}
                <span className="font-bold text-red-600 hover:underline">browse</span>
              </span>
              <span className="mt-1 text-sm text-gray-500">
                Supports images, documents, and PDFs
              </span>
            </label>

            <div className="mt-6 space-y-4">
              {items.map((it) => (
                <FileRow key={it.id} item={it} onDelete={() => handleDelete(it.id)} />
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="fixed right-4 top-4 z-50 space-y-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="flex items-center space-x-2 rounded-lg bg-gray-800 px-4 py-2 text-yellow-300 shadow-lg"
          >
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function FileRow({ item, onDelete }) {
  const isError = item.status === 'error'
  return (
    <div className="flex items-center space-x-4 rounded-lg bg-gray-800 p-3 shadow-md">
      <div className="flex-1 min-w-0">
        <p className="truncate text-sm font-medium text-white">{item.name}</p>
        <div className="mt-1 h-2 w-full rounded-full bg-gray-700">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${
              isError ? 'bg-red-600' : 'bg-red-600'
            }`}
            style={{ width: `${item.progress}%` }}
          />
        </div>
      </div>
      <button
        className="text-gray-400 hover:text-red-600"
        onClick={onDelete}
        aria-label="Remove"
      >
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
      {item.status === 'success' && (
        <div className="text-green-500">
          <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
      )}
    </div>
  )
}
