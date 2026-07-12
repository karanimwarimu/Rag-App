import { Link, useLocation } from 'react-router-dom'
import { env } from '../../config/env'

export default function Shell({ children }) {
  const { pathname } = useLocation()

  const navItem = (to, label) => (
    <Link
      to={to}
      className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
        pathname === to
          ? 'bg-indigo-600 text-white'
          : 'text-gray-300 hover:bg-gray-800'
      }`}
    >
      {label}
    </Link>
  )

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-white">
      <nav className="flex items-center gap-2 border-b border-gray-800 bg-gray-900 p-3">
        <Link
          to="/"
          className="mr-4 text-xl font-extrabold tracking-wide text-red-600"
        >
          MK1.3
        </Link>
        {navItem('/app/chat', 'Chat')}
        {navItem('/app/upload', 'Upload')}
        {env.ENABLE_LINK_UPLOADER && navItem('/app/links', 'Links')}
      </nav>
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  )
}
