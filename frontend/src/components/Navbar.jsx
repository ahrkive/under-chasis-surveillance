import { useAuth } from '../context/AuthContext'
import { Link, useLocation } from 'react-router-dom'

/**
 * Navbar with live connection indicator, guard name, role badge, and view switcher.
 */
export default function Navbar({ isConnected }) {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <nav
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '1rem 2rem',
        background: 'rgba(255, 255, 255, 0.03)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
        backdropFilter: 'blur(10px)',
      }}
    >
      {/* Logo + Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            background: 'linear-gradient(135deg, #6366f1, #818cf8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.2rem',
          }}
        >
          🔍
        </div>
        <div>
          <h1
            style={{
              fontSize: '1rem',
              fontWeight: 700,
              background: 'linear-gradient(135deg, #f1f5f9, #94a3b8)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              letterSpacing: '-0.01em',
            }}
          >
            Undercarriage Inspector
          </h1>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              fontSize: '0.7rem',
              color: 'var(--text-muted)',
            }}
          >
            <span className={`live-dot ${isConnected ? '' : 'disconnected'}`} />
            {isConnected ? 'Live' : 'Disconnected'}
          </div>
        </div>
      </div>

      {/* User + View Switcher + Logout */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {user?.role === 'admin' && (
          <div style={{ display: 'flex', gap: '0.5rem', marginRight: '0.5rem' }}>
            <Link
              to="/creator"
              style={{
                padding: '0.35rem 0.75rem',
                borderRadius: 8,
                fontSize: '0.75rem',
                fontWeight: 600,
                textDecoration: 'none',
                background: location.pathname === '/creator' || location.pathname === '/' ? 'rgba(129, 140, 248, 0.2)' : 'transparent',
                color: location.pathname === '/creator' || location.pathname === '/' ? '#818cf8' : 'var(--text-muted)',
                border: '1px solid rgba(129, 140, 248, 0.3)',
              }}
            >
              ⚡ Command Center
            </Link>
            <Link
              to="/guard"
              style={{
                padding: '0.35rem 0.75rem',
                borderRadius: 8,
                fontSize: '0.75rem',
                fontWeight: 600,
                textDecoration: 'none',
                background: location.pathname === '/guard' ? 'rgba(16, 185, 129, 0.2)' : 'transparent',
                color: location.pathname === '/guard' ? '#34d399' : 'var(--text-muted)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
              }}
            >
              🛡️ Guard View
            </Link>
          </div>
        )}

        {user && (
          <span
            style={{
              fontSize: '0.85rem',
              color: 'var(--text-secondary)',
              fontWeight: 500,
            }}
          >
            {user.full_name}
            <span
              style={{
                marginLeft: '0.5rem',
                fontSize: '0.7rem',
                color: user.role === 'admin' ? '#c084fc' : 'var(--accent-indigo)',
                textTransform: 'uppercase',
                fontWeight: 700,
                background: user.role === 'admin' ? 'rgba(192, 132, 252, 0.15)' : 'rgba(99, 102, 241, 0.15)',
                padding: '0.2rem 0.5rem',
                borderRadius: 6,
              }}
            >
              {user.role === 'admin' ? 'CREATOR' : 'GUARD'}
            </span>
          </span>
        )}
        <button
          onClick={logout}
          style={{
            padding: '0.4rem 1rem',
            background: 'rgba(255, 255, 255, 0.06)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: 8,
            color: 'var(--text-secondary)',
            fontSize: '0.8rem',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            fontFamily: 'var(--font-family)',
          }}
          onMouseEnter={(e) => {
            e.target.style.background = 'rgba(239, 68, 68, 0.1)'
            e.target.style.borderColor = 'rgba(239, 68, 68, 0.3)'
            e.target.style.color = '#f87171'
          }}
          onMouseLeave={(e) => {
            e.target.style.background = 'rgba(255, 255, 255, 0.06)'
            e.target.style.borderColor = 'rgba(255, 255, 255, 0.1)'
            e.target.style.color = 'var(--text-secondary)'
          }}
        >
          Logout
        </button>
      </div>
    </nav>
  )
}
