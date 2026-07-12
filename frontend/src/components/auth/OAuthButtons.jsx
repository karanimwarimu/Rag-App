export default function OAuthButtons() {
  const handle = (provider) => {
    // TODO: real OAuth flow (Guide 2 Step 5 stub routes exist as 501)
    console.log(`[auth] OAuth intent: ${provider}`)
  }

  const btn =
    'w-full rounded-lg border border-gray-700 bg-gray-950 p-3 text-sm font-semibold text-white transition-colors hover:bg-gray-800'

  return (
    <div className="space-y-2">
      <button className={btn} onClick={() => handle('google')}>
        Continue with Google
      </button>
      <button className={btn} onClick={() => handle('github')}>
        Continue with GitHub
      </button>
    </div>
  )
}
