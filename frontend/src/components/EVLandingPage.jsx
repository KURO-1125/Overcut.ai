import React, { useEffect, useRef } from 'react'
import gsap from 'gsap'
import ScrollTrigger from 'gsap/ScrollTrigger'
import {
  ArrowLeft, Zap, Battery, Activity, AlertTriangle,
  Shield, Database, ArrowUpRight,
} from 'lucide-react'

// ScrollTrigger is registered once at app root (main.jsx) — do not re-register here
// Smooth scroll is managed by the app-level Lenis instance in App.jsx

// ── Battery Hero SVG (upgraded) ───────────────────────────────────
function BatteryHeroSVG() {
  return (
    <svg
      viewBox="0 0 760 240"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className="w-full max-w-3xl mx-auto"
      style={{ height: '240px' }}
    >
      {/* Outer pack */}
      <rect x="20" y="20" width="720" height="200" rx="10" stroke="var(--border-bright)" strokeWidth="1.5" fill="none" />
      <rect x="740" y="90" width="18" height="60" rx="4" stroke="var(--border-bright)" strokeWidth="1" fill="none" />

      {/* Module dividers */}
      {[200, 380, 560].map(x => (
        <line key={x} x1={x} y1="20" x2={x} y2="220" stroke="var(--border-mid)" strokeWidth="1" />
      ))}

      {/* Module labels */}
      {['MOD-1', 'MOD-2', 'MOD-3 ⚡', 'MOD-4'].map((label, i) => (
        <text
          key={label}
          x={110 + i * 180}
          y="38"
          textAnchor="middle"
          fill={i === 2 ? '#00FF88' : 'var(--text-disabled)'}
          fontSize="9"
          fontFamily="'JetBrains Mono', monospace"
          fontWeight={i === 2 ? '600' : '400'}
        >
          {label}
        </text>
      ))}

      {/* Normal modules */}
      {[0, 1, 3].map(mod =>
        [0, 1, 2, 3, 4, 5].map(cell => (
          <circle
            key={`${mod}-${cell}`}
            cx={70 + mod * 180 + (cell % 2) * 50}
            cy={80 + Math.floor(cell / 2) * 46}
            r="16"
            fill="none"
            stroke={mod === 1 ? 'var(--border-bright)' : 'var(--border-mid)'}
            strokeWidth="1"
          />
        ))
      )}

      {/* Fault module (3) */}
      {[0, 1, 2, 3, 4, 5].map(cell => {
        const isFault = cell === 2
        return (
          <circle
            key={`fault-${cell}`}
            cx={430 + (cell % 2) * 50}
            cy={80 + Math.floor(cell / 2) * 46}
            r={isFault ? 18 : 16}
            fill={isFault ? 'rgba(0,255,136,0.12)' : 'none'}
            stroke={isFault ? '#00FF88' : 'rgba(0,255,136,0.4)'}
            strokeWidth={isFault ? 2 : 1}
          />
        )
      })}

      {/* Fault annotation */}
      <line x1="480" y1="126" x2="540" y2="88" stroke="#00FF88" strokeWidth="1" strokeDasharray="3 3" />
      <circle cx="540" cy="86" r="2" fill="#00FF88" />
      <text x="545" y="82" fill="#00FF88" fontSize="8" fontFamily="'JetBrains Mono', monospace">Vsag</text>
      <text x="545" y="93" fill="#00FF88" fontSize="8" fontFamily="'JetBrains Mono', monospace">-340mV</text>

      {/* Thermal heat bars */}
      {[0, 1, 2, 3].map(mod => {
        const heat = [0.2, 0.3, 0.9, 0.15][mod]
        const color = mod === 2 ? '#00FF88' : `rgba(0,255,136,${heat * 0.5})`
        return (
          <rect
            key={`heat-${mod}`}
            x={25 + mod * 180}
            y={215 - heat * 15}
            width="170"
            height={heat * 15}
            fill={color}
            opacity="0.35"
            rx="2"
          />
        )
      })}

      <text x="395" y="232" fill="var(--ev-signal)" fontSize="8" fontFamily="'JetBrains Mono', monospace" textAnchor="middle">
        HIGH THERMAL LOAD · MOD-3
      </text>
    </svg>
  )
}

// ── Voltage Wave background ───────────────────────────────────────
function VoltageWaveSVG() {
  return (
    <svg
      viewBox="0 0 1200 140"
      preserveAspectRatio="none"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className="w-full"
      style={{ height: '140px' }}
    >
      {/* Fill */}
      <path
        d="M 0 70 C 60 70 80 35 120 35 C 160 35 180 70 220 75 C 280 82 300 45 350 40 C 400 35 420 70 460 72 C 500 74 520 40 570 28 C 620 18 650 62 700 70 C 750 75 780 40 830 24 C 880 8 900 60 940 72 C 980 82 1000 44 1050 34 C 1100 24 1130 68 1200 62 L 1200 140 L 0 140 Z"
        fill="rgba(0,255,136,0.04)"
      />
      {/* Line */}
      <path
        d="M 0 70 C 60 70 80 35 120 35 C 160 35 180 70 220 75 C 280 82 300 45 350 40 C 400 35 420 70 460 72 C 500 74 520 40 570 28 C 620 18 650 62 700 70 C 750 75 780 40 830 24 C 880 8 900 60 940 72 C 980 82 1000 44 1050 34 C 1100 24 1130 68 1200 62"
        stroke="#00FF88"
        strokeWidth="1.5"
        fill="none"
      />
      {/* Sag window */}
      <rect x="790" y="8" width="160" height="124" fill="rgba(0,255,136,0.04)" stroke="#00FF88" strokeWidth="1" strokeDasharray="3 4" rx="2" />
      <text x="870" y="136" textAnchor="middle" fill="#00FF88" fontSize="8" fontFamily="'JetBrains Mono', monospace" letterSpacing="0.08em">VOLTAGE SAG</text>
      {/* Grid */}
      {[35, 70, 105].map(y => (
        <line key={y} x1="0" y1={y} x2="1200" y2={y} stroke="var(--border-dim)" strokeWidth="0.4" strokeDasharray="4 10" />
      ))}
    </svg>
  )
}

// ── Step Card ─────────────────────────────────────────────────────
function StepCard({ number, icon: Icon, title, body }) {
  const ref = useRef(null)
  return (
    <div
      ref={ref}
      className="ev-step relative flex flex-col gap-4 p-6 rounded-xl overflow-hidden"
      style={{
        background: 'var(--bg-surface-2)',
        border: '1px solid var(--border-mid)',
        opacity: 0,
        transform: 'translateY(40px)',
        willChange: 'transform, opacity',
      }}
      onMouseEnter={() => gsap.to(ref.current, { borderColor: 'rgba(0,255,136,0.25)', y: -3, duration: 0.25, ease: 'power2.out' })}
      onMouseLeave={() => gsap.to(ref.current, { borderColor: 'var(--border-mid)',    y:  0, duration: 0.25, ease: 'power2.out' })}
    >
      <div
        className="absolute top-0 left-0 right-0 h-[1px]"
        style={{ background: 'linear-gradient(to right, transparent, rgba(0,255,136,0.4), transparent)' }}
      />
      <div className="flex items-center gap-3">
        <span
          className="text-[11px] font-black"
          style={{ color: 'rgba(0,255,136,0.3)', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.08em' }}
        >
          {String(number).padStart(2, '0')}
        </span>
        <div
          className="w-10 h-10 flex items-center justify-center rounded-xl"
          style={{ border: '1px solid rgba(0,255,136,0.3)', background: 'rgba(0,255,136,0.06)' }}
        >
          <Icon size={18} style={{ color: '#00FF88' }} />
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
      className="ev-feat relative flex flex-col gap-3 p-5 rounded-xl overflow-hidden"
      style={{
        background: 'var(--bg-surface-2)',
        border: '1px solid var(--border-mid)',
        opacity: 0,
        transform: 'translateY(40px)',
        willChange: 'transform, opacity',
      }}
      onMouseEnter={() => gsap.to(ref.current, { borderColor: 'rgba(0,255,136,0.3)', y: -2, duration: 0.2, ease: 'power2.out' })}
      onMouseLeave={() => gsap.to(ref.current, { borderColor: 'var(--border-mid)',   y:  0, duration: 0.2, ease: 'power2.out' })}
    >
      <div
        className="absolute top-0 left-0 right-0 h-[1px]"
        style={{ background: 'linear-gradient(to right, transparent, rgba(0,255,136,0.3), transparent)' }}
      />
      <div
        className="w-9 h-9 flex items-center justify-center rounded-lg"
        style={{ border: '1px solid rgba(0,255,136,0.25)', background: 'rgba(0,255,136,0.06)' }}
      >
        <Icon size={16} style={{ color: '#00FF88' }} />
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
        <span className="w-1 h-1 rounded-full" style={{ background: '#00FF88' }} />
        <span
          className="text-[10px] font-semibold"
          style={{ color: '#00FF88', fontFamily: "'JetBrains Mono', monospace" }}
        >
          {stat}
        </span>
      </div>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────
export default function EVLandingPage({ onLaunch, onBack }) {
  const containerRef = useRef(null)
  const stepsRef     = useRef(null)
  const featsRef     = useRef(null)
  // Smooth scroll is managed by the app-level Lenis instance in App.jsx

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from('.ev-hero-title',   { y: 50, opacity: 0, duration: 0.8, ease: 'power3.out', delay: 0.1 })
      gsap.from('.ev-hero-sub',     { y: 30, opacity: 0, duration: 0.7, ease: 'power3.out', delay: 0.3 })
      gsap.from('.ev-hero-stats',   { y: 20, opacity: 0, duration: 0.6, ease: 'power3.out', delay: 0.5 })
      gsap.from('.ev-battery-svg',  { opacity: 0, scale: 0.97, duration: 0.9, ease: 'power3.out', delay: 0.2 })

      ScrollTrigger.create({
        trigger: stepsRef.current,
        start: 'top 80%',
        onEnter: () => gsap.to('.ev-step', { opacity: 1, y: 0, duration: 0.65, stagger: 0.1, ease: 'power3.out' }),
      })
      ScrollTrigger.create({
        trigger: featsRef.current,
        start: 'top 80%',
        onEnter: () => gsap.to('.ev-feat', { opacity: 1, y: 0, duration: 0.65, stagger: 0.08, ease: 'power3.out' }),
      })
    }, containerRef)
    return () => ctx.revert()
  }, [])

  const STATS = [
    { icon: Zap,           value: '50',   unit: 'Hz',  label: 'Pack Resolution' },
    { icon: AlertTriangle, value: '4',    unit: '',    label: 'Anomaly Profiles' },
    { icon: Database,      value: 'B0005', unit: '',   label: 'NASA PCoE Dataset' },
    { icon: Shield,        value: 'DTC',  unit: '',    label: 'Fault Code Output' },
  ]

  return (
    <div ref={containerRef} className="flex flex-col">

      {/* ── Hero ──────────────────────────────────────────────── */}
      <section
        className="relative pt-14 pb-8 overflow-hidden"
        style={{ background: 'var(--bg-floor)', minHeight: '70vh' }}
      >
        <div className="absolute bottom-0 left-0 right-0 overflow-hidden" style={{ opacity: 0.5 }}>
          <VoltageWaveSVG />
        </div>
        <div className="absolute inset-0 telemetry-grid-bg opacity-20" />
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 60% 60% at 50% 30%, rgba(0,255,136,0.04) 0%, transparent 70%)' }}
        />

        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 flex flex-col items-center text-center gap-6">

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

          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-full text-[10px] font-black tracking-[0.1em] uppercase"
            style={{
              border: '1px solid rgba(0,255,136,0.3)',
              background: 'rgba(0,255,136,0.06)',
              color: '#00FF88',
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            <span className="live-beacon" />
            EV FLEET MODE
          </div>

          <h1
            className="ev-hero-title display-title"
            style={{
              fontSize: 'clamp(36px, 6vw, 70px)',
              color: 'var(--text-bright)',
              letterSpacing: '-0.03em',
              maxWidth: '700px',
              willChange: 'transform, opacity',
            }}
          >
            EV Fleet<br />
            <span style={{ color: '#00FF88' }}>Battery Analytics</span>
          </h1>

          <p
            className="ev-hero-sub text-[15px] leading-relaxed max-w-xl"
            style={{ color: 'var(--text-secondary)', fontFamily: "'Inter', sans-serif", willChange: 'transform, opacity' }}
          >
            Real-time pack health monitoring, cell-level fault isolation, and thermal runaway detection.
            Synthetic cycles parameterised against NASA Ames Li-ion degradation profiles, with optional on-device AI.
          </p>

          {/* CTAs */}
          <div className="ev-hero-sub flex flex-wrap justify-center gap-4">
            <button
              type="button"
              onClick={onLaunch}
              className="flex items-center gap-2 px-7 py-3.5 rounded-xl font-bold text-[14px] cursor-pointer"
              style={{
                fontFamily: "'Space Grotesk', sans-serif",
                background: '#00FF88',
                color: '#000',
                border: 'none',
                letterSpacing: '0.02em',
                willChange: 'transform',
              }}
              onMouseEnter={e => gsap.to(e.currentTarget, { scale: 1.03, boxShadow: '0 0 32px rgba(0,255,136,0.4)', duration: 0.2 })}
              onMouseLeave={e => gsap.to(e.currentTarget, { scale: 1, boxShadow: 'none', duration: 0.2 })}
            >
              <Battery size={15} />
              <span>Launch EV Workspace</span>
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

          {/* Battery illustration */}
          <div className="ev-battery-svg w-full mt-4" style={{ willChange: 'transform, opacity' }}>
            <BatteryHeroSVG />
          </div>

          {/* Stats row */}
          <div
            className="ev-hero-stats w-full max-w-3xl grid grid-cols-2 md:grid-cols-4 gap-3"
            style={{ willChange: 'transform, opacity' }}
          >
            {STATS.map(({ icon: Icon, value, unit, label }) => (
              <div
                key={label}
                className="flex flex-col items-center gap-1 p-4 rounded-xl"
                style={{ background: 'rgba(8,12,16,0.8)', border: '1px solid var(--border-mid)', backdropFilter: 'blur(8px)' }}
              >
                <Icon size={14} style={{ color: 'rgba(0,255,136,0.5)' }} />
                <div className="flex items-baseline gap-1">
                  <span
                    className="text-[20px] font-black"
                    style={{ fontFamily: "'Space Grotesk', sans-serif", color: '#00FF88', lineHeight: 1 }}
                  >
                    {value}
                  </span>
                  {unit && (
                    <span
                      className="text-[12px] font-bold"
                      style={{ color: 'rgba(0,255,136,0.6)', fontFamily: "'JetBrains Mono', monospace" }}
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
              <span className="w-1 h-1 rounded-full" style={{ background: '#00FF88' }} />
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
            <StepCard number={1} icon={Battery}       title="Select Pack Cycle"  body="Choose from NASA B0005/B0007 or commercial fleet NMC 811 pack profiles with injected fault signatures at 50Hz resolution." />
            <StepCard number={2} icon={Activity}      title="Isolate Window"     body="Crop a time window on the Voltage, Current, and Temperature channels to focus on the anomaly onset region for CLIP embedding." />
            <StepCard number={3} icon={AlertTriangle} title="BMS Diagnosis"      body="The AI classifies thermal runaway, cell imbalance, voltage sag, or lithium plating with DTC codes and remediation steps." />
          </div>
        </div>
      </section>

      {/* ── Feature Grid ─────────────────────────────────────────── */}
      <section
        className="py-24"
        style={{ background: 'var(--bg-surface-1)', borderTop: '1px solid var(--border-dim)' }}
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
            <FeatureCard icon={Zap}      title="Butler-Volmer Physics"  body="Pack voltage and thermal response are approximated with Butler-Volmer kinetics rather than pure threshold logic." stat="Synthetic electrochemical model" />
            <FeatureCard icon={Database} title="50Hz Polars DataFrames" body="Pack telemetry is generated and processed as Polars DataFrames at 50Hz resolution." stat="Polars · 50Hz" />
            <FeatureCard icon={Shield}   title="NASA Ames Prognostics"  body="Synthetic cycles are parameterised against the NASA Ames B0005, B0006, B0007 and B0018 Li-ion degradation profiles." stat="Synthetic · NASA-referenced" />
            <FeatureCard icon={Activity} title="Pack Topology SVG Map"  body="Real-time rendered SVG battery pack topology showing cell-level health indicators, temperature gradients, and fault locations." stat="Interactive Pack Map" />
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────── */}
      <section
        className="py-24 relative overflow-hidden"
        style={{ borderTop: '1px solid var(--border-dim)' }}
      >
        <div className="absolute inset-0 telemetry-grid-bg opacity-30" />
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 50% 50% at 50% 50%, rgba(0,255,136,0.05) 0%, transparent 70%)' }}
        />
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 text-center flex flex-col items-center gap-6">
          <div
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-black tracking-[0.1em] uppercase"
            style={{ border: '1px solid rgba(0,255,136,0.3)', background: 'rgba(0,255,136,0.06)', color: '#00FF88', fontFamily: "'JetBrains Mono', monospace" }}
          >
            <span className="live-beacon" />
            System Ready
          </div>
          <h2
            className="text-[42px] sm:text-[56px] font-bold leading-none"
            style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)', letterSpacing: '-0.03em' }}
          >
            Ready to Analyze?
          </h2>
          <p className="text-[15px] max-w-md" style={{ color: 'var(--text-secondary)' }}>
            Launch the EV workspace and start isolating fault signatures in battery pack telemetry.
          </p>
          <button
            type="button"
            onClick={onLaunch}
            className="flex items-center gap-2 px-8 py-4 rounded-xl font-bold text-[15px] cursor-pointer"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              background: '#00FF88',
              color: '#000',
              border: 'none',
              letterSpacing: '0.02em',
            }}
            onMouseEnter={e => gsap.to(e.currentTarget, { scale: 1.03, boxShadow: '0 0 40px rgba(0,255,136,0.45)', duration: 0.2 })}
            onMouseLeave={e => gsap.to(e.currentTarget, { scale: 1, boxShadow: 'none', duration: 0.2 })}
          >
            <Battery size={16} />
            <span>Launch EV Workspace</span>
            <ArrowUpRight size={15} />
          </button>
        </div>
      </section>
    </div>
  )
}
