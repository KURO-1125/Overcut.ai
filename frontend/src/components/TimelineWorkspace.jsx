import React, { useEffect, useRef, useState, useMemo } from 'react'
import uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'
import {
  Activity, Scissors, Zap, RefreshCw,
  ChevronRight, Eye,
  Play, Pause, RotateCcw,
} from 'lucide-react'
import TrackMap from './TrackMap'
import BatteryPackMap from './BatteryPackMap'
import RaceStintMacroBar from './RaceStintMacroBar'
import { generateF1TelemetrySeries, generateEVTelemetrySeries } from '../data/telemetryData'
import { apiFetch } from '../lib/api'

// ── Telemetry overlay computation ───────────────────────────────
function computeTelemetryOverlay(primaryData, refData) {
  if (!primaryData?.series || !refData?.series) return null
  const priTimes = primaryData.series[0]
  const priSpeeds = primaryData.series[1]
  const refTimes = refData.series[0]
  const refSpeeds = refData.series[1]
  const refThrottles = refData.series[2]
  const refBrakes = refData.series[3]
  if (!priTimes?.length || !refTimes?.length) return null
  const nPri = priTimes.length
  const nRef = refTimes.length
  const priDist = new Float64Array(nPri)
  for (let i = 1; i < nPri; i++) {
    const vAvg = ((priSpeeds[i - 1] || 0) + (priSpeeds[i] || 0)) / 7.2
    priDist[i] = priDist[i - 1] + vAvg * Math.max(priTimes[i] - priTimes[i - 1], 0)
  }
  const refDist = new Float64Array(nRef)
  for (let j = 1; j < nRef; j++) {
    const vAvg = ((refSpeeds[j - 1] || 0) + (refSpeeds[j] || 0)) / 7.2
    refDist[j] = refDist[j - 1] + vAvg * Math.max(refTimes[j] - refTimes[j - 1], 0)
  }
  const maxRefDist = refDist[nRef - 1]
  const maxPriDist = priDist[nPri - 1]
  const resampledRefSpeeds = new Float64Array(nPri)
  const resampledRefThrottles = new Float64Array(nPri)
  const resampledRefBrakes = new Float64Array(nPri)
  const deltaT = new Float64Array(nPri)
  let refIdx = 0
  for (let i = 0; i < nPri; i++) {
    const normDist = maxPriDist > 0 ? priDist[i] / maxPriDist : i / Math.max(nPri - 1, 1)
    const mappedRefDist = normDist * maxRefDist
    while (refIdx < nRef - 2 && refDist[refIdx + 1] < mappedRefDist) refIdx++
    const d0 = refDist[refIdx], d1 = refDist[refIdx + 1]
    const alpha = d1 - d0 > 1e-6 ? Math.min(Math.max((mappedRefDist - d0) / (d1 - d0), 0), 1) : 0
    resampledRefSpeeds[i] = Math.round(((refSpeeds[refIdx] || 0) + alpha * ((refSpeeds[refIdx + 1] || 0) - (refSpeeds[refIdx] || 0))) * 10) / 10
    resampledRefThrottles[i] = Math.round((refThrottles[refIdx] || 0) + alpha * ((refThrottles[refIdx + 1] || 0) - (refThrottles[refIdx] || 0)))
    resampledRefBrakes[i] = Math.round((refBrakes[refIdx] || 0) + alpha * ((refBrakes[refIdx + 1] || 0) - (refBrakes[refIdx] || 0)))
    deltaT[i] = Math.round((refTimes[refIdx] + alpha * (refTimes[refIdx + 1] - refTimes[refIdx]) - priTimes[i]) * 1000) / 1000
  }
  return {
    resampledRefSpeeds: Array.from(resampledRefSpeeds),
    resampledRefThrottles: Array.from(resampledRefThrottles),
    resampledRefBrakes: Array.from(resampledRefBrakes),
    deltaT: Array.from(deltaT),
  }
}

function synthesizeComparisonFallback(baseTelemetry, compNum, compInfo) {
  if (!baseTelemetry?.series) return null
  const [baseTimes, baseSpeeds, baseThrottles, baseBrakes, baseGears, baseRpms] = baseTelemetry.series
  const numVal = parseInt(compNum || '4', 10)
  const sessionSeed = (numVal * 31 + (baseTelemetry.lap_number || 1) * 17) % 1000
  const speedScale = 0.975 + Math.sin(sessionSeed) * 0.035
  const syntheticSpeeds = baseSpeeds.map((s, idx) =>
    Math.max(50, Math.round((s * speedScale + Math.sin(idx * 0.15 + sessionSeed) * 3.5) * 10) / 10)
  )
  const syntheticLapTime = Math.round((baseTelemetry.lap_time_seconds + 0.28 * (speedScale > 1 ? -1 : 1)) * 1000) / 1000
  return {
    status: 'success',
    driver: String(compNum),
    driver_name: compInfo?.name || `Driver #${compNum}`,
    driver_code: compInfo?.code || `D${compNum}`,
    team_name: compInfo?.team || 'Formula 1',
    team_color: compInfo?.color || '#FF8000',
    lap_number: baseTelemetry.lap_number || 1,
    lap_time_seconds: syntheticLapTime,
    track_map: baseTelemetry.track_map,
    series: [baseTimes, syntheticSpeeds, baseThrottles.map(t => Math.min(100, Math.max(0, t))), baseBrakes.map(b => Math.min(100, Math.max(0, b))), baseGears || [], baseRpms || []],
  }
}

// ── Collapsible: Lap Stint Bar ───────────────────────────────────
function LapStintCollapsible({ lapsSummary, activeLapNumber, onSelectLap, totalLaps, sessionType, circuitName }) {
  const [open, setOpen] = useState(false)
  const activeLap = lapsSummary.find(l => l.lap_number === activeLapNumber) || lapsSummary[0]
  const fastestLap = lapsSummary.reduce((best, cur) => {
    if (!cur.lap_time) return best
    if (!best || !best.lap_time) return cur
    return cur.lap_time < best.lap_time ? cur : best
  }, null)
  return (
    <div style={{ borderBottom: '1px solid var(--border-dim)' }}>
      <button type="button" onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-2 cursor-pointer"
        style={{ background: 'transparent', border: 'none', textAlign: 'left' }}
        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.02)' }}
        onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
      >
        <div className="flex items-center gap-3 font-mono text-[10px]">
          <span style={{ color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            {sessionType === 'R' ? 'Race Stints' : 'Qualifying Sessions'}
          </span>
          <span style={{ color: 'var(--text-muted)' }}>{circuitName} · {lapsSummary.length} Laps</span>
          <span className="px-2 py-0.5 rounded"
            style={{ background: 'rgba(232,255,0,0.08)', color: 'var(--f1-signal)', border: '1px solid rgba(232,255,0,0.2)' }}
          >
            Lap #{activeLapNumber}{activeLap?.lap_time && ` · ${activeLap.lap_time.toFixed(3)}s`}
            {activeLap?.compound && ` · ${activeLap.compound}`}
          </span>
          {fastestLap && (
            <span style={{ color: '#c084fc', fontSize: '10px' }}>
              P1 #{fastestLap.lap_number} ({fastestLap.lap_time?.toFixed(3)}s)
            </span>
          )}
        </div>
        <ChevronRight size={13} style={{ color: 'var(--text-disabled)', transform: open ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s ease' }} />
      </button>
      {open && (
        <div style={{ padding: '12px 16px', background: 'var(--bg-surface-1)' }}>
          <RaceStintMacroBar
            lapsSummary={lapsSummary}
            activeLapNumber={activeLapNumber}
            onSelectLap={onSelectLap}
            totalLaps={totalLaps}
            sessionType={sessionType}
            circuitName={circuitName}
          />
        </div>
      )}
    </div>
  )
}

// ── Collapsible: Ghost Comparison ────────────────────────────────
function GhostComparisonCollapsible({
  compareDriver, setCompareDriver,
  compareTelemetry, setCompareTelemetry,
  loadCompareTelemetry,
  loadingCompare,
  availableDrivers, driver, compareDriverInfo,
  visibleChannels, toggleChannel, telemetry,
}) {
  const [open, setOpen] = useState(false)
  const hasGhost = !!compareTelemetry
  return (
    <div style={{ borderBottom: '1px solid var(--border-dim)' }}>
      <button type="button" onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-2 cursor-pointer"
        style={{ background: 'transparent', border: 'none', textAlign: 'left' }}
        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.02)' }}
        onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
      >
        <div className="flex items-center gap-3 font-mono text-[10px]">
          <span style={{ color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Ghost Comparison</span>
          {hasGhost ? (
            <span className="flex items-center gap-1.5 px-2 py-0.5 rounded"
              style={{ background: 'rgba(192,132,252,0.1)', color: '#c084fc', border: '1px solid rgba(192,132,252,0.25)' }}
            >
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: compareDriverInfo?.color || '#FF8000' }} />
              #{compareDriverInfo?.number || compareDriver} {compareDriverInfo?.code || compareTelemetry?.driver_code}
              {telemetry?.lap_time_seconds && compareTelemetry?.lap_time_seconds && (() => {
                const delta = compareTelemetry.lap_time_seconds - telemetry.lap_time_seconds
                return <span style={{ color: delta >= 0 ? '#05df72' : '#ff2a4b', marginLeft: '4px', fontWeight: 700 }}>{delta >= 0 ? '+' : ''}{delta.toFixed(3)}s</span>
              })()}
            </span>
          ) : (
            <span style={{ color: 'var(--text-disabled)' }}>No ghost active</span>
          )}
        </div>
        <ChevronRight size={13} style={{ color: 'var(--text-disabled)', transform: open ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s ease' }} />
      </button>
      {open && (
        <div className="flex flex-wrap items-center gap-3 px-4 py-3" style={{ background: 'var(--bg-surface-1)' }}>
          <select
            value={compareDriver || ''}
            onChange={e => {
              const val = e.target.value || null
              setCompareDriver(val)
              if (val) loadCompareTelemetry(val, null)
              else setCompareTelemetry(null)
            }}
            className="appearance-none cursor-pointer text-[11px] font-medium px-3 py-1.5 rounded-md focus:outline-none"
            style={{ background: 'var(--bg-surface-2)', color: 'var(--text-primary)', border: '1px solid var(--border-mid)', fontFamily: "'Inter', sans-serif" }}
          >
            <option value="">— Select Ghost Driver —</option>
            {availableDrivers.filter(d => String(d.number || d.id) !== String(driver)).map(d => (
              <option key={d.number || d.id} value={d.number || d.id}>#{d.number || d.id} {d.name} ({d.team})</option>
            ))}
          </select>
          {loadingCompare && (
            <span className="text-[10px] animate-pulse" style={{ color: 'var(--f1-signal)', fontFamily: "'JetBrains Mono', monospace" }}>Syncing ghost…</span>
          )}
          {hasGhost && (
            <>
              <div className="flex items-center gap-0.5 p-0.5 rounded" style={{ background: 'var(--bg-surface-3)', border: '1px solid var(--border-dim)' }}>
                {[
                  { key: 'refSpeed', label: 'Spd', color: compareDriverInfo?.color || '#FF8000' },
                  { key: 'delta', label: 'Δt', color: '#c084fc' },
                  { key: 'refThrottle', label: 'Thr', color: '#22d3ee' },
                  { key: 'refBrake', label: 'Brk', color: '#fb7185' },
                ].map(({ key, label, color }) => (
                  <button key={key} type="button" onClick={() => toggleChannel(key)}
                    className="px-2 py-1 rounded text-[10px] font-bold cursor-pointer transition-all"
                    style={{ background: visibleChannels[key] ? `${color}18` : 'transparent', color: visibleChannels[key] ? color : 'var(--text-disabled)', border: 'none' }}
                  >{label}</button>
                ))}
              </div>
              <button type="button" onClick={() => { setCompareDriver(null); setCompareTelemetry(null) }}
                className="text-[10px] cursor-pointer transition-colors"
                style={{ background: 'none', border: 'none', color: 'var(--text-disabled)' }}
                onMouseEnter={e => { e.currentTarget.style.color = '#ff2a4b' }}
                onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-disabled)' }}
              >× Clear</button>
            </>
          )}
        </div>
      )}
    </div>
  )
}

// ── Collapsible: Corner / Phase Anchors ──────────────────────────
function AnchorsCollapsible({ isEV, activeAnchorList, activeCorner, handleAnchorSelect, resetView, circuitName }) {
  const [open, setOpen] = useState(false)
  if (!activeAnchorList?.length) return null
  return (
    <div style={{ borderTop: '1px solid var(--border-dim)' }}>
      <div
        className="w-full flex items-center justify-between px-4 py-2"
        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.02)' }}
        onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
      >
        <button type="button" onClick={() => setOpen(o => !o)} aria-expanded={open}
          className="flex-1 flex items-center gap-3 font-mono text-[10px] cursor-pointer"
          style={{ background: 'transparent', border: 'none', textAlign: 'left' }}
        >
          <span style={{ color: 'var(--text-disabled)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            {isEV ? 'Phase Anchors' : `${circuitName || 'Circuit'} Corners`}
          </span>
          {activeCorner && (
            <span className="px-2 py-0.5 rounded"
              style={{ background: 'rgba(232,255,0,0.08)', color: 'var(--f1-signal)', border: '1px solid rgba(232,255,0,0.2)' }}
            >{activeCorner}</span>
          )}
          <span style={{ color: 'var(--text-disabled)' }}>{activeAnchorList.length} {isEV ? 'phases' : 'turns'}</span>
        </button>
        <div className="flex items-center gap-2">
          <button type="button" onClick={resetView}
            className="text-[10px] px-2 py-0.5 rounded cursor-pointer"
            style={{ background: 'var(--bg-surface-3)', border: '1px solid var(--border-dim)', color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-muted)' }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-disabled)' }}
          >Reset</button>
          <ChevronRight size={13} style={{ color: 'var(--text-disabled)', transform: open ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s ease' }} />
        </div>
      </div>
      {open && (
        <div className="px-4 pb-3" style={{ background: 'var(--bg-surface-1)' }}>
          <div className="flex gap-1.5 overflow-x-auto scrollbar-none py-1.5">
            {activeAnchorList.map((anchor, idx) => {
              const parts = anchor.name.split(' ')
              const code = parts[0]
              const name = parts.slice(1).join(' ')
              const isSelected = activeCorner === anchor.name
              return (
                <button key={idx} type="button" onClick={() => handleAnchorSelect(anchor)}
                  className="flex-shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded cursor-pointer transition-all"
                  style={{
                    background: isSelected ? (isEV ? 'rgba(0,255,136,0.1)' : 'rgba(232,255,0,0.1)') : 'var(--bg-surface-2)',
                    border: `1px solid ${isSelected ? (isEV ? 'rgba(0,255,136,0.35)' : 'rgba(232,255,0,0.35)') : 'var(--border-dim)'}`,
                    fontFamily: "'JetBrains Mono', monospace",
                    whiteSpace: 'nowrap',
                  }}
                >
                  <span className="text-[10px] font-bold" style={{ color: isSelected ? (isEV ? 'var(--ev-signal)' : 'var(--f1-signal)') : 'var(--text-secondary)' }}>{code}</span>
                  {name && <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{name}</span>}
                  <span className="text-[9px]" style={{ color: 'var(--text-disabled)' }}>{anchor.start}s</span>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────
export default function TimelineWorkspace({
  onSelectAnomaly,
  isAnalyzing,
  presetRange,
  mode = 'motorsport',
  useVLM = false,
  driver = '1',
  cycleKey = 'nasa_b0005_sag',
  year = 2025,
  event = 'monaco',
  sessionType = 'Q',
  availableDrivers = [],
}) {
  const chartContainerRef = useRef(null)
  const uplotRef = useRef(null)

  const fitChart = () => {
    const el = chartContainerRef.current
    const u = uplotRef.current
    if (!el || !u || !el.clientWidth) return
    const wrapEl = u.root.querySelector('.u-wrap')
    const legendH = wrapEl ? Math.round(u.root.getBoundingClientRect().height - wrapEl.getBoundingClientRect().height) : 0
    const height = Math.max(160, Math.round(el.clientHeight) - legendH)
    if (u.height !== height || u.width !== el.clientWidth) u.setSize({ width: el.clientWidth, height })
  }

  // chartReady: false until the user clicks "Load Telemetry".
  const [chartReady, setChartReady] = useState(false)
  const [telemetry, setTelemetry] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const [showTrackMap, setShowTrackMap] = useState(true)
  const sidePanelRef = useRef(null)
  const chartColumnRef = useRef(null)
  const [chartHeight, setChartHeight] = useState(280)
  const [hoverMetrics, setHoverMetrics] = useState(null)
  const [selectedRange, setSelectedRange] = useState(null)

  const [visibleChannels, setVisibleChannels] = useState({
    speed: true, throttle: true, brake: true,
    voltage: true, current: true, temperature: true,
    refSpeed: true, refThrottle: false, refBrake: false, delta: true,
  })

  const [activeCorner, setActiveCorner] = useState(null)
  const [selectedLap, setSelectedLap] = useState(null)

  const [compareDriver, setCompareDriver] = useState(null)
  const [compareTelemetry, setCompareTelemetry] = useState(null)
  const [loadingCompare, setLoadingCompare] = useState(false)

  const [isPlaying, setIsPlaying] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0)
  const [playbackTime, setPlaybackTime] = useState(0.0)
  const animFrameRef = useRef(null)
  const lastTimeRef = useRef(null)

  const telemetryRequestRef = useRef(0)
  const compareRequestRef = useRef(0)
  const telemetryControllerRef = useRef(null)
  const compareControllerRef = useRef(null)

  useEffect(() => () => {
    telemetryControllerRef.current?.abort()
    compareControllerRef.current?.abort()
  }, [])

  const isEV = mode === 'ev' || telemetry?.domain === 'EV_BATTERY'

  // Real F1 feeds (OpenF1, FastF1) sample at ~4 Hz; the synthetic path is
  // generated at 100 Hz. Label whatever is actually in the payload.
  const sampleRateHz = useMemo(() => {
    const times = telemetry?.series?.[0]
    if (!times || times.length < 2) return null
    const span = times[times.length - 1] - times[0]
    if (!(span > 0)) return null
    return Math.round((times.length - 1) / span)
  }, [telemetry])

  // Size the chart slot so the chart column matches the side panel exactly
  useEffect(() => {
    const measure = () => {
      const wide = window.matchMedia('(min-width: 1024px)').matches
      const panel = sidePanelRef.current
      const column = chartColumnRef.current
      if (!chartReady || !wide || !showTrackMap || !panel || !column) { setChartHeight(280); return }
      const diff = Math.round(panel.getBoundingClientRect().height - column.getBoundingClientRect().height)
      if (Math.abs(diff) > 1) setChartHeight(prev => Math.max(280, prev + diff))
    }
    measure()
    const ro = new ResizeObserver(measure)
    if (sidePanelRef.current) ro.observe(sidePanelRef.current)
    window.addEventListener('resize', measure)
    return () => { ro.disconnect(); window.removeEventListener('resize', measure) }
  }, [chartReady, showTrackMap, telemetry, chartHeight])

  // Keep anchorFnRef current so uPlot setCursor hook always uses fresh telemetry corners
  const anchorFnRef = useRef(null)
  useEffect(() => {
    anchorFnRef.current = (time) => {
      const list = isEV ? telemetry?.phase_anchors : telemetry?.corners
      if (!list) return null
      return list.find(c => time >= c.start && time <= c.end) || null
    }
  }, [isEV, telemetry])

  // loadTelemetry — explicit lap-select calls and manual refresh
  const loadTelemetry = async (lapOverride) => {
    const requestId = ++telemetryRequestRef.current
    telemetryControllerRef.current?.abort()
    const controller = new AbortController()
    telemetryControllerRef.current = controller

    setError(null)
    setLoading(true)
    try {
      const activeLapTarget = lapOverride !== undefined ? lapOverride : selectedLap
      const lapQuery = (!isEV && activeLapTarget != null) ? `&lap=${encodeURIComponent(activeLapTarget)}` : ''
      const path = mode === 'ev'
        ? `/api/ev/telemetry/stream?cycle_key=${encodeURIComponent(cycleKey || 'nasa_b0005_sag')}`
        : `/api/telemetry/stream?year=${year}&event=${encodeURIComponent(event)}&session_type=${encodeURIComponent(sessionType)}&driver=${encodeURIComponent(driver || '1')}${lapQuery}`
      const res = await apiFetch(path, { signal: controller.signal, timeoutMs: 15000 })
      const json = await res.json()
      if (requestId !== telemetryRequestRef.current) return
      if (json.status === 'success' && json.series?.length > 0) {
        setTelemetry(json)
        if (json.lap_number != null) setSelectedLap(json.lap_number)
      } else {
        throw new Error('Malformed telemetry payload')
      }
    } catch (err) {
      if (err.name === 'AbortError' || requestId !== telemetryRequestRef.current) return
      console.warn('Backend telemetry offline, using labelled synthetic fallback:', err.message)
      setError(`Telemetry API unavailable (${err.message}). Displaying simulated waveform.`)
      setTelemetry({ ...(mode === 'ev' ? generateEVTelemetrySeries() : generateF1TelemetrySeries()), simulated: true })
    } finally {
      if (requestId === telemetryRequestRef.current) setLoading(false)
    }
  }

  const loadCompareTelemetry = async (compNum, lapOverride) => {
    if (!compNum || isEV) { setCompareTelemetry(null); return }
    const requestId = ++compareRequestRef.current
    compareControllerRef.current?.abort()
    const controller = new AbortController()
    compareControllerRef.current = controller

    setLoadingCompare(true)
    try {
      const lapQuery = (lapOverride ?? selectedLap) != null ? `&lap=${encodeURIComponent(lapOverride ?? selectedLap)}` : ''
      const path = `/api/telemetry/stream?year=${year}&event=${encodeURIComponent(event)}&session_type=${encodeURIComponent(sessionType)}&driver=${encodeURIComponent(compNum)}${lapQuery}`
      const res = await apiFetch(path, { signal: controller.signal, timeoutMs: 15000 })
      const json = await res.json()
      if (requestId !== compareRequestRef.current) return
      if (json.status === 'success' && json.series?.length > 0) setCompareTelemetry(json)
    } catch (err) {
      if (err.name === 'AbortError' || requestId !== compareRequestRef.current) return
      console.warn('Ghost telemetry offline, synthesizing fallback:', err.message)
      if (telemetry?.series) {
        const compInfo = availableDrivers.find(d => String(d.number || d.id) === String(compNum))
        setCompareTelemetry(synthesizeComparisonFallback(telemetry, compNum, compInfo))
      }
    } finally {
      if (requestId === compareRequestRef.current) setLoadingCompare(false)
    }
  }

  const handleSelectLap = (lapNum) => {
    setIsPlaying(false); setPlaybackTime(0.0)
    setSelectedRange(null); setActiveCorner(null)
    setSelectedLap(lapNum)
    loadTelemetry(lapNum)
    if (compareDriver) loadCompareTelemetry(compareDriver, lapNum)
  }

  // Reset chartReady when session params change — user must re-load
  useEffect(() => {
    setChartReady(false)
    setTelemetry(null)
    setSelectedRange(null)
    setActiveCorner(null)
    setHoverMetrics(null)
  }, [mode, year, event, sessionType, driver, cycleKey]) // eslint-disable-line react-hooks/exhaustive-deps

  // Main sync effect — only fires when chartReady is true
  useEffect(() => {
    if (!chartReady) return
    let isMounted = true
    const controller = new AbortController()

    setIsPlaying(false); setPlaybackTime(0.0)
    setSelectedRange(null); setActiveCorner(null)
    setHoverMetrics(null); setSelectedLap(null)

    const run = async () => {
      setError(null); setLoading(true)
      try {
        const path = mode === 'ev'
          ? `/api/ev/telemetry/stream?cycle_key=${encodeURIComponent(cycleKey || 'nasa_b0005_sag')}`
          : `/api/telemetry/stream?year=${year}&event=${encodeURIComponent(event)}&session_type=${encodeURIComponent(sessionType)}&driver=${encodeURIComponent(driver || '1')}`
        const res = await apiFetch(path, { signal: controller.signal })
        const json = await res.json()
        if (!isMounted) return
        if (json.status === 'success' && json.series?.length > 0) {
          setTelemetry(json)
          if (json.lap_number != null) setSelectedLap(json.lap_number)
        } else {
          throw new Error('Malformed telemetry payload')
        }
      } catch (err) {
        if (err.name === 'AbortError' || !isMounted) return
        console.warn('Backend offline, using labelled synthetic fallback:', err.message)
        setError(`Telemetry API unavailable (${err.message}). Displaying simulated waveform.`)
        setTelemetry({ ...(mode === 'ev' ? generateEVTelemetrySeries() : generateF1TelemetrySeries()), simulated: true })
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    run()

    if (compareDriver && String(compareDriver) === String(driver)) {
      setCompareDriver(null); setCompareTelemetry(null)
    } else if (compareDriver && !isEV) {
      loadCompareTelemetry(compareDriver, null)
    }

    return () => { isMounted = false; controller.abort() }
  }, [chartReady, mode, year, event, sessionType, driver, cycleKey]) // eslint-disable-line react-hooks/exhaustive-deps

  const compareDriverInfo = useMemo(() => {
    if (!compareDriver) return null
    return availableDrivers.find(d => String(d.number || d.id) === String(compareDriver)) || {
      name: compareTelemetry?.driver_name || `Driver #${compareDriver}`,
      code: compareTelemetry?.driver_code || `D${compareDriver}`,
      color: compareTelemetry?.team_color || '#FF8000',
      team: compareTelemetry?.team_name || 'Formula 1',
      number: String(compareDriver),
    }
  }, [compareDriver, availableDrivers, compareTelemetry])

  const overlayData = useMemo(() => {
    if (isEV || !compareTelemetry || !telemetry?.series || !compareTelemetry?.series) return null
    return computeTelemetryOverlay(telemetry, compareTelemetry)
  }, [telemetry, compareTelemetry, isEV])

  const selectionStats = useMemo(() => {
    if (!selectedRange || !telemetry?.series) return null
    if (isEV) {
      const [times, voltages, currents, temperatures] = telemetry.series
      let minV = Infinity, maxV = -Infinity, maxTemp = -Infinity, peakCurr = -Infinity, count = 0
      for (let i = 0; i < times.length; i++) {
        if (times[i] >= selectedRange.start && times[i] <= selectedRange.end) {
          count++
          if (voltages[i] < minV) minV = voltages[i]
          if (voltages[i] > maxV) maxV = voltages[i]
          if (temperatures[i] > maxTemp) maxTemp = temperatures[i]
          if (currents[i] > peakCurr) peakCurr = currents[i]
        }
      }
      if (count === 0) return null
      return { isEV: true, minV: minV.toFixed(2), maxV: maxV.toFixed(2), deltaV: (maxV - minV).toFixed(2), maxTemp: maxTemp.toFixed(1), peakCurr: peakCurr.toFixed(1), pointsCount: count }
    } else {
      const [times, speeds, , brakes] = telemetry.series
      let minSpeed = Infinity, maxSpeed = -Infinity, maxBrake = 0, count = 0
      for (let i = 0; i < times.length; i++) {
        if (times[i] >= selectedRange.start && times[i] <= selectedRange.end) {
          count++
          if (speeds[i] < minSpeed) minSpeed = speeds[i]
          if (speeds[i] > maxSpeed) maxSpeed = speeds[i]
          if (brakes[i] > maxBrake) maxBrake = brakes[i]
        }
      }
      if (count === 0) return null
      return { isEV: false, minSpeed: Math.round(minSpeed), maxSpeed: Math.round(maxSpeed), deltaSpeed: Math.round(maxSpeed - minSpeed), maxBrake, pointsCount: count }
    }
  }, [selectedRange, telemetry, isEV])

  // Build uPlot chart
  useEffect(() => {
    if (!telemetry || !chartContainerRef.current || !chartReady) return
    if (uplotRef.current) { uplotRef.current.destroy(); uplotRef.current = null }
    const containerWidth = chartContainerRef.current.clientWidth || 860
    const containerHeight = Math.max(200, Math.round(chartContainerRef.current.clientHeight) || 280)
    let opts, chartData

    if (isEV) {
      const [times, voltages, currents, temperatures] = telemetry.series
      chartData = [times, voltages, currents, temperatures]
      opts = {
        width: containerWidth, height: containerHeight,
        cursor: { drag: { x: true, y: false, setScale: false }, points: { size: 6, width: 2 }, sync: { key: 'ev_telemetry' } },
        select: { show: true, over: true },
        hooks: {
          setCursor: [(u) => {
            const idx = u.cursor.idx
            if (idx != null && idx >= 0 && idx < times.length) {
              const t = times[idx]
              const anchor = anchorFnRef.current(t)
              setHoverMetrics({ time: t, voltage: voltages[idx], current: currents[idx], temperature: temperatures[idx], corner: anchor?.name || null })
            }
          }],
          setSelect: [(u) => {
            const minX = u.posToVal(u.select.left, 'x')
            const maxX = u.posToVal(u.select.left + u.select.width, 'x')
            if (maxX > minX + 0.3) setSelectedRange({ start: Math.round(minX * 10) / 10, end: Math.round(maxX * 10) / 10, duration: Math.round((maxX - minX) * 10) / 10 })
          }],
        },
        scales: { x: { time: false }, voltage: { range: [2.5, 4.35] }, current: { range: [-25, 85] }, temperature: { range: [15, 75] } },
        axes: [
          { scale: 'x', stroke: '#94a3b8', font: '10px "JetBrains Mono", monospace', grid: { stroke: '#151c28', width: 1 }, ticks: { stroke: '#283244', width: 1 }, values: (s, ticks) => ticks.map(t => t != null ? `${t.toFixed(1)}s` : '') },
          { scale: 'voltage', stroke: '#00f0ff', font: '10px "JetBrains Mono", monospace', size: 65, grid: { stroke: '#151c28', width: 1 }, ticks: { stroke: '#283244', width: 1 }, values: (s, ticks) => ticks.map(v => v != null ? `${v.toFixed(2)} V` : '') },
          { side: 1, scale: 'current', stroke: '#f59e0b', font: '10px "JetBrains Mono", monospace', size: 55, grid: { show: false }, ticks: { stroke: '#283244', width: 1 }, values: (s, ticks) => ticks.map(v => v != null ? `${v.toFixed(0)} A` : '') },
        ],
        series: [
          { label: 'Time', value: (s, v) => v != null ? `${v.toFixed(2)}s` : '' },
          { label: 'Voltage', scale: 'voltage', show: visibleChannels.voltage, stroke: '#00f0ff', width: 1.8, fill: 'rgba(0,240,255,0.08)', value: (s, v) => v != null ? `${v.toFixed(2)} V` : '0 V' },
          { label: 'Current', scale: 'current', show: visibleChannels.current, stroke: '#f59e0b', width: 1.5, fill: 'rgba(245,158,11,0.08)', value: (s, v) => v != null ? `${v.toFixed(1)} A` : '0 A' },
          { label: 'Temperature', scale: 'temperature', show: visibleChannels.temperature, stroke: '#ff2a4b', width: 1.5, fill: 'rgba(255,42,75,0.08)', value: (s, v) => v != null ? `${v.toFixed(1)} °C` : '0 °C' },
        ],
      }
    } else {
      const [times, speeds, throttles, brakes, gears, rpms] = telemetry.series
      const priCode = telemetry.driver_code || 'Pri'
      let data = [times, speeds, throttles, brakes]
      const series = [
        { label: 'Time', value: (s, v) => v != null ? `${v.toFixed(2)}s` : '' },
        { label: `${priCode} Speed`, scale: 'speed', show: visibleChannels.speed, stroke: '#ffffff', width: 1.8, fill: 'rgba(255,255,255,0.04)', value: (s, v) => v != null ? `${v.toFixed(0)} km/h` : '0 km/h' },
        { label: `${priCode} Throttle`, scale: 'pct', show: visibleChannels.throttle, stroke: '#05df72', width: 1.5, fill: 'rgba(5,223,114,0.08)', value: (s, v) => v != null ? `${v.toFixed(0)}%` : '0%' },
        { label: `${priCode} Brake`, scale: 'pct', show: visibleChannels.brake, stroke: '#ff2a4b', width: 1.7, fill: 'rgba(255,42,75,0.16)', value: (s, v) => v != null ? `${v.toFixed(0)}%` : '0%' },
      ]
      const axes = [
        { scale: 'x', stroke: '#94a3b8', font: '10px "JetBrains Mono", monospace', grid: { stroke: '#151c28', width: 1 }, ticks: { stroke: '#283244', width: 1 }, values: (s, ticks) => ticks.map(t => t != null ? `${t.toFixed(1)}s` : '') },
        { scale: 'speed', stroke: '#ffffff', font: '10px "JetBrains Mono", monospace', size: 68, grid: { stroke: '#151c28', width: 1 }, ticks: { stroke: '#283244', width: 1 }, values: (s, ticks) => ticks.map(v => v != null ? `${v.toFixed(0)} km/h` : '') },
        { side: 1, scale: 'pct', stroke: '#05df72', font: '10px "JetBrains Mono", monospace', size: 45, grid: { show: false }, ticks: { stroke: '#283244', width: 1 }, values: (s, ticks) => ticks.map(v => v != null ? `${v.toFixed(0)}%` : '') },
      ]
      const scales = { x: { time: false }, speed: { range: [0, 315] }, pct: { range: [0, 100] } }
      if (overlayData) {
        data = [times, speeds, throttles, brakes, overlayData.resampledRefSpeeds, overlayData.resampledRefThrottles, overlayData.resampledRefBrakes, overlayData.deltaT]
        const refCode = compareDriverInfo?.code || 'Ref'
        const refColor = compareDriverInfo?.color || '#FF8000'
        series.push({ label: `${refCode} Spd`, scale: 'speed', show: visibleChannels.refSpeed, stroke: refColor, width: 1.8, dash: [5, 4], value: (s, v) => v != null ? `${v.toFixed(0)} km/h` : '0 km/h' })
        series.push({ label: `${refCode} Thr`, scale: 'pct', show: visibleChannels.refThrottle, stroke: '#22d3ee', width: 1.3, dash: [4, 4], value: (s, v) => v != null ? `${v.toFixed(0)}%` : '0%' })
        series.push({ label: `${refCode} Brk`, scale: 'pct', show: visibleChannels.refBrake, stroke: '#fb7185', width: 1.3, dash: [4, 4], value: (s, v) => v != null ? `${v.toFixed(0)}%` : '0%' })
        series.push({ label: `Δt`, scale: 'delta', show: visibleChannels.delta, stroke: '#c084fc', width: 2.2, fill: 'rgba(192,132,252,0.12)', value: (s, v) => v != null ? `${v >= 0 ? '+' : ''}${v.toFixed(3)}s` : '0.000s' })
        let maxAbsDelta = 0.25
        overlayData.deltaT.forEach(v => { if (Math.abs(v) > maxAbsDelta) maxAbsDelta = Math.abs(v) })
        scales.delta = { range: [-Math.min(Math.max(Math.ceil(maxAbsDelta * 1.25 * 10) / 10, 0.5), 10), Math.min(Math.max(Math.ceil(maxAbsDelta * 1.25 * 10) / 10, 0.5), 10)] }
        axes.push({ side: 1, scale: 'delta', stroke: '#c084fc', font: '10px "JetBrains Mono", monospace', size: 55, grid: { stroke: 'rgba(192,132,252,0.15)', width: 1, dash: [2, 2] }, ticks: { stroke: '#c084fc', width: 1 }, values: (s, ticks) => ticks.map(v => v != null ? `${v >= 0 ? '+' : ''}${v.toFixed(2)}s` : '') })
      }
      chartData = data
      opts = {
        width: containerWidth, height: containerHeight,
        cursor: { drag: { x: true, y: false, setScale: false }, points: { size: 6, width: 2 } },
        select: { show: true, over: true },
        hooks: {
          setCursor: [(u) => {
            const idx = u.cursor.idx
            if (idx != null && idx >= 0 && idx < times.length) {
              const t = times[idx]
              const corner = anchorFnRef.current(t)
              const metrics = { time: t, speed: speeds[idx], throttle: throttles[idx], brake: brakes[idx], gear: gears ? gears[idx] : 1, rpm: rpms ? rpms[idx] : 0, corner: corner?.name || null }
              if (overlayData) {
                metrics.refSpeed = overlayData.resampledRefSpeeds[idx]
                metrics.deltaT = overlayData.deltaT[idx]
                metrics.refCode = compareDriverInfo?.code
                metrics.refColor = compareDriverInfo?.color
              }
              setHoverMetrics(metrics)
            }
          }],
          setSelect: [(u) => {
            const minX = u.posToVal(u.select.left, 'x')
            const maxX = u.posToVal(u.select.left + u.select.width, 'x')
            if (maxX > minX + 0.3) setSelectedRange({ start: Math.round(minX * 10) / 10, end: Math.round(maxX * 10) / 10, duration: Math.round((maxX - minX) * 10) / 10 })
          }],
        },
        scales,
        axes,
        series,
      }
    }

    try { uplotRef.current = new uPlot(opts, chartData, chartContainerRef.current) }
    catch (e) { console.error('uPlot mount failed:', e) }
    requestAnimationFrame(fitChart)

    return () => {
      if (uplotRef.current) { uplotRef.current.destroy(); uplotRef.current = null }
    }
  }, [telemetry, compareTelemetry, overlayData, visibleChannels, isEV, chartReady, compareDriverInfo?.code, compareDriverInfo?.color])

  // Keep the canvas (plus its live legend) inside the chart slot
  useEffect(() => {
    const el = chartContainerRef.current
    if (!el || !chartReady) return
    const ro = new ResizeObserver(fitChart)
    ro.observe(el)
    window.addEventListener('resize', fitChart)
    fitChart()
    return () => { ro.disconnect(); window.removeEventListener('resize', fitChart) }
  }, [chartReady, telemetry, showTrackMap])

  // Visually select a preset range on the chart
  useEffect(() => {
    if (!presetRange) return
    const [start, end] = presetRange
    const timer = setTimeout(() => {
      if (!uplotRef.current) return
      setSelectedRange({ start, end, duration: Math.round((end - start) * 10) / 10 })
      setActiveCorner(null)
      const leftPx = uplotRef.current.valToPos(start, 'x')
      const rightPx = uplotRef.current.valToPos(end, 'x')
      uplotRef.current.setSelect({ left: leftPx, top: 0, width: rightPx - leftPx, height: uplotRef.current.bbox.height }, false)
    }, 350)
    return () => clearTimeout(timer)
  }, [presetRange])

  // Playback loop
  useEffect(() => {
    if (!isPlaying || !telemetry?.series) {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
      lastTimeRef.current = null
      return
    }
    const times = telemetry.series[0]
    if (!times?.length) return
    const maxTime = times[times.length - 1]
    const loop = (timestamp) => {
      if (lastTimeRef.current == null) lastTimeRef.current = timestamp
      const delta = (timestamp - lastTimeRef.current) / 1000
      lastTimeRef.current = timestamp
      setPlaybackTime(prev => { let next = prev + delta * playbackSpeed; if (next >= maxTime) next = 0; return next })
      animFrameRef.current = requestAnimationFrame(loop)
    }
    animFrameRef.current = requestAnimationFrame(loop)
    return () => { if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current) }
  }, [isPlaying, playbackSpeed, telemetry])

  // Sync playback tick to hoverMetrics + uPlot cursor
  useEffect(() => {
    if (!isPlaying || !telemetry?.series) return
    const times = telemetry.series[0]
    if (!times?.length) return
    let low = 0, high = times.length - 1
    while (low <= high) { const mid = (low + high) >> 1; if (times[mid] < playbackTime) low = mid + 1; else high = mid - 1 }
    const idx = Math.min(Math.max(low, 0), times.length - 1)
    const t = times[idx]
    const anchor = anchorFnRef.current(t)
    if (isEV) {
      const [, voltages, currents, temperatures, socs] = telemetry.series
      setHoverMetrics({ time: t, voltage: voltages[idx], current: currents[idx], temperature: temperatures[idx], soc: socs ? socs[idx] : null, corner: anchor?.name || null })
    } else {
      const [, speeds, throttles, brakes, gears, rpms] = telemetry.series
      setHoverMetrics({ time: t, speed: speeds[idx], throttle: throttles[idx], brake: brakes[idx], gear: gears ? gears[idx] : 7, rpm: rpms ? rpms[idx] : 11200, corner: anchor?.name || null })
    }
    if (uplotRef.current) {
      const leftPos = uplotRef.current.valToPos(t, 'x')
      if (leftPos != null && !isNaN(leftPos)) uplotRef.current.setCursor({ left: leftPos, top: 40 })
    }
  }, [playbackTime, isPlaying, telemetry, isEV])

  const handleAnchorSelect = (anchor) => {
    setActiveCorner(anchor.name)
    const range = { start: anchor.start, end: anchor.end, duration: Math.round((anchor.end - anchor.start) * 10) / 10 }
    setSelectedRange(range)
    if (uplotRef.current) {
      const leftPx = uplotRef.current.valToPos(anchor.start, 'x')
      const rightPx = uplotRef.current.valToPos(anchor.end, 'x')
      uplotRef.current.setSelect({ left: leftPx, top: 0, width: rightPx - leftPx, height: uplotRef.current.bbox.height }, false)
    }
    if (onSelectAnomaly) onSelectAnomaly(range.start, range.end)
  }

  const triggerAnalysis = () => { if (selectedRange && onSelectAnomaly) onSelectAnomaly(selectedRange.start, selectedRange.end) }

  const resetView = () => {
    setSelectedRange(null); setActiveCorner(null)
    if (uplotRef.current) {
      uplotRef.current.setSelect({ left: 0, top: 0, width: 0, height: 0 }, false)
      uplotRef.current.setData(uplotRef.current.data)
    }
  }

  const toggleChannel = (key) => setVisibleChannels(prev => ({ ...prev, [key]: !prev[key] }))
  const activeAnchorList = isEV ? telemetry?.phase_anchors : telemetry?.corners

  // ── Render ────────────────────────────────────────────────────
  return (
    <div
      className="rounded-xl overflow-hidden shadow-2xl"
      style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-mid)' }}
      role="region"
      aria-label="High-Frequency Telemetry Workspace"
    >
      {/* Pre-chart: session selector state */}
      {!chartReady && (
        <div className="flex flex-col items-center justify-center gap-6 p-12 text-center" style={{ minHeight: '340px' }}>
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
            style={{ background: isEV ? 'rgba(0,255,136,0.08)' : 'rgba(232,255,0,0.08)', border: `1px solid ${isEV ? 'rgba(0,255,136,0.25)' : 'rgba(232,255,0,0.25)'}` }}
          >
            <Activity size={28} style={{ color: isEV ? 'var(--ev-signal)' : 'var(--f1-signal)' }} />
          </div>
          <div>
            <h3 className="text-[18px] font-bold mb-2"
              style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)', letterSpacing: '-0.02em' }}
            >
              {isEV ? 'Select a battery pack to analyze' : 'Select a session and driver to analyze'}
            </h3>
            <p className="text-[13px] max-w-sm mx-auto"
              style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif", lineHeight: 1.6 }}
            >
              {isEV
                ? 'Choose a cycle from the selector above, then load the 50Hz electrochemical telemetry stream.'
                : 'Choose year, event, session type, and driver from the selectors above, then load the lap telemetry.'}
            </p>
          </div>
          <button type="button" onClick={() => setChartReady(true)}
            className="flex items-center gap-2.5 px-6 py-3 rounded-xl font-bold text-[13px] cursor-pointer transition-all"
            style={{ fontFamily: "'Space Grotesk', sans-serif", background: isEV ? 'var(--ev-signal)' : 'var(--f1-signal)', color: '#000', border: 'none', letterSpacing: '0.02em' }}
            onMouseEnter={e => { e.currentTarget.style.opacity = '0.9' }}
            onMouseLeave={e => { e.currentTarget.style.opacity = '1' }}
          >
            <Play size={14} fill="currentColor" />
            {isEV ? 'Load BMS Telemetry Stream' : 'Load 100Hz Telemetry Stream'}
          </button>
          <p className="text-[11px]" style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}>
            {isEV ? '50Hz · NASA Ames Li-ion · NMC 811' : '100Hz · FastF1 3.4 · FIA Data Feed'}
          </p>
        </div>
      )}

      {/* Full chart workspace */}
      {chartReady && (
        <>
          {/* Chart header bar */}
          <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5"
            style={{ borderBottom: '1px solid var(--border-dim)', background: 'var(--bg-surface-1)' }}
          >
            <div className="flex items-center gap-2 flex-wrap">
              <div className="flex items-center gap-1.5">
                <span className="live-beacon" aria-hidden="true" />
                <span
                  className="text-[10px] font-bold tracking-[0.1em] uppercase"
                  style={{ color: isEV ? 'var(--ev-signal)' : 'var(--f1-signal)', fontFamily: "'JetBrains Mono', monospace" }}
                >
                  {isEV ? '50Hz EV BMS Battery Feed' : sampleRateHz ? `${sampleRateHz}Hz Telemetry Feed` : 'Telemetry Canvas'}
                </span>
                {telemetry?.simulated && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded"
                    style={{ background: 'rgba(255,184,0,0.12)', color: '#FFB800', border: '1px solid rgba(255,184,0,0.3)', fontFamily: "'JetBrains Mono', monospace" }}
                  >SIMULATED FEED</span>
                )}
                {telemetry?.source === 'OPENF1' && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded"
                    title={telemetry.data_source || 'Telemetry data: OpenF1 (CC BY-NC-SA 4.0)'}
                    style={{ background: 'rgba(0,240,255,0.1)', color: '#00f0ff', border: '1px solid rgba(0,240,255,0.3)', fontFamily: "'JetBrains Mono', monospace" }}
                  >OPENF1 · CC BY-NC-SA</span>
                )}
              </div>
              <div className="hidden sm:flex items-center gap-1.5 font-mono text-[10px]">
                <span className="px-2 py-0.5 rounded border"
                  style={{ background: 'var(--bg-surface-3)', border: '1px solid var(--border-dim)', color: 'var(--text-secondary)' }}
                >{telemetry ? telemetry.session_id : 'Syncing…'}</span>
                <span className="px-2 py-0.5 rounded border font-semibold"
                  style={{ background: isEV ? 'rgba(0,255,136,0.08)' : 'rgba(232,255,0,0.08)', borderColor: isEV ? 'rgba(0,255,136,0.25)' : 'rgba(232,255,0,0.25)', color: isEV ? 'var(--ev-signal)' : 'var(--f1-signal)' }}
                >{telemetry?.driver_name ? `${telemetry.driver_name} #${telemetry.driver}` : isEV ? 'Unit EV-B0005' : 'Car #1 VER'}</span>
                {!isEV && telemetry?.lap_number && (
                  <span className="px-2 py-0.5 rounded border"
                    style={{ background: 'var(--bg-surface-3)', border: '1px solid var(--border-dim)', color: 'var(--text-muted)' }}
                  >Lap {telemetry.lap_number}{telemetry.is_fastest_lap && <span style={{ color: '#c084fc', marginLeft: '4px' }}>P1</span>} ({telemetry.lap_time_seconds}s)</span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 font-mono text-[10px] overflow-x-auto">
              {hoverMetrics ? (
                <div className="flex items-center gap-2.5 px-3 py-1.5 rounded"
                  style={{ background: 'var(--bg-surface-3)', border: '1px solid var(--border-dim)' }}
                >
                  <span style={{ color: 'var(--text-disabled)' }}>T:</span>
                  <span style={{ color: 'var(--text-bright)', fontWeight: 700 }}>{hoverMetrics.time?.toFixed(2)}s</span>
                  {isEV ? (
                    <>
                      <span style={{ color: 'var(--accent)' }}>V: <strong>{hoverMetrics.voltage?.toFixed(2)}V</strong></span>
                      <span style={{ color: '#f59e0b' }}>A: <strong>{hoverMetrics.current?.toFixed(1)}A</strong></span>
                      <span style={{ color: '#ff2a4b' }}>T: <strong>{hoverMetrics.temperature?.toFixed(1)}°C</strong></span>
                    </>
                  ) : (
                    <>
                      <span style={{ color: '#fff' }}><strong>{hoverMetrics.speed?.toFixed(0)}</strong> km/h</span>
                      <span style={{ color: '#05df72' }}>Thr: <strong>{hoverMetrics.throttle}%</strong></span>
                      <span style={{ color: '#ff2a4b' }}>Brk: <strong>{hoverMetrics.brake}%</strong></span>
                      <span style={{ color: '#f59e0b' }}>G<strong>{hoverMetrics.gear}</strong></span>
                      {hoverMetrics.deltaT != null && (
                        <span className="px-1.5 py-0.5 rounded font-bold"
                          style={{ background: hoverMetrics.deltaT >= 0 ? 'rgba(5,223,114,0.12)' : 'rgba(255,42,75,0.12)', color: hoverMetrics.deltaT >= 0 ? '#05df72' : '#ff2a4b', border: `1px solid ${hoverMetrics.deltaT >= 0 ? 'rgba(5,223,114,0.25)' : 'rgba(255,42,75,0.25)'}` }}
                        >Δt {hoverMetrics.deltaT >= 0 ? '+' : ''}{hoverMetrics.deltaT.toFixed(3)}s</span>
                      )}
                    </>
                  )}
                  {hoverMetrics.corner && (
                    <span className="px-1.5 py-0.5 rounded"
                      style={{ background: 'rgba(232,255,0,0.08)', color: 'var(--f1-signal)', border: '1px solid rgba(232,255,0,0.2)' }}
                    >{hoverMetrics.corner}</span>
                  )}
                </div>
              ) : (
                <span style={{ color: 'var(--text-disabled)' }}>{isEV ? 'Hover for pack metrics' : 'Hover for telemetry'}</span>
              )}
              <div className="flex items-center gap-0.5 p-0.5 rounded"
                style={{ background: 'var(--bg-surface-3)', border: '1px solid var(--border-dim)' }}
              >
                {(isEV
                  ? [{ key: 'voltage', label: 'V', color: 'var(--accent)' }, { key: 'current', label: 'A', color: '#f59e0b' }, { key: 'temperature', label: '°C', color: '#ff2a4b' }]
                  : [{ key: 'speed', label: 'Spd', color: '#fff' }, { key: 'throttle', label: 'Thr', color: '#05df72' }, { key: 'brake', label: 'Brk', color: '#ff2a4b' }]
                ).map(({ key, label, color }) => (
                  <button key={key} onClick={() => toggleChannel(key)}
                    className="px-2 py-1 rounded text-[10px] font-bold cursor-pointer"
                    style={{ background: visibleChannels[key] ? (color === '#fff' ? 'rgba(255,255,255,0.1)' : `${color}18`) : 'transparent', color: visibleChannels[key] ? color : 'var(--text-disabled)', border: 'none' }}
                  >{label}</button>
                ))}
              </div>
              <button onClick={() => setShowTrackMap(!showTrackMap)}
                className="px-2.5 py-1 rounded text-[10px] font-semibold cursor-pointer"
                style={{ background: showTrackMap ? (isEV ? 'rgba(0,255,136,0.1)' : 'rgba(232,255,0,0.1)') : 'var(--bg-surface-3)', color: showTrackMap ? (isEV ? 'var(--ev-signal)' : 'var(--f1-signal)') : 'var(--text-muted)', border: `1px solid ${showTrackMap ? (isEV ? 'rgba(0,255,136,0.25)' : 'rgba(232,255,0,0.25)') : 'var(--border-dim)'}` }}
              >{isEV ? 'Pack' : 'Map'}</button>
              <button onClick={() => loadTelemetry()}
                className="p-1.5 rounded cursor-pointer"
                style={{ background: 'var(--bg-surface-3)', border: '1px solid var(--border-dim)', color: 'var(--text-muted)' }}
                title="Reload telemetry"
                onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)' }}
                onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)' }}
              ><RefreshCw size={12} /></button>
            </div>
          </div>

          {/* Chart + side panel grid */}
          <div className={`grid grid-cols-1 ${showTrackMap ? 'xl:grid-cols-4 lg:grid-cols-3' : ''} gap-0 items-start`}>
            <div ref={chartColumnRef} className={`${showTrackMap ? 'xl:col-span-3 lg:col-span-2' : ''} space-y-0 min-w-0`}>
              {error && (
                <div className="flex items-start gap-2 px-4 py-2 text-[11px]"
                  style={{ background: 'rgba(255,184,0,0.06)', borderBottom: '1px solid rgba(255,184,0,0.2)', color: '#FFB800', fontFamily: "'JetBrains Mono', monospace" }}
                >
                  <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1" style={{ background: '#FFB800' }} />
                  <span>{error}</span>
                </div>
              )}
              {!isEV && telemetry?.laps_summary && telemetry.laps_summary.length > 0 && (
                <LapStintCollapsible
                  lapsSummary={telemetry.laps_summary}
                  activeLapNumber={telemetry.lap_number || selectedLap || 1}
                  onSelectLap={handleSelectLap}
                  totalLaps={telemetry.total_laps || telemetry.laps_summary.length}
                  sessionType={sessionType}
                  circuitName={telemetry.circuit_name || event}
                />
              )}
              {!isEV && (
                <GhostComparisonCollapsible
                  compareDriver={compareDriver}
                  setCompareDriver={setCompareDriver}
                  compareTelemetry={compareTelemetry}
                  setCompareTelemetry={setCompareTelemetry}
                  loadCompareTelemetry={loadCompareTelemetry}
                  loadingCompare={loadingCompare}
                  availableDrivers={availableDrivers}
                  driver={driver}
                  compareDriverInfo={compareDriverInfo}
                  visibleChannels={visibleChannels}
                  toggleChannel={toggleChannel}
                  telemetry={telemetry}
                />
              )}
              {/* uPlot canvas */}
              <div className="relative" style={{ height: `${chartHeight}px`, borderTop: '1px solid var(--border-dim)', borderBottom: '1px solid var(--border-dim)' }}>
                {loading && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-xs"
                    style={{ color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}
                  >
                    <Activity className="animate-spin" size={18} style={{ color: isEV ? 'var(--ev-signal)' : 'var(--f1-signal)' }} />
                    <span>{isEV ? 'Streaming 50Hz BMS telemetry…' : 'Streaming 100Hz lap telemetry…'}</span>
                  </div>
                )}
                <div ref={chartContainerRef} className="w-full h-full" style={{ display: loading ? 'none' : 'block' }} />
              </div>
              <AnchorsCollapsible
                isEV={isEV}
                activeAnchorList={activeAnchorList}
                activeCorner={activeCorner}
                handleAnchorSelect={handleAnchorSelect}
                resetView={resetView}
                circuitName={telemetry?.circuit_name}
              />
            </div>
            {showTrackMap && (
              <div ref={sidePanelRef} className="xl:col-span-1 lg:col-span-1" style={{ borderLeft: '1px solid var(--border-dim)' }}>
                {isEV ? (
                  <BatteryPackMap
                    packTopology={telemetry?.pack_topology}
                    hoverTime={isPlaying ? playbackTime : (hoverMetrics?.time ?? null)}
                    hoverMetrics={hoverMetrics}
                    selectedRange={selectedRange}
                    onModuleClick={(mod) => handleAnchorSelect({ name: mod.id, start: mod.anomaly_window?.[0] ?? 40.0, end: mod.anomaly_window?.[1] ?? 58.0, type: mod.fault_flag || 'Cell Anomaly' })}
                  />
                ) : (
                  <TrackMap
                    trackMap={telemetry?.track_map}
                    hoverTime={isPlaying ? playbackTime : (hoverMetrics?.time ?? null)}
                    selectedRange={selectedRange}
                    activeCorner={activeCorner}
                    onCornerClick={handleAnchorSelect}
                    driver={driver}
                    driverCode={telemetry?.driver_code}
                    circuitName={telemetry?.circuit_name || event}
                    eventName={telemetry?.event_name || event}
                    lapLength={telemetry?.lap_len || telemetry?.track_map?.lap_len}
                    lapNumber={telemetry?.lap_number || selectedLap || 1}
                    compareTrackMap={compareTelemetry?.track_map}
                    compareDriver={compareDriver}
                    compareDriverCode={compareDriverInfo?.code || compareTelemetry?.driver_code}
                    compareColor={compareDriverInfo?.color || compareTelemetry?.team_color}
                  />
                )}
              </div>
            )}
          </div>

          {/* Playback + ROI action bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3"
            style={{ borderTop: '1px solid var(--border-dim)', background: 'var(--bg-surface-1)' }}
          >
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1 p-0.5 rounded"
                style={{ background: 'var(--bg-surface-3)', border: '1px solid var(--border-dim)' }}
              >
                <button type="button" onClick={() => setIsPlaying(!isPlaying)}
                  className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-semibold cursor-pointer"
                  style={{ background: isPlaying ? 'rgba(5,223,114,0.12)' : 'transparent', color: isPlaying ? '#05df72' : 'var(--text-muted)', border: 'none' }}
                >
                  {isPlaying ? <Pause size={10} /> : <Play size={10} />}
                  <span>{isPlaying ? 'Pause' : 'Replay'}</span>
                </button>
                <button type="button" onClick={() => { setIsPlaying(false); setPlaybackTime(0.0) }}
                  className="p-1 rounded cursor-pointer"
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-disabled)' }}
                  onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-muted)' }}
                  onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-disabled)' }}
                ><RotateCcw size={10} /></button>
                {[1.0, 2.0, 4.0].map(spd => (
                  <button key={spd} type="button" onClick={() => setPlaybackSpeed(spd)}
                    className="px-1.5 py-1 rounded text-[9px] font-bold cursor-pointer"
                    style={{ background: playbackSpeed === spd ? 'rgba(232,255,0,0.12)' : 'transparent', color: playbackSpeed === spd ? 'var(--f1-signal)' : 'var(--text-disabled)', border: 'none' }}
                  >{spd}x</button>
                ))}
                <span className="px-2 text-[10px] font-mono" style={{ color: 'var(--f1-signal)', borderLeft: '1px solid var(--border-dim)' }}>
                  {isPlaying && <span style={{ color: '#05df72', marginRight: '4px' }}>●</span>}
                  {playbackTime.toFixed(1)}s / {telemetry?.lap_time_seconds ?? 0}s
                </span>
              </div>
              {selectedRange ? (
                <div className="flex items-center gap-2 font-mono text-[11px]">
                  <span className="px-2 py-0.5 rounded font-bold"
                    style={{ background: 'rgba(0,212,255,0.08)', color: 'var(--accent)', border: '1px solid rgba(0,212,255,0.2)' }}
                  >ROI {selectedRange.start}s → {selectedRange.end}s (Δ{selectedRange.duration}s)</span>
                  {selectionStats && (
                    <span style={{ color: 'var(--text-muted)' }}>
                      {selectionStats.isEV
                        ? `${selectionStats.maxV}V→${selectionStats.minV}V · ${selectionStats.peakCurr}A · ${selectionStats.maxTemp}°C`
                        : `${selectionStats.maxSpeed}→${selectionStats.minSpeed} km/h · Brk ${selectionStats.maxBrake}%`}
                    </span>
                  )}
                </div>
              ) : (
                <span className="text-[11px] flex items-center gap-1.5" style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}>
                  <Scissors size={12} style={{ color: isEV ? 'var(--ev-signal)' : 'var(--f1-signal)' }} />
                  Drag on the chart to select an anomaly window
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1.5 rounded text-[10px] font-semibold flex items-center gap-1.5"
                style={{ background: 'var(--bg-surface-3)', border: '1px solid var(--border-dim)', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}
              >
                {useVLM ? <Eye size={11} style={{ color: 'var(--accent)' }} /> : <Zap size={11} style={{ color: 'var(--f1-signal)' }} />}
                {useVLM ? 'Overcut 7B QLoRA' : 'Heuristic'}
              </span>
              <button onClick={triggerAnalysis} disabled={isAnalyzing || !selectedRange}
                className="flex items-center gap-2 px-4 py-2 rounded font-bold text-[12px] cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                style={{ fontFamily: "'Space Grotesk', sans-serif", background: isAnalyzing ? 'var(--border-mid)' : (isEV ? 'var(--ev-signal)' : 'var(--f1-signal)'), color: '#000', border: 'none', letterSpacing: '0.02em' }}
              >
                {isAnalyzing ? (
                  <><span className="w-3.5 h-3.5 rounded-full animate-spin" style={{ border: '2px solid rgba(0,0,0,0.3)', borderTopColor: '#000' }} /><span>Diagnosing…</span></>
                ) : (
                  <>{useVLM ? <Eye size={13} /> : <Zap size={13} />}<span>{isEV ? 'Execute EV Diagnosis' : 'Execute AI Diagnosis'}</span></>
                )}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
