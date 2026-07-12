import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useSession } from '../../context/SessionContext'
import OAuthButtons from './OAuthButtons'
import ForgotPasswordForm from './ForgotPasswordForm'

export default function LoginForm() {
  const { login } = useSession()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showForgot, setShowForgot] = useState(false)

  const submit = (e) => {
    e.preventDefault()
    // TODO: POST /api/v1/auth/login (not implemented yet)
    login({ user_id: 'dev-user', token: null })
    navigate('/app/chat')
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950 p-4 text-white">
      <div className="w-full max-w-md rounded-2xl border border-gray-800 bg-gray-900 p-8 shadow-xl">
        <h1 className="mb-6 text-center text-3xl font-bold text-red-600">Log In</h1>
        {showForgot ? (
          <ForgotPasswordForm onBack={() => setShowForgot(false)} />
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email"
              className="w-full rounded-lg border border-gray-800 bg-gray-950 p-3 text-white focus:outline-none focus:ring-2 focus:ring-red-600"
            />
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              className="w-full rounded-lg border border-gray-800 bg-gray-950 p-3 text-white focus:outline-none focus:ring-2 focus:ring-red-600"
            />
            <button
              type="submit"
              className="w-full rounded-lg bg-red-600 p-3 font-semibold text-white hover:bg-red-700"
            >
              Log In
            </button>
          </form>
        )}

        {!showForgot && (
          <div className="mt-4 space-y-3">
            <button
              onClick={() => setShowForgot(true)}
              className="w-full text-sm text-gray-400 hover:text-white"
            >
              Forgot password?
            </button>
            <OAuthButtons />
            <p className="text-center text-sm text-gray-400">
              No account?{' '}
              <Link to="/signup" className="font-bold text-red-600 hover:underline">
                Sign up
              </Link>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
