import { Navigate, Route, Routes } from 'react-router-dom'
import Nav from './components/Nav'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Browse from './pages/Browse'
import CookMode from './pages/CookMode'
import RecipeDetail from './pages/RecipeDetail'
import RecipeEdit from './pages/RecipeEdit'
import Search from './pages/Search'
import SignIn from './pages/SignIn'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) return <div className="pa-loading">Loading…</div>
  if (!isAuthenticated) return <Navigate to="/signin" replace />
  return <>{children}</>
}

function RootRedirect() {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) return <div className="pa-loading">Loading…</div>
  return <Navigate to={isAuthenticated ? '/browse' : '/signin'} replace />
}

function AppRoutes() {
  return (
    <>
      <Nav />
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/signin" element={<SignIn />} />
        <Route path="/browse" element={<RequireAuth><Browse /></RequireAuth>} />
        <Route path="/recipes/new" element={<RequireAuth><RecipeEdit /></RequireAuth>} />
        <Route path="/recipes/:id/edit" element={<RequireAuth><RecipeEdit /></RequireAuth>} />
        <Route path="/recipes/:id/cook" element={<RequireAuth><CookMode /></RequireAuth>} />
        <Route path="/recipes/:id" element={<RequireAuth><RecipeDetail /></RequireAuth>} />
        <Route path="/search" element={<RequireAuth><Search /></RequireAuth>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
