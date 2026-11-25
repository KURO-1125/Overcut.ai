import React, { useEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import ScrollTrigger from 'gsap/ScrollTrigger'
import {
  ArrowLeft, Flag, TrendingUp, Zap,
  Search, Scissors, Cpu, Map, Activity, ArrowUpRight,
  Database, Shield,
} from 'lucide-react'

// ScrollTrigger is registered once at app root (main.jsx) — do not re-register here
// Smooth scroll is managed by the app-level Lenis instance in App.jsx

// ── Waveform Hero (richer version) ───────────────────────────────
function WaveformHeroSVG() {
  return (
    <svg
      viewBox="0 0 1200 220"
      preserveAspectRatio="none"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className="w-full"
      style={{ height: '220px' }}
    >
      {/* Grid lines */}
      {[44, 88, 132, 176].map(y => (
        <line key={y} x1="0" y1={y} x2="1200" y2={y}
          stroke="var(--border-dim)" strokeWidth="0.5" strokeDasharray="4 10" />
      ))}

      {/* Background fill */}
      <path
        d="M 0 170 L 0 100 C 50 100 80 50 100 50 C 120 50 140 100 160 110 C 200 125 220 60 260 40 C 300 20 320 90 360 90 C 400 90 420 50 460 30 C 500 10 540 80 580 90 C 620 100 650 50 700 20 C 750 -10 780 80 820 100 C 860 120 880 60 920 40 C 960 20 980 90 1020 100 C 1060 110 1080 60 1120 40 C 1140 30 1160 90 1200 90 L 1200 170 Z"
        fill="rgba(232,255,0,0.04)"
      />

      {/* Primary waveform */}
      <path
        d="M 0 100 C 50 100 80 50 100 50 C 120 50 140 100 160 110 C 200 125 220 60 260 40 C 300 20 320 90 360 90 C 400 90 420 50 460 30 C 500 10 540 80 580 90 C 620 100 650 50 700 20 C 750 -10 780 80 820 100 C 860 120 880 60 920 40 C 960 20 980 90 1020 100 C 1060 110 1080 60 1120 40 C 1140 30 1160 90 1200 90"
        stroke="#E8FF00"
        strokeWidth="1.5"
        fill="none"
      />

      {/* Anomaly selection window */}
      <rect x="640" y="8" width="180" height="162" fill="rgba(232,255,0,0.05)" stroke="#E8FF00" strokeWidth="1" strokeDasharray="3 4" rx="2" />

      {/* Drag handles */}
      <rect x="637" y="80" width="6" height="30" fill="#E8FF00" rx="2" opacity="0.8" />
      <rect x="817" y="80" width="6" height="30" fill="#E8FF00" rx="2" opacity="0.8" />

      {/* Anomaly label */}
      <text x="730" y="184" textAnchor="middle" fill="#E8FF00" fontSize="9" fontFamily="'JetBrains Mono', monospace" letterSpacing="0.1em">
        ANOMALY WINDOW · +68.4s
      </text>

      {/* Sector markers */}
      <line x1="380" y1="0" x2="380" y2="220" stroke="rgba(232,255,0,0.15)" strokeWidth="1" strokeDasharray="2 4" />
      <line x1="760" y1="0" x2="760" y2="220" stroke="rgba(232,255,0,0.15)" strokeWidth="1" strokeDasharray="2 4" />
      <text x="190" y="210" textAnchor="middle" fill="rgba(232,255,0,0.4)" fontSize="8" fontFamily="'JetBrains Mono', monospace">S1</text>
      <text x="570" y="210" textAnchor="middle" fill="rgba(232,255,0,0.4)" fontSize="8" fontFamily="'JetBrains Mono', monospace">S2</text>
      <text x="980" y="210" textAnchor="middle" fill="rgba(232,255,0,0.4)" fontSize="8" fontFamily="'JetBrains Mono', monospace">S3</text>
    </svg>
  )
}

// ── Interactive Waveform Preview ──────────────────────────────────
const WAVEFORM_PATHS = {
  monaco: 'M 0 60 C 30 60 50 20 70 20 C 90 20 100 50 120 55 C 150 62 160 30 190 15 C 220 0 240 45 270 50 C 300 55 320 25 350 10 C 380 -5 400 50 430 55 C 460 60 470 30 500 20 C 530 10 550 50 570 55',
  monza:  'M 0 55 C 40 55 60 10 90 10 C 120 10 140 55 170 55 C 200 55 210 10 250 5 C 290 0 310 50 350 50 C 390 50 400 15 440 10 C 480 5 500 50 540 55 C 560 58 570 30 570 30',
  spa:    'M 0 55 C 50 55 70 30 100 25 C 130 20 150 55 180 60 C 210 65 230 20 270 10 C 310 0 330 45 370 50 C 410 55 430 20 470 15 C 510 10 530 50 560 55 C 565 56 568 50 570 48',
}

const TABS = [
  { id: 'monaco', label: 'Monaco · T1 Braking', icon: Flag,     delta: '+0.183s lockup' },
  { id: 'monza',  label: 'Monza · Delta-T',     icon: TrendingUp, delta: 'P2 − P1: −0.047s' },
  { id: 'spa',    label: 'Spa · Sector 1',       icon: Zap,      delta: 'ERS deploy 94%' },
]

function WaveformPreview() {
  const [active, setActive] = useState('monaco')
  const pathRef = useRef(null)

  const switchTab = (id) => {
    if (id === active) return
    if (pathRef.current) {
      gsap.to(pathRef.current, {
        opacity: 0,
        y: 6,
        duration: 0.18,
        ease: 'power2.in',
        onComplete: () => {
          if (pathRef.current) {
            pathRef.current.setAttribute('d', WAVEFORM_PATHS[id])
            setActive(id)
            gsap.to(pathRef.current, { opacity: 1, y: 0, duration: 0.25, ease: 'power2.out' })
          }
        },
      })
    } else {
      setActive(id)
    }
  }

  const activeTab = TABS.find(t => t.id === active)

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-mid)' }}
    >
      {/* Tab bar */}
      <div
        className="flex items-center gap-1 p-3"
        style={{ borderBottom: '1px solid var(--border-dim)' }}
      >
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => switchTab(id)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-medium cursor-pointer transition-all"
            style={{
              fontFamily: "'Inter', sans-serif",
              background: active === id ? 'rgba(232,255,0,0.08)' : 'transparent',
              border: active === id ? '1px solid rgba(232,255,0,0.28)' : '1px solid transparent',
              color: active === id ? '#E8FF00' : 'var(--text-muted)',
            }}
          >
            <Icon size={11} />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Waveform canvas */}
      <div className="p-5">
        <svg
          viewBox="0 0 570 80"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
          className="w-full"
          style={{ height: '80px' }}
        >
          {[20, 40, 60].map(y => (
            <line key={y} x1="0" y1={y} x2="570" y2={y} stroke="var(--border-dim)" strokeWidth="0.5" />
          ))}
          <path
            ref={pathRef}
            d={WAVEFORM_PATHS.monaco}
            stroke="#E8FF00"
            strokeWidth="1.8"
            fill="none"
            style={{ willChange: 'transform, opacity' }}
          />
          {/* Anomaly dot */}
          <circle cx="350" cy="10" r="3" fill="#E8FF00" opacity="0.8" />
        </svg>

        <div className="flex items-center justify-between mt-3">
          <div className="flex items-center gap-3">
            <span
              className="text-[10px]"
              style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
            >
              4Hz real · OpenF1 / FastF1 · 2025
            </span>
            {activeTab && (
              <span
                className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-semibold"
                style={{ background: 'rgba(232,255,0,0.08)', color: '#E8FF00', border: '1px solid rgba(232,255,0,0.2)', fontFamily: "'JetBrains Mono', monospace" }}
              >
                {activeTab.delta}
              </span>
            )}
          </div>
          <span
            className="inline-flex items-center gap-1 text-[10px] font-semibold"
            style={{ color: '#E8FF00', fontFamily: "'JetBrains Mono', monospace" }}
          >
            <span className="live-beacon beacon-f1" />
            LIVE
          </span>
        </div>
      </div>
    </div>
  )
}

// ── Step Card ─────────────────────────────────────────────────────
function StepCard({ number, icon: Icon, title, body }) {
  const ref = useRef(null)
  return (
    <div
      ref={ref}
      className="step-card relative flex flex-col gap-4 p-6 rounded-xl overflow-hidden"
      style={{
        background: 'var(--bg-surface-2)',
        border: '1px solid var(--border-mid)',
        opacity: 0,
        transform: 'translateY(40px)',
        willChange: 'transform, opacity',
      }}
      onMouseEnter={() => gsap.to(ref.current, { borderColor: 'rgba(232,255,0,0.25)', y: -3, duration: 0.25, ease: 'power2.out' })}
      onMouseLeave={() => gsap.to(ref.current, { borderColor: 'var(--border-mid)',    y:  0, duration: 0.25, ease: 'power2.out' })}
    >
      {/* Top glow bar */}
      <div
        className="absolute top-0 left-0 right-0 h-[1px]"
        style={{ background: 'linear-gradient(to right, transparent, rgba(232,255,0,0.4), transparent)' }}
      />

      <div className="flex items-center gap-3">
        <span
          className="text-[11px] font-black"
          style={{ color: 'rgba(232,255,0,0.3)', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.08em' }}
        >
          {String(number).padStart(2, '0')}
        </span>
        <div
          className="w-10 h-10 flex items-center justify-center rounded-xl"
          style={{ border: '1px solid rgba(232,255,0,0.3)', background: 'rgba(232,255,0,0.06)' }}
        >
          <Icon size={18} style={{ color: '#E8FF00' }} />
        </div>
      </div>

      <h3
        className="text-[17px] font-bold"
        style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)', letterSpacing: '-0.01em' }}
      >
        {title}
      </h3>
      <p
        className="text-[13px] leading-relaxed"
        style={{ color: 'var(--text-secondary)', fontFamily: "'Inter', sans-serif" }}
      >
        {body}
      </p>
    </div>
  )
}

// ── Feature Card ──────────────────────────────────────────────────
function FeatureCard({ icon: Icon, title, body, stat }) {
  const ref = useRef(null)
  return (
    <div
      ref={ref}
      className="feat-card relative flex flex-col gap-3 p-5 rounded-xl overflow-hidden"
      style={{
        background: 'var(--bg-surface-2)',
        border: '1px solid var(--border-mid)',
        opacity: 0,
        transform: 'translateY(40px)',
        willChange: 'transform, opacity',
      }}
      onMouseEnter={() => gsap.to(ref.current, { borderColor: 'rgba(0,212,255,0.3)', y: -2, duration: 0.2, ease: 'power2.out' })}
      onMouseLeave={() => gsap.to(ref.current, { borderColor: 'var(--border-mid)',   y:  0, duration: 0.2, ease: 'power2.out' })}
    >
      <div
        className="absolute top-0 left-0 right-0 h-[1px]"
        style={{ background: 'linear-gradient(to right, transparent, rgba(0,212,255,0.3), transparent)' }}
      />
      <div
        className="w-9 h-9 flex items-center justify-center rounded-lg"
        style={{ border: '1px solid rgba(0,212,255,0.2)', background: 'rgba(0,212,255,0.06)' }}
      >
        <Icon size={16} style={{ color: 'var(--accent)' }} />
      </div>
      <h3
        className="text-[14px] font-semibold"
        style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-primary)' }}
      >
        {title}
      </h3>
      <p
        className="text-[12px] leading-relaxed flex-1"
        style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif" }}
      >
        {body}
      </p>
      <div
        className="pt-3 flex items-center gap-1.5"
        style={{ borderTop: '1px solid var(--border-dim)' }}
      >
        <span
          className="w-1 h-1 rounded-full"
          style={{ background: 'var(--accent)' }}
        />
        <span
          className="text-[10px] font-semibold"
          style={{ color: 'var(--accent)', fontFamily: "'JetBrains Mono', monospace" }}
        >
          {stat}
        </span>
      </div>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────
export default function F1LandingPage({ onLaunch, onBack }) {
  const containerRef = useRef(null)
  const stepsRef     = useRef(null)
  const featsRef     = useRef(null)
  // Smooth scroll is managed by the app-level Lenis instance in App.jsx

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.f1-hero-title', { y: 50, opacity: 0, duration: 0.8, ease: 'power3.out', delay: 0.1 })
      gsap.from('.f1-hero-sub',   { y: 30, opacity: 0, duration: 0.7, ease: 'power3.out', delay: 0.3 })
      gsap.from('.f1-hero-stats', { y: 20, opacity: 0, duration: 0.6, ease: 'power3.out', delay: 0.5 })
      gsap.from('.f1-wave',       { opacity: 0,        duration: 0.9, ease: 'power3.out', delay: 0.15 })

      ScrollTrigger.create({
        trigger: stepsRef.current,
        start: 'top 80%',
        onEnter: () => gsap.to('.step-card', { opacity: 1, y: 0, duration: 0.65, stagger: 0.1, ease: 'power3.out' }),
      })
      ScrollTrigger.create({
        trigger: featsRef.current,
        start: 'top 80%',
        onEnter: () => gsap.to('.feat-card', { opacity: 1, y: 0, duration: 0.65, stagger: 0.08, ease: 'power3.out' }),
      })
    }, containerRef)
    return () => ctx.revert()
  }, [])

  const STATS = [
    { icon: Map,      value: '24',         unit: 'Circuits',  label: 'FIA 2025 Calendar' },
    { icon: Activity, value: '100',        unit: 'Hz',        label: 'Sampling Rate' },
    { icon: Flag,     value: '2025–26',    unit: '',          label: 'Season Coverage' },
    { icon: Cpu,      value: '7B',         unit: 'QLoRA',     label: 'On-Device AI' },
  ]

  return (
    <div ref={containerRef} className="flex flex-col">

      {/* ── Hero ──────────────────────────────────────────────── */}
      <section
        className="relative pt-14 pb-8 overflow-hidden"
        style={{ background: 'var(--bg-floor)', minHeight: '70vh' }}
      >
        {/* Waveform background */}
        <div className="f1-wave absolute bottom-0 left-0 right-0" style={{ willChange: 'opacity' }}>
          <WaveformHeroSVG />
        </div>

        {/* Grid pattern */}
        <div className="absolute inset-0 telemetry-grid-bg opacity-20" />

        {/* F1 amber glow */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 60% 60% at 50% 30%, rgba(232,255,0,0.04) 0%, transparent 70%)' }}
        />

        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 flex flex-col items-center text-center gap-6">

          {/* Back button */}
          <button
            type="button"
            onClick={onBack}
            className="self-start flex items-center gap-1.5 text-[12px] cursor-pointer transition-colors mb-2"
            style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif", background: 'none', border: 'none' }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)' }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)' }}
          >
            <ArrowLeft size={13} />
            <span>Back to Home</span>
          </button>

          {/* Badge */}
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full text-[10px] font-black tracking-[0.1em] uppercase"
            style={{
              border: '1px solid rgba(232,255,0,0.3)',
              background: 'rgba(232,255,0,0.06)',
              color: '#E8FF00',
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            <span className="live-beacon beacon-f1" />
            FORMULA 1 MODE
          </div>

          {/* Headline */}
          <h1
            className="f1-hero-title display-title"
            style={{
              fontSize: 'clamp(36px, 6vw, 70px)',
              color: 'var(--text-bright)',
              letterSpacing: '-0.03em',
              maxWidth: '700px',
              willChange: 'transform, opacity',
            }}
          >
            Formula 1<br />
            <span style={{ color: '#E8FF00' }}>Telemetry Intelligence</span>
          </h1>

          <p
            className="f1-hero-sub text-[15px] leading-relaxed max-w-xl"
            style={{ color: 'var(--text-secondary)', fontFamily: "'Inter', sans-serif", willChange: 'transform, opacity' }}
          >
            Select your season, Grand Prix, and driver. Drag a window on the real lap trace.
            Get structured, evidence-grounded diagnostics from the telemetry waveform.
          </p>

          {/* CTAs */}
          <div className="f1-hero-sub flex flex-wrap justify-center gap-4">
            <button
              type="button"
              onClick={onLaunch}
              className="flex items-center gap-2 px-7 py-3.5 rounded-xl font-bold text-[14px] cursor-pointer"
              style={{
                fontFamily: "'Space Grotesk', sans-serif",
                background: '#E8FF00',
                color: '#000',
                border: 'none',
                letterSpacing: '0.02em',
                willChange: 'transform',
              }}
              onMouseEnter={e => gsap.to(e.currentTarget, { scale: 1.03, boxShadow: '0 0 32px rgba(232,255,0,0.4)', duration: 0.2 })}
              onMouseLeave={e => gsap.to(e.currentTarget, { scale: 1, boxShadow: 'none', duration: 0.2 })}
            >
              <Flag size={15} />
              <span>Launch F1 Workspace</span>
              <ArrowUpRight size={14} />
            </button>
            <button
              type="button"
              onClick={onBack}
              className="btn-ghost flex items-center gap-2"
            >
              <ArrowLeft size={13} />
              <span>Back</span>
            </button>
          </div>

          {/* Stats row */}
          <div
            className="f1-hero-stats w-full max-w-3xl grid grid-cols-2 md:grid-cols-4 gap-3 mt-4"
            style={{ willChange: 'transform, opacity' }}
          >
            {STATS.map(({ icon: Icon, value, unit, label }) => (
              <div
                key={label}
                className="flex flex-col items-center gap-1 p-4 rounded-xl"
                style={{ background: 'rgba(8,12,16,0.8)', border: '1px solid var(--border-mid)', backdropFilter: 'blur(8px)' }}
              >
                <Icon size={14} style={{ color: 'rgba(232,255,0,0.5)' }} />
                <div className="flex items-baseline gap-1">
                  <span
                    className="text-[20px] font-black"
                    style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#E8FF00', lineHeight: 1 }}
                  >
                    {value}
                  </span>
                  {unit && (
                    <span
                      className="text-[12px] font-bold"
                      style={{ color: 'rgba(232,255,0,0.6)', fontFamily: "'JetBrains Mono', monospace" }}
                    >
                      {unit}
                    </span>
                  )}
                </div>
                <span
                  className="text-[10px] text-center"
                  style={{ color: 'var(--text-disabled)', fontFamily: "'Inter', sans-serif" }}
                >
                  {label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ─────────────────────────────────────────── */}
      <section
        className="py-24"
        style={{ borderTop: '1px solid var(--border-dim)' }}
        ref={stepsRef}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="mb-14 text-center">
            <div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full mb-4 text-[10px] font-bold tracking-[0.15em] uppercase"
              style={{ border: '1px solid var(--border-mid)', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}
            >
              <span className="w-1 h-1 rounded-full" style={{ background: '#E8FF00' }} />
              Workflow
            </div>
            <h2
              className="text-[36px] sm:text-[44px] font-bold"
              style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)', letterSpacing: '-0.03em' }}
            >
              How It Works
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <StepCard number={1} icon={Search}  title="Select Session" body="Choose season, Grand Prix, session type and driver from the 2025 and 2026 FIA calendars. Data streams from OpenF1 (real car telemetry, ~4 Hz) or a local FastF1 cache." />
            <StepCard number={2} icon={Scissors} title="Slice Anomaly"  body="Drag on the telemetry chart to crop any micro-sector window. The system generates a waveform PNG artifact for CLIP embedding." />
            <StepCard number={3} icon={Cpu}      title="Get Diagnosis"  body="CLIP embeds the waveform, FAISS retrieves historical precedents, and the optional 7B QLoRA adapter (or deterministic heuristic fallback) returns a structured engineering report." />
          </div>
        </div>
      </section>

      {/* ── Live Waveform Preview ────────────────────────────────── */}
      <section
        className="py-24"
        style={{ background: 'var(--bg-surface-1)', borderTop: '1px solid var(--border-dim)' }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="mb-10 text-center">
            <h2
              className="text-[32px] sm:text-[40px] font-bold mb-3"
              style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)', letterSpacing: '-0.03em' }}
            >
              Waveform Preview
            </h2>
            <p className="text-[14px]" style={{ color: 'var(--text-muted)' }}>
              Switch sessions to see how telemetry signatures vary across circuits.
            </p>
          </div>
          <WaveformPreview />
        </div>
      </section>

      {/* ── Feature Grid ─────────────────────────────────────────── */}
      <section
        className="py-24"
        style={{ borderTop: '1px solid var(--border-dim)' }}
        ref={featsRef}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="mb-14 text-center">
            <div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full mb-4 text-[10px] font-bold tracking-[0.15em] uppercase"
              style={{ border: '1px solid var(--border-mid)', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}
            >
              <span className="w-1 h-1 rounded-full" style={{ background: 'var(--accent)' }} />
              Under the Hood
            </div>
            <h2
              className="text-[32px] sm:text-[40px] font-bold"
              style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)', letterSpacing: '-0.03em' }}
            >
              Technical Architecture
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <FeatureCard icon={Activity} title="OpenF1 + FastF1 Data" body="Real 2025/2026 car telemetry from OpenF1 (~4 Hz) and cached FastF1 sessions, with track position and tyre data. Synthetic traces are always labelled." stat="OpenF1 · FastF1" />
            <FeatureCard icon={Database} title="OpenCLIP Embedding"    body="Waveform PNG crops encoded via OpenCLIP ViT-B/32 into 512-dimensional unit-sphere vectors for semantic similarity search."               stat="ViT-B-32 · 512-dim" />
            <FeatureCard icon={Shield}   title="FAISS Vector Search"   body="IndexFlatIP inner product similarity over the cosine-normalized embedding space for deterministic nearest-neighbor precedent retrieval."     stat="IndexFlatIP · Cosine Sim" />
            <FeatureCard icon={Cpu}      title="Hallucination Failsafe" body="A 0.65 confidence threshold gate rejects low-certainty model outputs before they surface to the engineer. Zero ungrounded diagnoses."       stat="0.65 Threshold" />
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────── */}
      <section
        className="py-24 relative overflow-hidden"
        style={{ background: 'var(--bg-surface-1)', borderTop: '1px solid var(--border-dim)' }}
      >
        <div className="absolute inset-0 telemetry-grid-bg opacity-30" />
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 50% 50% at 50% 50%, rgba(232,255,0,0.05) 0%, transparent 70%)' }}
        />
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 text-center flex flex-col items-center gap-6">
          <div
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-black tracking-[0.1em] uppercase"
            style={{ border: '1px solid rgba(232,255,0,0.3)', background: 'rgba(232,255,0,0.06)', color: '#E8FF00', fontFamily: "'JetBrains Mono', monospace" }}
          >
            <span className="live-beacon beacon-f1" />
            System Ready
          </div>
          <h2
            className="text-[42px] sm:text-[56px] font-bold leading-none"
            style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)', letterSpacing: '-0.03em' }}
          >
            Ready to Analyze?
          </h2>
          <p className="text-[15px] max-w-md" style={{ color: 'var(--text-secondary)' }}>
            Launch the F1 workspace and start cropping anomaly windows on live telemetry.
          </p>
          <button
            type="button"
            onClick={onLaunch}
            className="flex items-center gap-2 px-8 py-4 rounded-xl font-bold text-[15px] cursor-pointer"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              background: '#E8FF00',
              color: '#000',
              border: 'none',
              letterSpacing: '0.02em',
            }}
            onMouseEnter={e => gsap.to(e.currentTarget, { scale: 1.03, boxShadow: '0 0 40px rgba(232,255,0,0.45)', duration: 0.2 })}
            onMouseLeave={e => gsap.to(e.currentTarget, { scale: 1, boxShadow: 'none', duration: 0.2 })}
          >
            <Flag size={16} />
            <span>Launch F1 Workspace</span>
            <ArrowUpRight size={15} />
          </button>
        </div>
      </section>
    </div>
  )
}
