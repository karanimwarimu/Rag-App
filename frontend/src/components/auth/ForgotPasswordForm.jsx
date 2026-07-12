export default function ForgotPasswordForm({ onBack }) {
  const submit = (e) => {
    e.preventDefault()
    // TODO: POST /api/v1/auth/forgot-password (not implemented yet)
    console.log('[auth] forgot-password stub')
    alert('If that email exists, a reset link has been sent (stub).')
    onBack?.()
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <input
        type="email"
        required
        placeholder="Email"
        className="w-full rounded-lg border border-gray-800 bg-gray-950 p-3 text-white"
      />
      <button
        type="submit"
        className="w-full rounded-lg bg-red-600 p-3 font-semibold text-white hover:bg-red-700"
      >
        Send reset link
      </button>
      <button
        type="button"
        onClick={onBack}
        className="w-full text-sm text-gray-400 hover:text-white"
      >
        Back to login
      </button>
    </form>
  )
}
