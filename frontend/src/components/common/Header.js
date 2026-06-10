import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../hooks/useTheme';

function SunIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M12 3v1m0 16v1m8.66-9H21M3 12H2m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 6a6 6 0 100 12A6 6 0 0012 6z"/>
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
    </svg>
  );
}

export default function Header() {
  const { user, logout } = useAuth();
  const { dark, toggle } = useTheme();

  return (
    <header className="shrink-0 px-6 py-3 flex items-center justify-between transition-colors duration-200"
            style={{
              background: 'var(--bg-header)',
              borderBottom: '1px solid var(--border)',
              boxShadow: 'var(--shadow)',
            }}>

      {/* Left: breadcrumb placeholder */}
      <div />

      {/* Right: controls */}
      <div className="flex items-center gap-3">

        {/* User email */}
        <span className="text-sm hidden sm:block" style={{ color: 'var(--text-muted)' }}>
          {user?.email}
        </span>

        {/* Theme toggle */}
        <button
          onClick={toggle}
          title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
          className="flex items-center justify-center h-8 w-8 rounded-lg border transition-all duration-200 hover:scale-110"
          style={{
            background: 'var(--bg-card)',
            borderColor: 'var(--border)',
            color: 'var(--text-muted)',
          }}
        >
          {dark ? <SunIcon /> : <MoonIcon />}
        </button>

        {/* Sign out */}
        <button
          onClick={logout}
          className="text-sm px-3 py-1.5 rounded-lg border transition-all duration-200 font-medium hover:opacity-80"
          style={{
            background: 'var(--bg-card)',
            borderColor: 'var(--border)',
            color: 'var(--text-body)',
          }}
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
