import { useEffect, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Nav() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    function handleClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [menuOpen])

  const hidden = location.pathname === '/signin' || location.pathname.includes('/cook')
  if (hidden) return null

  const initial = user
    ? (user.display_name?.[0] ?? user.email[0]).toUpperCase()
    : ''

  return (
    <nav className="pa-nav">
      <NavLink to="/browse" className="pa-nav-logo">
        <span className="pa-nav-logo-mark">
          <span className="pa-nav-logo-hole" />
        </span>
        pantry
      </NavLink>

      <div className="pa-nav-links">
        <NavLink to="/browse" className={({ isActive }) => 'pa-nav-link' + (isActive ? ' active' : '')}>
          Browse
        </NavLink>
        <NavLink to="/search" className={({ isActive }) => 'pa-nav-link' + (isActive ? ' active' : '')}>
          Search
        </NavLink>
        <NavLink to="/recipes/new" className={({ isActive }) => 'pa-nav-link' + (isActive ? ' active' : '')}>
          Add Recipe
        </NavLink>
      </div>

      {user && (
        <div className="pa-nav-avatar-wrap" ref={wrapRef}>
          <button
            className="pa-avatar"
            onClick={() => setMenuOpen(o => !o)}
            aria-label="User menu"
          >
            {initial}
          </button>
          {menuOpen && (
            <div className="pa-nav-menu">
              <div className="pa-nav-menu-label">signed in · {user.email}</div>
              <button
                className="pa-menuitem"
                onClick={() => { setMenuOpen(false); logout() }}
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      )}
    </nav>
  )
}
