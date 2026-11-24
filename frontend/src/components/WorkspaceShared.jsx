import React, { useRef, useEffect, useState } from 'react'
import gsap from 'gsap'
import {
  ChevronDown, Cpu, ShieldCheck, Clock, Eye, FileText,
  CheckCircle, Sparkles, ArrowUpRight, Activity, Settings, Scissors,
} from 'lucide-react'
import { resolveImageUrl } from '../lib/api'

// ── Styled Select ─────────────────────────────────────────────────
export function StyledSelect({ value, onChange, children, style = {} }) {
  return (
    <div className="relative inline-flex items-center">
      <select
        value={value}
        onChange={onChange}
        className="appearance-none cursor-pointer text-[12px] font-medium pr-7 pl-3 py-1.5 rounded-md focus:outline-none transition-all"
        style={{
          fontFamily: "'Inter', sans-serif",
          background: 'var(--bg-surface-2)',
          color: 'var(--text-primary)',
          border: '1px solid var(--border-mid)',
          ...style,
        }}
        onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)' }}
        onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-mid)' }}
      >
        {children}
      </select>
      <ChevronDown
        size={11}
        className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2"
        style={{ color: 'var(--text-muted)' }}
      />
    </div>
  )
}

// ── Model Pill ────────────────────────────────────────────────────
export function ModelPill({ id, label, active, onClick, disabled = false, hint }) {
  const ref = useRef(null)
  return (
    <button
      ref={ref}
      type="button"
      onClick={() => onClick(id)}
      disabled={disabled}
      title={hint}
      className="flex flex-col px-3 py-2 rounded-md text-[11px] font-semibold transition-all"
      style={{
        fontFamily: "'Space Grotesk', sans-serif",
        background: active ? 'rgba(0,212,255,0.1)' : 'transparent',
        color: active ? 'var(--accent)' : 'var(--text-muted)',
        border: active ? '1px solid rgba(0,212,255,0.28)' : '1px solid transparent',
        gap: '2px',
        opacity: disabled ? 0.45 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
      onMouseEnter={() => {
        if (!active && !disabled) gsap.to(ref.current, { backgroundColor: 'rgba(255,255,255,0.03)', duration: 0.15 })
      }}
      onMouseLeave={() => {
        if (!active && !disabled) gsap.to(ref.current, { backgroundColor: 'transparent', duration: 0.15 })
      }}
    >
      {label}
    </button>
  )
}

// ── Settings Popover (model selector + provider availability) ────
export function SettingsPopover({
  reasoningMode, setReasoningMode,
  vlmStatus,
  accentColor = 'var(--accent)',
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const localAvailable = !!vlmStatus?.providers_available?.local_vlm
  const cloudAvailable = !!vlmStatus?.providers_available?.google_gemini

  useEffect(() => {
    const handleClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    const handleEscape = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [])

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md cursor-pointer transition-all"
        style={{
          background: open ? 'rgba(255,255,255,0.06)' : 'var(--bg-surface-2)',
          border: `1px solid ${open ? 'var(--border-bright)' : 'var(--border-mid)'}`,
        }}
      >
        <Settings size={13} style={{ color: accentColor }} />
        <span
          className="text-[10px] font-semibold tracking-[0.08em] uppercase"
          style={{ color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}
        >
          {reasoningMode === 'local_vlm' ? '7B' : reasoningMode === 'cloud_gemini' ? 'Gemini' : 'Heur'}
        </span>
        <ChevronDown size={10} style={{ color: 'var(--text-disabled)' }} />
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-2 z-50 w-64 p-4 rounded-xl"
          style={{
            background: 'var(--bg-surface-2)',
            border: '1px solid var(--border-mid)',
            boxShadow: '0 16px 48px rgba(0,0,0,0.6)',
          }}
        >
          <div
            className="text-[10px] font-bold uppercase tracking-[0.1em] mb-3"
            style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
          >
            Inference Engine
          </div>
          <div className="flex flex-col gap-1.5 mb-3">
            <ModelPill
              id="local_vlm"
              label="Overcut 7B QLoRA (Local)"
              active={reasoningMode === 'local_vlm'}
              onClick={setReasoningMode}
              disabled={!localAvailable}
              hint={localAvailable ? undefined : 'No CUDA device or LoRA adapter available; requests fall back to the heuristic engine.'}
            />
            <ModelPill id="deterministic" label="Heuristic Engine" active={reasoningMode === 'deterministic'} onClick={setReasoningMode} />
            <ModelPill
              id="cloud_gemini"
              label="Gemini (Cloud)"
              active={reasoningMode === 'cloud_gemini'}
              onClick={setReasoningMode}
              disabled={!cloudAvailable}
              hint={cloudAvailable ? undefined : 'GEMINI_API_KEY is not configured on the server.'}
            />
          </div>

          <div
            className="text-[10px] pt-3 space-y-1"
            style={{ borderTop: '1px solid var(--border-dim)', color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
          >
            <div className="flex items-center gap-2">
              <span className={`live-beacon ${vlmStatus?.loaded ? 'beacon-accent' : 'beacon-f1'}`} />
              <span style={{ color: vlmStatus?.loaded ? 'var(--accent)' : 'var(--f1-signal)' }}>
                {vlmStatus
                  ? (vlmStatus.loaded
                      ? 'LOCAL VLM LOADED'
                      : vlmStatus.providers_available?.local_vlm
                        ? 'LOCAL VLM READY (LOADS ON DEMAND)'
                        : 'LOCAL VLM UNAVAILABLE')
                  : 'BACKEND UNKNOWN'}
              </span>
            </div>
            <div style={{ color: cloudAvailable ? 'var(--accent)' : 'var(--text-disabled)' }}>
              CLOUD GEMINI {cloudAvailable ? 'CONFIGURED' : 'NOT CONFIGURED'}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Severity Badge ────────────────────────────────────────────────
export function SeverityBadge({ severity }) {
  const colorMap = {
    CRITICAL: { bg: 'rgba(255,51,102,0.12)',  text: '#FF3366', border: 'rgba(255,51,102,0.3)',  glow: '#FF3366' },
    HIGH:     { bg: 'rgba(255,107,53,0.12)',  text: '#FF6B35', border: 'rgba(255,107,53,0.3)',  glow: '#FF6B35' },
    MEDIUM:   { bg: 'rgba(255,184,0,0.12)',   text: '#FFB800', border: 'rgba(255,184,0,0.3)',   glow: '#FFB800' },
    LOW:      { bg: 'rgba(0,212,255,0.12)',   text: '#00D4FF', border: 'rgba(0,212,255,0.3)',   glow: '#00D4FF' },
  }
  const c = colorMap[severity] || colorMap.HIGH
  return (
    <span
      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black tracking-[0.08em] uppercase"
      style={{
        background: c.bg,
        color: c.text,
        border: `1px solid ${c.border}`,
        fontFamily: "'JetBrains Mono', monospace",
        boxShadow: `0 0 12px ${c.glow}20`,
      }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ background: c.text, boxShadow: `0 0 6px ${c.glow}` }}
      />
      {severity}
    </span>
  )
}

// ── Metric Counter Card ────────────────────────────────────────────
export function MetricCard({ label, value, sub, accentColor = 'var(--accent)', icon: Icon }) {
  return (
    <div
      className="relative flex flex-col p-4 rounded-xl overflow-hidden"
      style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-mid)' }}
    >
      <div
        className="absolute top-0 left-0 right-0 h-[1px]"
        style={{ background: `linear-gradient(to right, transparent, ${accentColor}50, transparent)` }}
      />
      <div
        className="text-[9px] font-bold uppercase tracking-[0.1em] mb-2 flex items-center gap-1.5"
        style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
      >
        {Icon && <Icon size={10} style={{ color: accentColor }} />}
        {label}
      </div>
      <div
        className="text-[20px] font-bold flex items-center gap-1.5 mb-1"
        style={{ fontFamily: "'Space Grotesk', sans-serif", color: accentColor }}
      >
        {value}
      </div>
      <div
        className="text-[11px]"
        style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif" }}
      >
        {sub}
      </div>
    </div>
  )
}

// ── Results Panel (shared between F1 and EV) ──────────────────────
export function ResultsPanel({
  data, loading, elapsedMs, isEV, onOpenDossier, error,
}) {
  const resultsRef   = useRef(null)
  const prevDataRef  = useRef(null)
  const confRef      = useRef(null)
  const confTweenRef = useRef(null)

  useEffect(() => {
    if (data && !loading && resultsRef.current && data !== prevDataRef.current) {
      prevDataRef.current = data
      const ctx = gsap.context(() => {
        gsap.fromTo(
          resultsRef.current,
          { y: 40, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.65, ease: 'power3.out' }
        )
      })
      return () => ctx.revert()
    }
  }, [data, loading])

  useEffect(() => {
    if (data?.diagnostic?.confidence && confRef.current) {
      if (confTweenRef.current) confTweenRef.current.kill()
      const target = Math.round(data.diagnostic.confidence * 100)
      const obj = { val: 0 }
      confTweenRef.current = gsap.to(obj, {
        val: target,
        duration: 1.2,
        ease: 'power2.out',
        snap: { val: 1 },
        onUpdate: () => {
          if (confRef.current) confRef.current.textContent = Math.round(obj.val) + '%'
        },
      })
    }
    return () => {
      if (confTweenRef.current) confTweenRef.current.kill()
    }
  }, [data])

  // Loading state
  if (loading) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-4 p-10 rounded-xl"
        style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-mid)', minHeight: '200px' }}
      >
        <span
          className="inline-block w-8 h-8 rounded-full animate-spin"
          style={{ border: '2px solid var(--border-mid)', borderTopColor: isEV ? 'var(--ev-signal)' : 'var(--f1-signal)' }}
        />
        <span
          className="text-[12px]"
          style={{ color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}
        >
          {isEV ? 'Running EV multimodal diagnosis…' : 'Running F1 telemetry diagnosis…'}
        </span>
      </div>
    )
  }

  // Empty state — no data yet
  if (!data) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-5 p-10 rounded-xl"
        style={{
          background: 'var(--bg-surface-1)',
          border: '1px dashed var(--border-mid)',
          minHeight: '220px',
        }}
      >
        {/* Icon */}
        <div
          className="w-14 h-14 rounded-2xl flex items-center justify-center"
          style={{
            background: isEV ? 'rgba(0,255,136,0.06)' : 'rgba(232,255,0,0.06)',
            border: `1px solid ${isEV ? 'rgba(0,255,136,0.2)' : 'rgba(232,255,0,0.2)'}`,
          }}
        >
          <Scissors size={22} style={{ color: isEV ? 'var(--ev-signal)' : 'var(--f1-signal)' }} />
        </div>

        {/* Text */}
        <div className="text-center">
          <p
            className="text-[15px] font-semibold mb-2"
            style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-primary)', letterSpacing: '-0.01em' }}
          >
            {isEV ? 'Select a voltage anomaly window to diagnose' : 'Select a telemetry window to diagnose'}
          </p>
          <p
            className="text-[13px] max-w-sm"
            style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif", lineHeight: 1.6 }}
          >
            {isEV
              ? 'Drag on the 50Hz chart above to highlight any voltage sag, thermal spike, or current anomaly, then click Execute EV Diagnosis.'
              : 'Drag on the 100Hz chart above to highlight any braking event, corner, or speed anomaly, then click Execute AI Diagnosis.'}
          </p>
        </div>

        {/* Step pills */}
        <div className="flex flex-wrap justify-center gap-2">
          {['1 · Drag to select', '2 · Click Execute', '3 · Read diagnosis'].map((step, i) => (
            <span
              key={i}
              className="px-3 py-1.5 rounded-full text-[11px] font-semibold"
              style={{
                background: 'var(--bg-surface-2)',
                border: '1px solid var(--border-dim)',
                color: 'var(--text-disabled)',
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              {step}
            </span>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div ref={resultsRef} className="space-y-5" style={{ willChange: 'transform, opacity' }}>
      {error && (
        <div
          className="flex items-start gap-2 px-4 py-3 rounded-lg text-[12px]"
          style={{ background: 'rgba(255,184,0,0.08)', border: '1px solid rgba(255,184,0,0.3)', color: 'var(--text-secondary)', fontFamily: "'Inter', sans-serif" }}
        >
          <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5" style={{ background: '#FFB800' }} />
          <span>{error}</span>
        </div>
      )}
      {/* Metric counters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MetricCard
          label="Pipeline Status"
          value={
            <span className="flex items-center gap-1.5">
              <CheckCircle size={16} style={{ color: data.simulated ? '#FFB800' : '#00FF88' }} />
              <span>{data.simulated ? 'SIMULATED' : (data.status || 'OK').toUpperCase()}</span>
            </span>
          }
          sub={data.simulated ? 'API unreachable — synthetic payload' : 'Slicing & vector retrieval'}
          accentColor={data.simulated ? '#FFB800' : '#00FF88'}
          icon={Activity}
        />
        <MetricCard
          label="Inference Engine"
          value={
            <span className="flex items-center gap-1.5">
              <Cpu size={16} style={{ color: 'var(--accent)' }} />
              <span>
                {data.diagnostic.provider === 'LOCAL_VLM' ? 'Overcut 7B'
                  : data.diagnostic.provider?.startsWith('CLOUD') ? 'Gemini'
                    : data.diagnostic.provider === 'SIMULATED' ? 'Simulation'
                      : data.diagnostic.provider === 'HALLUCINATION_FAILSAFE' ? 'Failsafe'
                        : 'Heuristic'}
              </span>
            </span>
          }
          sub={data.diagnostic.model_name}
          accentColor="var(--accent)"
          icon={Cpu}
        />
        <MetricCard
          label="Confidence"
          value={
            <span className="flex items-center gap-1.5">
              <ShieldCheck size={16} style={{ color: 'var(--accent)' }} />
              <span ref={confRef}>{Math.round((data.diagnostic.confidence || 0) * 100)}%</span>
            </span>
          }
          sub={data.diagnostic.is_insufficient_data ? 'FAILSAFE: below 0.65 gate' : '> 0.65 guardrail passed'}
          accentColor="var(--accent)"
          icon={ShieldCheck}
        />
        <MetricCard
          label="Latency"
          value={
            <span className="flex items-center gap-1.5">
              <Clock size={16} style={{ color: 'var(--accent-dim)' }} />
              <span>{elapsedMs ? `${(elapsedMs / 1000).toFixed(2)}s` : '—'}</span>
            </span>
          }
          sub="End-to-end execution"
          accentColor="var(--accent-dim)"
          icon={Clock}
        />
      </div>

      {/* Waveform artifact + Diagnostic dossier */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">

        {/* Waveform Artifact */}
        <div className="lg:col-span-5 flex flex-col p-5 rounded-xl"
          style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-mid)' }}
        >
          <div className="flex items-center justify-between pb-3 mb-3"
            style={{ borderBottom: '1px solid var(--border-dim)' }}
          >
            <div className="flex items-center gap-2">
              <Eye size={13} style={{ color: 'var(--accent)' }} />
              <span className="text-[12px] font-semibold"
                style={{ color: 'var(--text-primary)', fontFamily: "'Space Grotesk', sans-serif" }}
              >
                Micro-Cropped ROI Artifact
              </span>
            </div>
            <span className="text-[10px] truncate max-w-[140px]"
              style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
            >
              {data.crop_filename}
            </span>
          </div>

          <div className="flex-1 flex items-center justify-center rounded-lg overflow-hidden min-h-[160px]"
            style={{ background: 'rgba(0,0,0,0.5)', border: '1px solid var(--border-dim)' }}
          >
            {data.image_url ? (
              <img src={resolveImageUrl(data.image_url)} alt="Telemetry anomaly waveform crop"
                className="w-full h-auto max-h-52 object-contain" />
            ) : (
              <div className="text-center px-6 py-8">
                <Activity size={24} style={{ color: 'var(--border-bright)', margin: '0 auto 8px' }} />
                <span className="text-[11px]"
                  style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
                >
                  Waveform processed in memory
                </span>
              </div>
            )}
          </div>

          <div className="grid grid-cols-3 gap-2 mt-4">
            {[
              {
                label: 'Window',
                value: `${parseFloat((data.telemetry_metrics.duration_seconds || 15).toFixed(1))}s`,
              },
              {
                label: isEV ? 'Peak A' : 'Top Speed',
                value: isEV
                  ? `${Math.round(data.telemetry_metrics.peak_current || 140)}A`
                  : `${Math.round(data.telemetry_metrics.max_speed || 294)} km/h`,
              },
              {
                label: isEV ? 'Max °C' : 'Min Speed',
                value: isEV
                  ? `${parseFloat((data.telemetry_metrics.max_temperature || 42).toFixed(1))}°C`
                  : `${Math.round(data.telemetry_metrics.min_speed || 68)} km/h`,
              },
            ].map(({ label, value }) => (
              <div key={label} className="p-3 rounded-lg text-center"
                style={{ background: 'var(--bg-surface-3)', border: '1px solid var(--border-dim)' }}
              >
                <div className="text-[9px] uppercase font-bold mb-1"
                  style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
                >
                  {label}
                </div>
                <div className="text-[14px] font-bold"
                  style={{ color: 'var(--accent)', fontFamily: "'JetBrains Mono', monospace" }}
                >
                  {value}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Diagnostic Dossier Card */}
        <div className="lg:col-span-7 flex flex-col p-6 rounded-xl gap-4 relative overflow-hidden"
          style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-mid)' }}
        >
          <div className="absolute top-0 left-0 right-0 h-[1px]"
            style={{ background: `linear-gradient(to right, transparent, var(--accent)60, transparent)` }}
          />

          <div className="flex items-center justify-between pb-3"
            style={{ borderBottom: '1px solid var(--border-dim)' }}
          >
            <div className="flex items-center gap-2">
              <Sparkles size={14} style={{ color: 'var(--accent)' }} />
              <span className="text-[11px] font-bold uppercase tracking-[0.1em]"
                style={{ color: 'var(--text-secondary)', fontFamily: "'JetBrains Mono', monospace" }}
              >
                Autonomous Diagnostic Dossier
              </span>
            </div>
            <SeverityBadge severity={data.diagnostic.severity} />
          </div>

          <div>
            <h3 className="text-[20px] font-bold leading-snug mb-2"
              style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)', letterSpacing: '-0.02em' }}
            >
              {data.diagnostic.title}
            </h3>
            <p className="text-[13px] leading-relaxed"
              style={{ color: 'var(--text-secondary)', fontFamily: "'Inter', sans-serif" }}
            >
              {data.diagnostic.root_cause}
            </p>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[9px] font-bold uppercase tracking-[0.1em]"
                style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
              >
                Model Confidence
              </span>
              <span className="text-[12px] font-bold"
                style={{ color: 'var(--accent)', fontFamily: "'JetBrains Mono', monospace" }}
              >
                {Math.round(data.diagnostic.confidence * 100)}%
              </span>
            </div>
            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border-dim)' }}>
              <div className="h-full rounded-full transition-all duration-1000"
                style={{
                  width: `${Math.round(data.diagnostic.confidence * 100)}%`,
                  background: 'linear-gradient(to right, var(--accent), rgba(0,212,255,0.6))',
                  boxShadow: '0 0 8px rgba(0,212,255,0.5)',
                }}
              />
            </div>
          </div>

          <div>
            <span className="text-[9px] font-bold uppercase tracking-[0.1em] block mb-2"
              style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
            >
              Physical Evidence
            </span>
            <div className="space-y-1.5">
              {data.diagnostic.physical_evidence.slice(0, 3).map((ev, i) => (
                <div key={i} className="flex items-start gap-2.5 p-2.5 rounded-lg text-[12px]"
                  style={{ background: 'var(--bg-surface-3)', border: '1px solid var(--border-dim)' }}
                >
                  <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5" style={{ background: 'var(--accent)' }} />
                  <span style={{ color: 'var(--text-secondary)', fontFamily: "'Inter', sans-serif", lineHeight: '1.5' }}>
                    {ev}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="p-4 rounded-lg relative overflow-hidden"
            style={{ background: 'rgba(0,212,255,0.04)', border: '1px solid rgba(0,212,255,0.14)' }}
          >
            <div className="absolute top-0 left-0 right-0 h-[1px]"
              style={{ background: 'linear-gradient(to right, transparent, rgba(0,212,255,0.4), transparent)' }}
            />
            <span className="text-[9px] font-black uppercase tracking-[0.12em] block mb-1.5"
              style={{ color: 'var(--accent)', fontFamily: "'JetBrains Mono', monospace" }}
            >
              ◆ Tactical Recommendation
            </span>
            <p className="text-[12px] leading-relaxed"
              style={{ color: 'var(--text-primary)', fontFamily: "'Inter', sans-serif" }}
            >
              {data.diagnostic.strategic_recommendation}
            </p>
          </div>

          <div className="pt-3 flex flex-wrap items-center justify-between gap-3"
            style={{ borderTop: '1px solid var(--border-dim)' }}
          >
            <span className="text-[10px]"
              style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
            >
              {data.diagnostic.model_name}
            </span>
            <button type="button" onClick={onOpenDossier}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-[12px] font-bold cursor-pointer transition-all"
              style={{
                fontFamily: "'Space Grotesk', sans-serif",
                background: 'var(--accent)',
                color: '#000',
                border: 'none',
                letterSpacing: '0.02em',
              }}
              onMouseEnter={e => gsap.to(e.currentTarget, { scale: 1.03, boxShadow: '0 0 20px rgba(0,212,255,0.4)', duration: 0.15 })}
              onMouseLeave={e => gsap.to(e.currentTarget, { scale: 1, boxShadow: 'none', duration: 0.15 })}
            >
              <FileText size={13} />
              <span>Full Dossier</span>
              <ArrowUpRight size={12} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
