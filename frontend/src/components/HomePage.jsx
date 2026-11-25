import React, { useEffect, useRef } from 'react'
import gsap from 'gsap'
import ScrollTrigger from 'gsap/ScrollTrigger'
import {
  Activity, Database, Cpu, Shield, BarChart2, Globe,
  ArrowRight, ChevronDown, Flag, Zap, Map, GitBranch,
  Battery, Thermometer, ShieldCheck, ArrowUpRight,
} from 'lucide-react'

// ScrollTrigger is registered once at app root (main.jsx) — do not re-register here
// Smooth scroll is managed by the app-level Lenis instance in App.jsx

// ── Animated Grid SVG Background ──────────────────────────────────
function GridBackground() {
  return (
    <div
      className="absolute inset-0 pointer-events-none"
      aria-hidden="true"
      style={{ opacity: 0.4 }}
    >
      {/* Telemetry grid */}
      <div className="absolute inset-0 telemetry-grid-bg" />
      {/* Radial vignette to fade grid edges */}
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse 70% 60% at 50% 50%, transparent 0%, var(--bg-floor) 100%)',
        }}
      />
    </div>
  )
}

// ── Constellation SVG ─────────────────────────────────────────────
function ConstellationSVG() {
  const svgRef = useRef(null)

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.to(svgRef.current, {
        rotation: 360,
        duration: 120,
        ease: 'none',
        repeat: -1,
        transformOrigin: '50% 50%',
      })
      // Pulsing glow nodes
      gsap.to('.node-bright', {
        opacity: 0.4,
        scale: 0.9,
        duration: 2.5,
        ease: 'sine.inOut',
        repeat: -1,
        yoyo: true,
        stagger: 0.6,
        transformOrigin: 'center',
      })
    }, svgRef)
    return () => ctx.revert()
  }, [])

  const nodes = [
    { cx: 240, cy: 240, r: 7,   bright: true  },
    { cx: 120, cy: 100, r: 3.5, bright: false },
    { cx: 360, cy: 90,  r: 4.5, bright: true  },
    { cx: 400, cy: 200, r: 2.5, bright: false },
    { cx: 350, cy: 350, r: 5.5, bright: true  },
    { cx: 160, cy: 380, r: 3,   bright: false },
    { cx: 80,  cy: 260, r: 2.5, bright: false },
    { cx: 300, cy: 160, r: 3.5, bright: false },
    { cx: 180, cy: 200, r: 4.5, bright: true  },
    { cx: 420, cy: 320, r: 2,   bright: false },
    { cx: 60,  cy: 150, r: 2,   bright: false },
    { cx: 440, cy: 140, r: 3,   bright: false },
    { cx: 200, cy: 320, r: 3,   bright: false },
    { cx: 310, cy: 420, r: 3.5, bright: false },
    { cx: 140, cy: 300, r: 2,   bright: false },
    { cx: 380, cy: 260, r: 2.5, bright: false },
    { cx: 260, cy: 60,  r: 2,   bright: false },
    { cx: 100, cy: 400, r: 2,   bright: false },
    { cx: 460, cy: 400, r: 2,   bright: false },
    { cx: 240, cy: 400, r: 2.5, bright: false },
  ]
  const edges = [
    [0,1],[0,2],[0,8],[0,4],[0,5],
    [1,7],[1,6],[2,3],[2,11],[3,9],
    [4,9],[4,13],[5,14],[5,12],
    [7,8],[8,12],[6,14],[10,1],
    [11,16],[13,18],[15,3],[17,5],[19,13],
  ]

  return (
    <svg
      ref={svgRef}
      viewBox="0 0 480 480"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className="w-full h-full"
      style={{ willChange: 'transform' }}
    >
      <defs>
        <radialGradient id="nodeGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#00D4FF" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#00D4FF" stopOpacity="0" />
        </radialGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {/* Connection lines */}
      {edges.map(([a, b], i) => (
        <line
          key={i}
          x1={nodes[a].cx} y1={nodes[a].cy}
          x2={nodes[b].cx} y2={nodes[b].cy}
          stroke="var(--border-mid)"
          strokeWidth="0.6"
          opacity="0.7"
        />
      ))}

      {/* Glow halos on bright nodes */}
      {nodes.filter(n => n.bright).map((n, i) => (
        <circle
          key={`halo-${i}`}
          cx={n.cx} cy={n.cy}
          r={n.r * 4}
          fill="url(#nodeGlow)"
          opacity="0.15"
        />
      ))}

      {/* Nodes */}
      {nodes.map((n, i) => (
        <circle
          key={i}
          cx={n.cx} cy={n.cy}
          r={n.r}
          fill={n.bright ? 'var(--accent)' : 'var(--border-bright)'}
          opacity={n.bright ? 1 : 0.5}
          className={n.bright ? 'node-bright' : ''}
          filter={n.bright ? 'url(#glow)' : undefined}
        />
      ))}

      {/* Central "O" glyph — multi-ring */}
      <circle cx="240" cy="240" r="40" stroke="var(--accent)" strokeWidth="1" fill="none" opacity="0.12" />
      <circle cx="240" cy="240" r="28" stroke="var(--accent)" strokeWidth="1.5" fill="none" opacity="0.3" />
      <circle cx="240" cy="240" r="16" stroke="var(--accent)" strokeWidth="1" fill="none" opacity="0.2" />
      <text
        x="240" y="246"
        textAnchor="middle"
        fill="var(--accent)"
        fontSize="20"
        fontFamily="'Space Grotesk', sans-serif"
        fontWeight="700"
        opacity="0.8"
      >
        O
      </text>
    </svg>
  )
}

// ── Telemetry Ticker ──────────────────────────────────────────────
const TICKER_ITEMS = [
  { label: 'HAM · Monaco Q3', value: '+0.183s' },
  { label: 'VER · Sector 2', value: '34.218s' },
  { label: 'NASA B0005 · SOH', value: '72.4%' },
  { label: 'NOR · T1 Brake', value: '98%' },
  { label: 'LEC · Apex Speed', value: '68.4 km/h' },
  { label: 'Fleet Pack B · Temp', value: '61.2°C' },
  { label: 'VER · Full Lap', value: '1:10.457' },
  { label: 'EV Fleet C · ΔV', value: '340mV' },
]

function TelemetryTicker() {
  return (
    <div
      className="ticker-wrap py-2 overflow-hidden"
      style={{ borderTop: '1px solid var(--border-dim)', borderBottom: '1px solid var(--border-dim)' }}
      aria-hidden="true"
    >
      <div className="ticker-track">
        {[...TICKER_ITEMS, ...TICKER_ITEMS].map((item, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-2 text-[10px]"
            style={{ fontFamily: "'JetBrains Mono', monospace" }}
          >
            <span
              className="w-1 h-1 rounded-full"
              style={{ background: 'var(--accent)', flexShrink: 0 }}
            />
            <span style={{ color: 'var(--text-muted)' }}>{item.label}</span>
            <span
              className="font-semibold"
              style={{ color: 'var(--text-bright)' }}
            >
              {item.value}
            </span>
          </span>
        ))}
      </div>
    </div>
  )
}

// ── Bento Feature Card ────────────────────────────────────────────
function BentoCard({ icon: Icon, title, body, accent = 'var(--accent)', className = '', stat }) {
  const cardRef = useRef(null)
  return (
    <div
      ref={cardRef}
      className={`bento-card relative flex flex-col gap-3 p-5 rounded-xl overflow-hidden transition-all duration-300 ${className}`}
      style={{
        background: 'var(--bg-surface-1)',
        border: '1px solid var(--border-dim)',
        willChange: 'transform, opacity',
      }}
      onMouseEnter={() => {
        gsap.to(cardRef.current, {
          y: -3,
          borderColor: accent + '40',
          boxShadow: `0 8px 32px ${accent}12`,
          duration: 0.25,
          ease: 'power2.out',
        })
      }}
      onMouseLeave={() => {
        gsap.to(cardRef.current, {
          y: 0,
          borderColor: 'var(--border-dim)',
          boxShadow: 'none',
          duration: 0.25,
          ease: 'power2.out',
        })
      }}
    >
      {/* Top glow accent bar */}
      <div
        className="absolute top-0 left-5 right-5 h-[1px]"
        style={{ background: `linear-gradient(to right, transparent, ${accent}50, transparent)` }}
      />

      <div
        className="w-9 h-9 flex items-center justify-center rounded-lg"
        style={{
          background: `${accent}10`,
          border: `1px solid ${accent}25`,
        }}
      >
        <Icon size={16} style={{ color: accent }} />
      </div>

      <div>
        <h3
          className="text-[14px] font-semibold mb-1"
          style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-primary)' }}
        >
          {title}
        </h3>
        <p
          className="text-[12px] leading-relaxed"
          style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif" }}
        >
          {body}
        </p>
      </div>

      {stat && (
        <div
          className="mt-auto pt-3 text-[11px] font-semibold"
          style={{
            color: accent,
            fontFamily: "'JetBrains Mono', monospace",
            borderTop: '1px solid var(--border-dim)',
          }}
        >
          {stat}
        </div>
      )}
    </div>
  )
}

// ── Mode Card (premium glass version) ─────────────────────────────
function ModeCard({ signal, label, tagline, description, pills, ctaLabel, onCta, IllustrationSlot }) {
  const cardRef = useRef(null)
  const btnRef  = useRef(null)

  return (
    <div
      ref={cardRef}
      className="mode-card relative flex flex-col rounded-xl overflow-hidden"
      style={{
        background: 'var(--bg-surface-1)',
        border: `1px solid ${signal}18`,
        minHeight: '420px',
        opacity: 0,
        transform: 'translateY(40px)',
        willChange: 'transform, opacity',
      }}
      onMouseEnter={() => {
        gsap.to(cardRef.current, {
          borderColor: signal + '45',
          boxShadow: `0 0 48px ${signal}12, 0 24px 48px rgba(0,0,0,0.4)`,
          duration: 0.35,
          ease: 'power2.out',
        })
      }}
      onMouseLeave={() => {
        gsap.to(cardRef.current, {
          borderColor: signal + '18',
          boxShadow: 'none',
          duration: 0.35,
          ease: 'power2.out',
        })
      }}
    >
      {/* Top signal accent line */}
      <div
        className="absolute top-0 left-0 right-0 h-[2px]"
        style={{ background: `linear-gradient(to right, transparent 0%, ${signal}80 50%, transparent 100%)` }}
      />

      {/* Illustration */}
      <div
        className="relative p-6 overflow-hidden"
        style={{
          background: `linear-gradient(135deg, var(--bg-surface-2) 0%, ${signal}06 100%)`,
          borderBottom: `1px solid ${signal}15`,
        }}
      >
        {/* Background glow blob */}
        <div
          className="absolute inset-0 opacity-20"
          style={{ background: `radial-gradient(ellipse 60% 60% at 50% 80%, ${signal}25 0%, transparent 70%)` }}
        />
        <div className="relative z-10">
          <IllustrationSlot />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col p-6 gap-4">

        {/* Tag */}
        <div
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full self-start text-[10px] font-bold tracking-[0.08em] uppercase"
          style={{
            border: `1px solid ${signal}30`,
            background: `${signal}08`,
            color: signal,
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full glow-dot"
            style={{ background: signal }}
          />
          {tagline}
        </div>

        <h2
          className="text-[26px] font-bold leading-tight"
          style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)', letterSpacing: '-0.02em' }}
        >
          {label}
        </h2>
        <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)', fontFamily: "'Inter', sans-serif" }}>
          {description}
        </p>

        {/* Pills */}
        <div className="flex flex-wrap gap-2">
          {pills.map(({ icon: Icon, text }) => (
            <div
              key={text}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium"
              style={{
                border: `1px solid ${signal}20`,
                color: 'var(--text-muted)',
                background: 'rgba(255,255,255,0.03)',
                fontFamily: "'Inter', sans-serif",
              }}
            >
              <Icon size={10} style={{ color: signal }} />
              <span>{text}</span>
            </div>
          ))}
        </div>

        {/* CTA */}
        <button
          ref={btnRef}
          type="button"
          onClick={onCta}
          className="mt-auto w-full py-3 rounded-lg font-bold text-[13px] cursor-pointer flex items-center justify-center gap-2 transition-all"
          style={{
            fontFamily: "'Space Grotesk', sans-serif",
            background: signal,
            color: '#000',
            border: 'none',
            letterSpacing: '0.02em',
            willChange: 'transform',
          }}
          onMouseEnter={() => {
            gsap.to(btnRef.current, { scale: 1.02, boxShadow: `0 0 24px ${signal}50`, duration: 0.2 })
          }}
          onMouseLeave={() => {
            gsap.to(btnRef.current, { scale: 1, boxShadow: 'none', duration: 0.2 })
          }}
        >
          <span>{ctaLabel}</span>
          <ArrowUpRight size={14} />
        </button>
      </div>
    </div>
  )
}

// ── Circuit SVG ───────────────────────────────────────────────────
function F1CircuitSVG() {
  return (
    <svg viewBox="0 0 320 180" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" className="w-full">
      <path
        d="M 40 140 L 40 60 Q 40 30 70 30 L 180 30 Q 220 30 230 50 L 260 90 Q 270 110 250 125 L 220 140 Q 200 150 180 145 L 130 135 Q 110 130 100 145 L 80 155 Q 60 160 40 140 Z"
        stroke="#E8FF00"
        strokeWidth="2"
        fill="rgba(232,255,0,0.04)"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Animated racing car dot */}
      <circle cx="40" cy="100" r="4" fill="#E8FF00" opacity="0.9" />
      <circle cx="40" cy="100" r="8" fill="none" stroke="#E8FF00" strokeWidth="1" opacity="0.4" />
      {/* Speed vectors */}
      <line x1="70" y1="30" x2="55" y2="10" stroke="#E8FF00" strokeWidth="1" opacity="0.4" />
      <line x1="230" y1="50" x2="250" y2="35" stroke="#E8FF00" strokeWidth="1" opacity="0.4" />
      <line x1="250" y1="125" x2="270" y2="135" stroke="#E8FF00" strokeWidth="1" opacity="0.4" />
      {/* Sector labels */}
      <text x="80" y="50" fill="#E8FF00" fontSize="8" fontFamily="'JetBrains Mono', monospace" opacity="0.6">S1</text>
      <text x="210" y="75" fill="#E8FF00" fontSize="8" fontFamily="'JetBrains Mono', monospace" opacity="0.6">S2</text>
      <text x="150" y="155" fill="#E8FF00" fontSize="8" fontFamily="'JetBrains Mono', monospace" opacity="0.6">S3</text>
      {/* Start/finish */}
      <line x1="40" y1="100" x2="20" y2="100" stroke="#E8FF00" strokeWidth="2" />
    </svg>
  )
}

// ── Battery Cell SVG ──────────────────────────────────────────────
function BatteryCellSVG() {
  return (
    <svg viewBox="0 0 320 180" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" className="w-full">
      <rect x="20" y="20" width="280" height="140" rx="6" stroke="var(--border-bright)" strokeWidth="1.5" fill="none" />
      <line x1="90" y1="20" x2="90" y2="160" stroke="var(--border-mid)" strokeWidth="1" />
      <line x1="160" y1="20" x2="160" y2="160" stroke="var(--border-mid)" strokeWidth="1" />
      <line x1="230" y1="20" x2="230" y2="160" stroke="var(--border-mid)" strokeWidth="1" />
      {[0, 1, 2, 3].map(mod => mod !== 2 && [0, 1, 2, 3, 4, 5].map(cell => (
        <circle
          key={`${mod}-${cell}`}
          cx={35 + mod * 70 + (cell % 2) * 24}
          cy={40 + Math.floor(cell / 2) * 36}
          r="8"
          fill="none"
          stroke="var(--border-mid)"
          strokeWidth="1"
        />
      )))}
      {[0, 1, 2, 3, 4, 5].map(cell => (
        <circle
          key={`fault-${cell}`}
          cx={175 + (cell % 2) * 24}
          cy={40 + Math.floor(cell / 2) * 36}
          r="8"
          fill={cell === 2 ? 'rgba(0,255,136,0.18)' : 'none'}
          stroke={cell === 2 ? '#00FF88' : 'var(--ev-signal)'}
          strokeWidth={cell === 2 ? 2 : 1}
        />
      ))}
      {/* Fault indicator */}
      <line x1="175" y1="76" x2="195" y2="58" stroke="#00FF88" strokeWidth="1" strokeDasharray="2 2" opacity="0.7" />
      <text x="197" y="56" fill="#00FF88" fontSize="8" fontFamily="'JetBrains Mono', monospace">-340mV</text>
      <text x="165" y="168" fill="var(--ev-signal)" fontSize="7.5" fontFamily="'JetBrains Mono', monospace">MOD-3 · CELL IMBALANCE FAULT</text>
    </svg>
  )
}

// ── Main HomePage ─────────────────────────────────────────────────
export default function HomePage({ onNavigate }) {
  const containerRef = useRef(null)
  const modesRef     = useRef(null)
  const bentoRef     = useRef(null)
  // Smooth scroll is handled by the app-level Lenis instance in App.jsx

  // GSAP entrance + scroll animations
  useEffect(() => {
    const ctx = gsap.context(() => {
      // Hero text
      gsap.from('.hero-eyebrow', { y: 20, opacity: 0, duration: 0.6, ease: 'power3.out', delay: 0.1 })
      gsap.from('.hero-line',    { y: 60, opacity: 0, duration: 0.8, stagger: 0.1, ease: 'power3.out', delay: 0.2 })
      gsap.from('.hero-sub',     { y: 30, opacity: 0, duration: 0.7, ease: 'power3.out', delay: 0.55 })
      gsap.from('.hero-btns',    { y: 20, opacity: 0, duration: 0.6, ease: 'power3.out', delay: 0.7 })
      gsap.from('.hero-svg',     { opacity: 0, scale: 0.92, duration: 1.2, ease: 'power3.out', delay: 0.25 })
      gsap.from('.hero-stats',   { y: 20, opacity: 0, duration: 0.6, ease: 'power3.out', delay: 0.85 })

      // Mode cards
      ScrollTrigger.create({
        trigger: modesRef.current,
        start: 'top 80%',
        onEnter: () => {
          gsap.to('.mode-card', { opacity: 1, y: 0, duration: 0.75, stagger: 0.15, ease: 'power3.out' })
        },
      })

      // Bento cards
      ScrollTrigger.create({
        trigger: bentoRef.current,
        start: 'top 80%',
        onEnter: () => {
          gsap.from('.bento-card', { opacity: 0, y: 32, duration: 0.65, stagger: 0.07, ease: 'power3.out' })
        },
      })
    }, containerRef)
    return () => ctx.revert()
  }, [])

  const scrollToModes = () => {
    const el = document.getElementById('modes')
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const HERO_STATS = [
    { value: '~4Hz', label: 'Real F1 Feed' },
    { value: 'GPU',   label: 'Local Inference' },
    { value: '7B',    label: 'QLoRA Model' },
    { value: '0.65',  label: 'Confidence Gate' },
  ]

  const FEATURES = [
    {
      icon: Activity,
      title: 'Real Telemetry Pipeline',
      body: 'Real 2025/2026 car telemetry at ~4 Hz (OpenF1 or cached FastF1), rendered on a high-resolution canvas and labelled when synthetic.',
      stat: 'OpenF1 · FastF1',
    },
    {
      icon: Database,
      title: 'FAISS Vector Retrieval',
      body: 'OpenCLIP ViT-B/32 embeddings in FAISS for cosine-similarity precedent lookup.',
      stat: 'ViT-B/32 · 512-dim',
    },
    {
      icon: Cpu,
      title: 'Optional 7B QLoRA Adapter',
      body: 'Qwen2.5-7B with a telemetry QLoRA adapter, loaded on-device when CUDA and the adapter are present.',
      stat: 'CUDA · 4-bit',
    },
    {
      icon: Shield,
      title: 'Anti-Hallucination Failsafe',
      body: '0.65 confidence gate rejects low-certainty outputs before they reach the pit wall.',
      stat: 'Zero Ungrounded Output',
    },
    {
      icon: BarChart2,
      title: 'Dual-Driver Delta Analysis',
      body: 'Side-by-side telemetry comparison with continuous micro-sector delta-time visualization.',
      stat: 'Ghost Car Overlay',
    },
    {
      icon: Globe,
      title: 'Multi-Domain Support',
      body: 'Formula 1 lap telemetry and EV battery pack health from NASA Ames and fleet data.',
      stat: 'F1 · EV · NASA',
    },
  ]

  return (
    <div ref={containerRef} className="flex flex-col">

      {/* ── Scanline overlay ─────────────────────────────────────── */}
      <div className="scanline-overlay pointer-events-none" aria-hidden="true" />

      {/* ── Hero ─────────────────────────────────────────────────── */}
      <section
        id="hero"
        className="relative min-h-[calc(100vh-56px)] flex items-center overflow-hidden"
        style={{ padding: '80px 0 60px' }}
      >
        <GridBackground />

        <div className="relative z-10 w-full max-w-7xl mx-auto px-4 sm:px-6 flex flex-col lg:flex-row items-center gap-12 lg:gap-20">

          {/* Left: Text */}
          <div className="flex-1 flex flex-col gap-6 lg:gap-7">

            {/* Eyebrow */}
            <div
              className="hero-eyebrow inline-flex items-center gap-2 self-start px-3 py-1.5 rounded-full"
              style={{
                border: '1px solid var(--border-mid)',
                background: 'rgba(0,212,255,0.06)',
              }}
            >
              <span className="live-beacon beacon-accent" />
              <span
                className="text-[10px] font-bold tracking-[0.18em] uppercase"
                style={{ color: 'var(--accent)', fontFamily: "'JetBrains Mono', monospace" }}
              >
                Multimodal Telemetry AI
              </span>
            </div>

            {/* Headline */}
            <div className="flex flex-col">
              {['Precision', 'Diagnostics.', 'At Race Speed.'].map((line, i) => (
                <h1
                  key={i}
                  className="hero-line display-title block leading-[0.95]"
                  style={{
                    fontSize: 'clamp(48px, 7vw, 86px)',
                    color: i === 1 ? 'var(--accent)' : 'var(--text-bright)',
                    willChange: 'transform, opacity',
                    letterSpacing: '-0.03em',
                  }}
                >
                  {line}
                </h1>
              ))}
            </div>

            {/* Subtext */}
            <p
              className="hero-sub text-[15px] leading-relaxed max-w-[460px]"
              style={{ color: 'var(--text-secondary)', fontFamily: "'Inter', sans-serif", willChange: 'transform, opacity' }}
            >
              The first multimodal AI platform for motorsport engineers and EV battery specialists.
              Drag a window on the telemetry waveform and get a structured engineering diagnosis grounded in retrieved precedent.
            </p>

            {/* CTAs */}
            <div className="hero-btns flex flex-wrap gap-3" style={{ willChange: 'transform, opacity' }}>
              <button
                type="button"
                onClick={scrollToModes}
                className="btn-primary flex items-center gap-2"
              >
                <span>Explore Platform</span>
                <ChevronDown size={14} />
              </button>
              <button
                type="button"
                onClick={() => onNavigate('workspace')}
                className="btn-ghost flex items-center gap-2"
              >
                <span>Launch Workspace</span>
                <ArrowRight size={14} />
              </button>
            </div>

            {/* Stats row */}
            <div
              className="hero-stats grid grid-cols-4 gap-3 max-w-[400px]"
              style={{ willChange: 'transform, opacity' }}
            >
              {HERO_STATS.map(({ value, label }) => (
                <div
                  key={value}
                  className="flex flex-col items-center gap-1 p-3 rounded-lg text-center"
                  style={{ background: 'var(--bg-surface-1)', border: '1px solid var(--border-dim)' }}
                >
                  <span
                    className="text-[18px] font-bold"
                    style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--accent)' }}
                  >
                    {value}
                  </span>
                  <span
                    className="text-[9px] leading-tight"
                    style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
                  >
                    {label}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Constellation */}
          <div
            className="hero-svg flex-1 flex items-center justify-center max-w-[460px] w-full aspect-square"
            style={{ willChange: 'transform, opacity' }}
          >
            <div className="relative w-full h-full">
              {/* Outer glow halo */}
              <div
                className="absolute inset-0"
                style={{ background: 'radial-gradient(ellipse 50% 50% at 50% 50%, rgba(0,212,255,0.08) 0%, transparent 70%)' }}
              />
              <ConstellationSVG />
            </div>
          </div>
        </div>

        {/* Scroll indicator */}
        <button
          type="button"
          className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1.5 cursor-pointer transition-opacity hover:opacity-70"
          onClick={scrollToModes}
          style={{ background: 'none', border: 'none' }}
        >
          <span
            className="text-[9px] tracking-[0.18em] uppercase"
            style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
          >
            Scroll
          </span>
          <div
            className="w-5 h-8 rounded-full flex items-start justify-center pt-1.5"
            style={{ border: '1px solid var(--border-mid)' }}
          >
            <div
              className="w-1 h-2 rounded-full"
              style={{ background: 'var(--accent)' }}
            />
          </div>
        </button>
      </section>

      {/* ── Live Telemetry Ticker ────────────────────────────────── */}
      <TelemetryTicker />

      {/* ── Mode Cards ───────────────────────────────────────────── */}
      <section id="modes" ref={modesRef} className="py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">

          <div className="text-center mb-14">
            {/* Section eyebrow */}
            <div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full mb-4 text-[10px] font-bold tracking-[0.15em] uppercase"
              style={{
                border: '1px solid var(--border-mid)',
                color: 'var(--text-muted)',
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              <span className="w-1 h-1 rounded-full" style={{ background: 'var(--accent)' }} />
              Choose Your Domain
            </div>
            <h2
              className="text-[38px] sm:text-[48px] font-bold mb-3"
              style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)', letterSpacing: '-0.03em' }}
            >
              Two Specialized Engines.
            </h2>
            <p className="text-[15px] max-w-md mx-auto" style={{ color: 'var(--text-muted)' }}>
              The same AI infrastructure, purpose-built for each domain's unique telemetry signature.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ModeCard
              signal="#E8FF00"
              label="Formula 1 Intelligence"
              tagline="F1 Motorsport · OpenF1"
              description="Real lap telemetry. Micro-sector anomaly detection. Dual-driver delta-T ghost car overlay across the FIA calendars."
              pills={[
                { icon: Activity,  text: 'Real F1 Telemetry' },
                { icon: GitBranch, text: 'Delta-T Analysis' },
                { icon: Map,       text: '24 FIA Circuits' },
                { icon: Cpu,       text: 'Local 7B VLM (optional)' },
              ]}
              ctaLabel="Enter F1 Intelligence"
              onCta={() => onNavigate('f1-landing')}
              IllustrationSlot={F1CircuitSVG}
            />
            <ModeCard
              signal="#00FF88"
              label="EV Fleet Analytics"
              tagline="EV Battery · 50Hz"
              description="50Hz pack telemetry. Cell-level fault isolation. Thermal runaway detection across NASA Ames and commercial fleet data."
              pills={[
                { icon: Zap,         text: '50Hz Pack Data' },
                { icon: Thermometer, text: 'Thermal Analysis' },
                { icon: Battery,     text: 'Cell Isolation' },
                { icon: ShieldCheck, text: 'Anti-Hallucination' },
              ]}
              ctaLabel="Enter EV Analytics"
              onCta={() => onNavigate('ev-landing')}
              IllustrationSlot={BatteryCellSVG}
            />
          </div>
        </div>
      </section>

      {/* ── Capabilities Bento ───────────────────────────────────── */}
      <section
        id="capabilities"
        ref={bentoRef}
        className="py-24"
        style={{ borderTop: '1px solid var(--border-dim)' }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6">

          <div className="text-center mb-14">
            <div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full mb-4 text-[10px] font-bold tracking-[0.15em] uppercase"
              style={{
                border: '1px solid var(--border-mid)',
                color: 'var(--text-muted)',
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              <span className="w-1 h-1 rounded-full" style={{ background: 'var(--accent)' }} />
              Technical Architecture
            </div>
            <h2
              className="text-[38px] sm:text-[48px] font-bold mb-3"
              style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)', letterSpacing: '-0.03em' }}
            >
              Built for the Pit Wall.
            </h2>
            <p className="text-[15px] max-w-lg mx-auto" style={{ color: 'var(--text-secondary)' }}>
              Every component is engineered for the precision and speed that race engineering demands.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map(f => (
              <BentoCard key={f.title} {...f} />
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────── */}
      <section
        id="cta"
        className="py-24 relative overflow-hidden"
        style={{ background: 'var(--bg-surface-1)', borderTop: '1px solid var(--border-dim)' }}
      >
        {/* Background grid */}
        <div className="absolute inset-0 telemetry-grid-bg opacity-30" />
        {/* Radial glow */}
        <div
          className="absolute inset-0"
          style={{ background: 'radial-gradient(ellipse 60% 60% at 50% 50%, rgba(0,212,255,0.06) 0%, transparent 70%)' }}
        />

        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 text-center flex flex-col items-center gap-6">
          <div
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-bold tracking-[0.15em] uppercase"
            style={{
              border: '1px solid rgba(0,212,255,0.3)',
              background: 'rgba(0,212,255,0.06)',
              color: 'var(--accent)',
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            <span className="live-beacon beacon-accent" />
            System Ready
          </div>

          <h2
            className="text-[42px] sm:text-[56px] font-bold leading-none"
            style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)', letterSpacing: '-0.03em' }}
          >
            Ready to Analyze?
          </h2>
          <p className="text-[15px] max-w-md" style={{ color: 'var(--text-secondary)' }}>
            Launch the workspace and start dragging anomaly windows on live telemetry.
          </p>

          <div className="flex flex-wrap justify-center gap-4">
            <button
              type="button"
              onClick={() => onNavigate('f1-landing')}
              className="flex items-center gap-2 px-7 py-3.5 rounded-lg font-bold text-[14px] cursor-pointer transition-all"
              style={{
                fontFamily: "'Space Grotesk', sans-serif",
                background: '#E8FF00',
                color: '#000',
                border: 'none',
                letterSpacing: '0.02em',
              }}
              onMouseEnter={e => gsap.to(e.currentTarget, { scale: 1.03, boxShadow: '0 0 32px rgba(232,255,0,0.4)', duration: 0.2 })}
              onMouseLeave={e => gsap.to(e.currentTarget, { scale: 1, boxShadow: 'none', duration: 0.2 })}
            >
              <Flag size={15} />
              <span>F1 Intelligence</span>
            </button>
            <button
              type="button"
              onClick={() => onNavigate('ev-landing')}
              className="flex items-center gap-2 px-7 py-3.5 rounded-lg font-bold text-[14px] cursor-pointer transition-all"
              style={{
                fontFamily: "'Space Grotesk', sans-serif",
                background: '#00FF88',
                color: '#000',
                border: 'none',
                letterSpacing: '0.02em',
              }}
              onMouseEnter={e => gsap.to(e.currentTarget, { scale: 1.03, boxShadow: '0 0 32px rgba(0,255,136,0.4)', duration: 0.2 })}
              onMouseLeave={e => gsap.to(e.currentTarget, { scale: 1, boxShadow: 'none', duration: 0.2 })}
            >
              <Zap size={15} />
              <span>EV Analytics</span>
            </button>
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────── */}
      <footer
        className="py-5"
        style={{ borderTop: '1px solid var(--border-dim)' }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span
              className="text-[13px] font-bold tracking-[0.06em]"
              style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-secondary)' }}
            >
              OVERCUT
            </span>
            <span style={{ color: 'var(--accent)', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '13px' }}>.AI</span>
            <span
              className="text-[11px]"
              style={{ color: 'var(--text-disabled)', fontFamily: "'Inter', sans-serif" }}
            >
              Multimodal Telemetry Diagnostics
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span
              className="text-[10px]"
              style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
            >
              FastF1 3.4 · OpenCLIP ViT-B/32 · Qwen2.5-7B QLoRA
            </span>
          </div>
        </div>
      </footer>
    </div>
  )
}
