import { useEffect, useRef, useState } from 'react'
import { sendChatMessage } from '../api/chat'

const MAX_RETRIES = 3
const INITIAL_DELAY = 1000

function now() {
  return new Date().toLocaleTimeString()
}

export default function ChatWorkspace() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [showError, setShowError] = useState(false)
  const [errorText, setErrorText] = useState('')
  const containerRef = useRef(null)
  const assistantIdRef = useRef(null)

  const scrollToBottom = () => {
    const el = containerRef.current
    if (el) el.scrollTop = el.scrollHeight
  }

  useEffect(scrollToBottom, [messages, isThinking])

  useEffect(() => {
    setMessages([
      {
        id: Date.now(),
        text: "Hello there! I'm an AI assistant. How can I help you today?",
        sender: 'ai',
        timestamp: now(),
      },
    ])
  }, [])

  const appendToAssistant = (chunk, full) => {
    const id = assistantIdRef.current
    if (id == null) return
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, text: full ?? m.text + chunk } : m))
    )
  }

  const showErrorModal = (message) => {
    setErrorText(message)
    setShowError(true)
  }

  const handleSend = async (text) => {
    const messageText = text.trim()
    if (messageText === '' || isThinking) return

    setIsThinking(true)
    const userMsg = {
      id: Date.now(),
      text: messageText,
      sender: 'user',
      timestamp: now(),
    }
    const aiId = Date.now() + 1
    assistantIdRef.current = aiId
    setMessages((prev) => [
      ...prev,
      { id: aiId, text: '', sender: 'ai', timestamp: now() },
    ])
    setInput('')

    let retries = 0
    let ok = false
    while (retries < MAX_RETRIES) {
      try {
        await sendChatMessage(messageText, {
          onToken: (chunk, full) => appendToAssistant(chunk, full),
        })
        ok = true
        break
      } catch (err) {
        console.error('Chat error:', err)
        retries += 1
        if (retries < MAX_RETRIES) {
          await new Promise((r) => setTimeout(r, INITIAL_DELAY * 2 ** (retries - 1)))
        }
      }
    }

    setIsThinking(false)
    assistantIdRef.current = null
    if (!ok) {
      setMessages((prev) => prev.filter((m) => m.id !== aiId))
      showErrorModal(
        "Sorry, I'm having trouble connecting right now. Please try again later."
      )
    }
  }

  const handleCopy = (text) => {
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    try {
      document.execCommand('copy')
    } catch (e) {
      console.error('Copy failed', e)
    }
    document.body.removeChild(ta)
  }

  return (
    <div className="flex h-full flex-col bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900 px-4 py-3">
        <h1 className="text-lg font-semibold tracking-wide">MK1.3 Chat</h1>
      </div>

      {/* Messages */}
      <div ref={containerRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-6">
        {messages.map((m) => (
          <MessageRow key={m.id} message={m} onCopy={() => handleCopy(m.text)} />
        ))}

        {isThinking && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-2xl bg-gray-800 px-4 py-3 text-gray-200">
              <div className="flex space-x-1">
                <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400" />
                <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:0.15s]" />
                <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:0.3s]" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Composer */}
      <form
        className="border-t border-gray-800 bg-gray-900 p-4"
        onSubmit={(e) => {
          e.preventDefault()
          handleSend(input)
        }}
      >
        <div className="mx-auto flex max-w-3xl items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Send a message..."
            className="flex-1 rounded-full border border-gray-700 bg-gray-800 px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-600"
          />
          <button
            type="submit"
            className="rounded-full bg-indigo-600 px-5 py-3 font-semibold text-white transition-colors hover:bg-indigo-700"
          >
            Send
          </button>
        </div>
      </form>

      {showError && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900 bg-opacity-75">
          <div className="w-80 rounded-2xl border border-red-500 bg-gray-800 p-6 text-center shadow-xl">
            <p className="mb-4 font-semibold text-red-400">{errorText}</p>
            <div className="flex justify-center space-x-4">
              <button
                className="rounded-full bg-gray-600 px-4 py-2 text-white transition-colors hover:bg-gray-700"
                onClick={() => setShowError(false)}
              >
                Close
              </button>
              <button
                className="rounded-full bg-indigo-600 px-4 py-2 text-white transition-colors hover:bg-indigo-700"
                onClick={() => window.location.reload()}
              >
                Reload Page
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function MessageRow({ message, onCopy }) {
  const isUser = message.sender === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow ${
          isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-gray-800 text-gray-100 rounded-bl-sm'
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{message.text}</p>
        <div className="mt-1 flex items-center justify-between gap-3">
          <span className="text-[10px] text-gray-400">{message.timestamp}</span>
          <button
            className="text-[11px] text-gray-400 hover:text-white"
            onClick={onCopy}
          >
            Copy
          </button>
        </div>
      </div>
    </div>
  )
}
