import React, { useRef, useEffect, useState } from 'react'
import gsap from 'gsap'
import { Home, Flag, Zap, LogIn, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

// ── Precision diamond logo mark ──────────────────────────────────
function LogoMark() {
  return (
    <svg
      width="30"
      height="30"
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {/* Outer diamond */}
      <polygon
        points="15,2 28,15 15,28 2,15"
        stroke="#00D4FF"
        strokeWidth="1.2"
        fill="none"
        opacity="0.9"
      />
      {/* Inner diamond fill */}
      <polygon
        points="15,7 23,15 15,23 7,15"
        stroke="#00D4FF"
        strokeWidth="0.8"
        fill="rgba(0,212,255,0.07)"
      />
      {/* Center cross hairs */}
      <line x1="15" y1="10" x2="15" y2="20" stroke="#00D4FF" strokeWidth="0.6" opacity="0.5" />
      <line x1="10" y1="15" x2="20" y2="15" stroke="#00D4FF" strokeWidth="0.6" opacity="0.5" />
      {/* Core */}
      <circle cx="15" cy="15" r="2.5" fill="#00D4FF" />
      {/* Tick corners */}
      <line x1="2" y1="15" x2="5" y2="15" stroke="#00D4FF" strokeWidth="1" opacity="0.4" />
      <line x1="25" y1="15" x2="28" y2="15" stroke="#00D4FF" strokeWidth="1" opacity="0.4" />
    </svg>
  )
}

// ── Telemetry status chip ─────────────────────────────────────────
function StatusChip({ children, color = 'var(--accent)' }) {
  return (
    <div
      className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 rounded"
      style={{
        background: `${color}10`,
        border: `1px solid ${color}25`,
      }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full glow-dot"
        style={{ background: color }}
      />
      <span
        className="text-[10px] font-semibold tracking-[0.08em]"
        style={{ color, fontFamily: "'JetBrains Mono', monospace" }}
      >
        {children}
      </span>
    </div>
  )
}

const NAV_ITEMS = [
  { id: 'home',       label: 'Home',          icon: Home },
  { id: 'f1-landing', label: 'F1',            icon: Flag },
  { id: 'ev-landing', label: 'EV',            icon: Zap },
]

export default function AppHeader({ currentView, onNavigate, mode }) {
  const { user, openAuth, logout } = useAuth()
  const headerRef = useRef(null)
  const [scrolled, setScrolled] = useState(false)

  // Track scroll for subtle shadow intensification
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Entrance animation
  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from(headerRef.current, {
        y: -24,
        opacity: 0,
        duration: 0.7,
        ease: 'power3.out',
      })
    }, headerRef)
    return () => ctx.revert()
  }, [])

  const activeSignal = mode === 'ev' ? 'var(--ev-signal)' : 'var(--f1-signal)'

  return (
    <header
      ref={headerRef}
      className="sticky top-0 z-50 h-[56px] flex items-center transition-all duration-300"
      style={{
        background: scrolled
          ? 'rgba(3,5,7,0.94)'
          : 'rgba(3,5,7,0.80)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        borderBottom: scrolled
          ? '1px solid var(--border-mid)'
          : '1px solid var(--border-dim)',
        boxShadow: scrolled ? '0 4px 32px rgba(0,0,0,0.6)' : 'none',
      }}
      role="banner"
    >
      <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between gap-4">

        {/* ── Left: Logo ───────────────────────────────────────── */}
        <button
          type="button"
          onClick={() => onNavigate('home')}
          className="flex items-center gap-2 cursor-pointer group flex-shrink-0"
          aria-label="Overcut AI — go to home"
          onMouseEnter={e => gsap.to(e.currentTarget.querySelector('svg'), { rotation: 45, duration: 0.4, ease: 'power2.out' })}
          onMouseLeave={e => gsap.to(e.currentTarget.querySelector('svg'), { rotation: 0, duration: 0.4, ease: 'power2.out' })}
        >
          <LogoMark />
          <div className="flex items-baseline gap-0.5">
            <span
              className="text-[14px] font-bold tracking-[0.08em] uppercase"
              style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)' }}
            >
              OVERCUT
            </span>
            <span
              className="text-[14px] font-bold tracking-[0.08em]"
              style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--accent)' }}
            >
              .AI
            </span>
          </div>
        </button>

        {/* ── Center: Nav ──────────────────────────────────────── */}
        <nav
          className="hidden md:flex items-center"
          style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid var(--border-dim)',
            borderRadius: '8px',
            padding: '3px',
            gap: '2px',
          }}
          role="navigation"
          aria-label="Main navigation"
        >
          {NAV_ITEMS.map((item) => {
            const isActive = currentView === item.id
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onNavigate(item.id)}
                className="relative px-3.5 py-1.5 rounded-md text-[12px] font-medium cursor-pointer transition-all duration-200 flex items-center gap-1.5"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  color: isActive ? 'var(--text-bright)' : 'var(--text-muted)',
                  background: isActive ? 'rgba(255,255,255,0.07)' : 'transparent',
                  border: 'none',
                }}
                aria-current={isActive ? 'page' : undefined}
                onMouseEnter={e => {
                  if (!isActive) gsap.to(e.currentTarget, { color: 'var(--text-primary)', duration: 0.15 })
                }}
                onMouseLeave={e => {
                  if (!isActive) gsap.to(e.currentTarget, { color: 'var(--text-muted)', duration: 0.15 })
                }}
              >
                <item.icon size={12} />
                <span>{item.label}</span>
                {isActive && (
                  <span
                    className="absolute bottom-0.5 left-1/2 -translate-x-1/2 w-3 h-[2px] rounded-full"
                    style={{ background: 'var(--accent)' }}
                  />
                )}
              </button>
            )
          })}
        </nav>

        {/* ── Right: Status + Auth ─────────────────────────────── */}
        <div className="flex items-center gap-2 flex-shrink-0">

          {/* Live telemetry chips */}
          <StatusChip color={activeSignal}>
            {mode === 'ev' ? '50HZ PACK' : '100HZ LAP'}
          </StatusChip>
          <StatusChip color="var(--accent)">
            VLM READY
          </StatusChip>

          {/* Auth section */}
          {user ? (
            <div className="flex items-center gap-1.5">
              <div
                className="hidden sm:flex items-center gap-2 px-2.5 py-1.5 rounded-md"
                style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-mid)' }}
              >
                <div
                  className="w-5 h-5 rounded flex items-center justify-center text-[9px] font-black"
                  style={{ background: 'var(--accent)', color: '#000' }}
                >
                  {(user.name || user.email || 'U')[0].toUpperCase()}
                </div>
                <span
                  className="text-[11px] font-medium max-w-[90px] truncate"
                  style={{ color: 'var(--text-secondary)', fontFamily: "'Inter', sans-serif" }}
                >
                  {user.name || user.email}
                </span>
              </div>
              <button
                type="button"
                onClick={logout}
                className="p-1.5 rounded-md cursor-pointer transition-colors"
                style={{ color: 'var(--text-muted)', background: 'none', border: 'none' }}
                title="Sign out"
                onMouseEnter={e => { e.currentTarget.style.color = 'var(--severity-critical)' }}
                onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)' }}
              >
                <LogOut size={13} />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={openAuth}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-[12px] font-semibold cursor-pointer transition-all duration-200"
              style={{
                background: 'var(--accent)',
                color: '#000',
                fontFamily: "'Space Grotesk', sans-serif",
                border: 'none',
                letterSpacing: '0.02em',
              }}
              onMouseEnter={e => gsap.to(e.currentTarget, {
                scale: 1.04,
                boxShadow: '0 0 20px rgba(0,212,255,0.4)',
                duration: 0.2,
              })}
              onMouseLeave={e => gsap.to(e.currentTarget, {
                scale: 1,
                boxShadow: 'none',
                duration: 0.2,
              })}
            >
              <LogIn size={12} />
              <span>Sign In</span>
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
