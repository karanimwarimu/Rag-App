import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { SessionProvider, useSession } from './context/SessionContext'
import Shell from './components/layout/Shell'
import Landing from './pages/Landing'
import LoginForm from './components/auth/LoginForm'
import SignUpForm from './components/auth/SignUpForm'
import ChatWorkspace from './pages/ChatWorkspace'
import UploadWorkspace from './pages/UploadWorkspace'
import LinkUploaderStub from './pages/LinkUploaderStub'
import { env } from './config/env'

function RequireAuth({ children }) {
  const { isAuthenticated } = useSession()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<LoginForm />} />
      <Route path="/signup" element={<SignUpForm />} />
      <Route
        path="/app/chat"
        element={
          <RequireAuth>
            <Shell>
              <ChatWorkspace />
            </Shell>
          </RequireAuth>
        }
      />
      <Route
        path="/app/upload"
        element={
          <RequireAuth>
            <Shell>
              <UploadWorkspace />
            </Shell>
          </RequireAuth>
        }
      />
      {env.ENABLE_LINK_UPLOADER && (
        <Route
          path="/app/links"
          element={
            <RequireAuth>
              <Shell>
                <LinkUploaderStub />
              </Shell>
            </RequireAuth>
          }
        />
      )}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <SessionProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </SessionProvider>
  )
}
