import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PhotoPlaceholder from '../components/PhotoPlaceholder'
import { useAuth } from '../contexts/AuthContext'

export default function SignIn() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email)
      navigate('/browse')
    } catch {
      setError('Sign in failed. Check your email and try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="pa-signin">
      <div className="pa-signin-hero">
        <PhotoPlaceholder style={{ height: '100%', borderRadius: 0, border: 'none' }} />
        <div className="pa-signin-hero-overlay">
          <p className="pa-signin-hero-tagline">Your recipes,<br />all in one place.</p>
        </div>
      </div>
      <div className="pa-signin-panel">
        <div className="pa-signin-logo">
          <span className="pa-signin-logo-dot" />
          pantry
        </div>
        <h1 className="pa-signin-heading">Welcome back</h1>
        <p className="pa-signin-sub">Sign in to access your recipe collection.</p>
        <form onSubmit={handleSubmit}>
          <div className="pa-signin-field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>
          {error && <p style={{ color: '#c00', fontSize: 13, marginBottom: 12 }}>{error}</p>}
          <button className="pa-signin-btn" type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <div className="pa-signin-divider">or continue with</div>
        <div className="pa-signin-social">
          <button className="pa-signin-social-btn" disabled>Continue with Google</button>
          <button className="pa-signin-social-btn" disabled>Continue with Apple</button>
        </div>
      </div>
    </div>
  )
}
