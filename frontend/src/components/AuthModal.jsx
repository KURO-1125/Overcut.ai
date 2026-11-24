import React, { useState, useEffect } from 'react'
import {
  X, Mail, Lock, User, Eye, EyeOff,
  ArrowRight, ShieldCheck,
} from 'lucide-react'
import { useAuth, DEMO_USERS } from '../context/AuthContext'

export default function AuthModal() {
  const {
    isAuthModalOpen, closeAuth,
    authMode, setAuthMode,
    login, signup, loginWithDemo,
    authError, authLoading,
  } = useAuth()

  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [name, setName]         = useState('')
  const [role, setRole]         = useState('Chief Race Engineer')
  const [team, setTeam]         = useState('Scuderia Ferrari HP')
  const [showPw, setShowPw]     = useState(false)

  useEffect(() => {
    if (!isAuthModalOpen) return
    const handleKey = (e) => { if (e.key === 'Escape') closeAuth() }
    document.addEventListener('keydown', handleKey)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.body.style.overflow = previousOverflow
    }
  }, [isAuthModalOpen, closeAuth])

  if (!isAuthModalOpen) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (authMode === 'login') {
      if (!email || !password) return
      await login(email, password)
    } else {
      if (!name || !email || !password) return
      await signup({ name, email, password, role, team })
    }
  }

  const handleDemoSelect = (demoUser) => {
    loginWithDemo(demoUser)
  }

  const inputStyle = {
    width: '100%',
    background: 'var(--bg-surface-2)',
    color: 'var(--text-primary)',
    border: '1px solid var(--border-mid)',
    borderRadius: '8px',
    padding: '10px 14px',
    fontSize: '12px',
    fontFamily: "'Inter', sans-serif",
    outline: 'none',
    transition: 'border-color 0.15s',
  }
  const iFocus = e => { e.target.style.borderColor = 'var(--accent)' }
  const iBlur  = e => { e.target.style.borderColor = 'var(--border-mid)' }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(12px)' }}
      onClick={closeAuth}
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
    >
      <div
        className="relative w-full max-w-md rounded-xl p-6 sm:p-8"
        style={{
          background: 'var(--bg-surface-1)',
          border: '1px solid var(--border-mid)',
          boxShadow: '0 24px 80px rgba(0,0,0,0.6)',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Close */}
        <button
          onClick={closeAuth}
          className="absolute top-4 right-4 p-1.5 rounded-md cursor-pointer transition-colors"
          style={{ color: 'var(--text-muted)', background: 'none', border: 'none' }}
          aria-label="Close"
        >
          <X size={16} />
        </button>

        {/* Header */}
        <div className="text-center mb-6">
          <div
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-semibold mb-3"
            style={{ border: '1px solid rgba(0,212,255,0.25)', background: 'rgba(0,212,255,0.08)', color: 'var(--accent)', fontFamily: "'JetBrains Mono', monospace" }}
          >
            <span className="live-beacon beacon-accent" style={{ width: 5, height: 5 }} />
            OVERCUT.AI ACCESS GATEWAY
          </div>
          <h2
            id="auth-modal-title"
            className="text-[22px] font-bold"
            style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)' }}
          >
            {authMode === 'login' ? 'Welcome Back' : 'Create Engineering ID'}
          </h2>
          <p
            className="text-[12px] mt-1.5 max-w-xs mx-auto"
            style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif" }}
          >
            {authMode === 'login'
              ? 'Sign in to access 100Hz telemetry intelligence and 7B on-device AI.'
              : 'Register your engineer profile for collaborative anomaly diagnostics.'}
          </p>
        </div>

        {/* Tab Switcher */}
        <div
          className="grid grid-cols-2 p-1 rounded-lg mb-6"
          style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-dim)' }}
        >
          {['login', 'signup'].map(tab => (
            <button
              key={tab}
              type="button"
              onClick={() => setAuthMode(tab)}
              className="py-2 text-[12px] font-semibold rounded-md cursor-pointer transition-all"
              style={{
                fontFamily: "'Space Grotesk', sans-serif",
                background: authMode === tab ? 'rgba(0,212,255,0.1)' : 'transparent',
                color: authMode === tab ? 'var(--accent)' : 'var(--text-muted)',
                border: authMode === tab ? '1px solid rgba(0,212,255,0.25)' : '1px solid transparent',
              }}
            >
              {tab === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          ))}
        </div>

        {/* Error */}
        {authError && (
          <div
            className="p-3 mb-4 rounded-lg flex items-center gap-2 text-[12px]"
            style={{ background: 'rgba(255,51,102,0.08)', border: '1px solid rgba(255,51,102,0.25)', color: '#FF3366', fontFamily: "'Inter', sans-serif" }}
          >
            <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: '#FF3366' }} />
            {authError}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-3">
          {authMode === 'signup' && (
            <div>
              <label className="block text-[11px] font-medium mb-1" style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif" }}>Full Name</label>
              <div className="relative">
                <User size={13} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-disabled)' }} />
                <input
                  type="text" required placeholder="Alex Vance"
                  value={name} onChange={e => setName(e.target.value)}
                  style={{ ...inputStyle, paddingLeft: '32px' }}
                  onFocus={iFocus} onBlur={iBlur}
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-[11px] font-medium mb-1" style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif" }}>Work Email</label>
            <div className="relative">
              <Mail size={13} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-disabled)' }} />
              <input
                type="email" required placeholder="engineer@scuderia.f1"
                autoFocus
                value={email} onChange={e => setEmail(e.target.value)}
                style={{ ...inputStyle, paddingLeft: '32px', fontFamily: "'JetBrains Mono', monospace" }}
                onFocus={iFocus} onBlur={iBlur}
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-medium mb-1" style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif" }}>Password</label>
            <div className="relative">
              <Lock size={13} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-disabled)' }} />
              <input
                type={showPw ? 'text' : 'password'} required
                placeholder="••••••••••••"
                value={password} onChange={e => setPassword(e.target.value)}
                style={{ ...inputStyle, paddingLeft: '32px', paddingRight: '36px', fontFamily: "'JetBrains Mono', monospace" }}
                onFocus={iFocus} onBlur={iBlur}
              />
              <button
                type="button" onClick={() => setShowPw(!showPw)}
                className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer"
                style={{ color: 'var(--text-muted)', background: 'none', border: 'none' }}
                aria-label={showPw ? 'Hide' : 'Show'}
              >
                {showPw ? <EyeOff size={13} /> : <Eye size={13} />}
              </button>
            </div>
            {authMode === 'signup' && (
              <p className="text-[10px] mt-1" style={{ color: 'var(--text-disabled)', fontFamily: "'Inter', sans-serif" }}>Minimum 8 characters</p>
            )}
          </div>

          {authMode === 'signup' && (
            <div className="grid grid-cols-2 gap-2.5">
              <div>
                <label className="block text-[11px] font-medium mb-1" style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif" }}>Team</label>
                <select value={team} onChange={e => setTeam(e.target.value)} style={{ ...inputStyle }}>
                  <option>Scuderia Ferrari HP</option>
                  <option>Oracle Red Bull Racing</option>
                  <option>McLaren F1 Team</option>
                  <option>Mercedes-AMG Petronas</option>
                  <option>Aston Martin Aramco</option>
                  <option>Williams Racing</option>
                  <option>Alpine F1 Team</option>
                  <option>Haas F1 Team</option>
                  <option>Kick Sauber</option>
                  <option>Visa Cash App RB</option>
                  <option>NASA Ames / EV Fleet</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-medium mb-1" style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif" }}>Specialization</label>
                <select value={role} onChange={e => setRole(e.target.value)} style={{ ...inputStyle }}>
                  <option>Chief Race Engineer</option>
                  <option>Telemetry Architect</option>
                  <option>Aerodynamicist</option>
                  <option>Vehicle Dynamics</option>
                  <option>BMS Battery Specialist</option>
                  <option>Performance Engineer</option>
                </select>
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={authLoading}
            className="w-full mt-2 py-3 px-4 rounded-lg font-semibold text-[13px] cursor-pointer transition-all flex items-center justify-center gap-2"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              background: 'var(--accent)',
              color: '#000',
              border: 'none',
              opacity: authLoading ? 0.6 : 1,
            }}
          >
            {authLoading ? (
              <span className="inline-block w-4 h-4 rounded-full animate-spin" style={{ border: '2px solid rgba(0,0,0,0.3)', borderTopColor: '#000' }} />
            ) : (
              <>
                <span>{authMode === 'login' ? 'Authenticate & Enter' : 'Complete Registration'}</span>
                <ArrowRight size={14} />
              </>
            )}
          </button>
        </form>

        {/* Divider */}
        <div className="relative my-5 text-center">
          <div className="absolute inset-0 flex items-center" style={{ top: '50%', transform: 'translateY(-50%)' }}>
            <div className="w-full" style={{ borderTop: '1px solid var(--border-dim)' }} />
          </div>
          <span
            className="relative px-3 text-[10px] uppercase tracking-wider font-semibold"
            style={{ background: 'var(--bg-surface-1)', color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
          >
            Or Instant Demo Access
          </span>
        </div>

        {/* Demo Users */}
        <div className="space-y-2">
          <div className="flex items-center justify-between mb-2 text-[11px]" style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif" }}>
            <span>Select a pre-configured team profile:</span>
            <span style={{ color: 'var(--accent)' }}>1-Click Fast Pass</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {DEMO_USERS.map(demo => (
              <button
                key={demo.id}
                type="button"
                onClick={() => handleDemoSelect(demo)}
                className="p-2.5 rounded-lg text-left cursor-pointer transition-all flex flex-col"
                style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-dim)' }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--border-bright)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-dim)' }}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <div
                    className="w-6 h-6 rounded-md flex items-center justify-center text-[10px] font-bold flex-shrink-0"
                    style={{ background: demo.accentColor || 'var(--accent)', color: '#000' }}
                  >
                    {demo.avatar}
                  </div>
                  <span className="text-[11px] font-semibold truncate" style={{ color: 'var(--text-primary)', fontFamily: "'Inter', sans-serif" }}>
                    {demo.name}
                  </span>
                </div>
                <span className="text-[10px] truncate" style={{ color: 'var(--text-disabled)', fontFamily: "'Inter', sans-serif" }}>
                  {demo.team}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Guest */}
        <div className="mt-5 pt-4 text-center" style={{ borderTop: '1px solid var(--border-dim)' }}>
          <button
            type="button"
            onClick={() => loginWithDemo({
              id: 'guest', name: 'Guest Observer', email: 'guest@overcut.ai',
              role: 'Observer', team: 'Paddock', avatar: 'GO', accentColor: '#3D5068', isDemo: true,
            })}
            className="text-[12px] cursor-pointer inline-flex items-center gap-1.5 transition-colors"
            style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif", background: 'none', border: 'none' }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-secondary)' }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)' }}
          >
            <ShieldCheck size={12} style={{ color: '#00FF88' }} />
            Continue as anonymous Guest Observer
          </button>
        </div>
      </div>
    </div>
  )
}
