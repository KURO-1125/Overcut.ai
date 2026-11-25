import React, { useMemo, useRef, useEffect } from 'react'
import { Zap, Wrench, ChevronLeft, ChevronRight, Layers } from 'lucide-react'

// Tire compound colors mapped to authentic FIA Pirelli palette
const COMPOUND_COLORS = {
  SOFT: {
    bg: '#ef4444',
    border: '#dc2626',
    text: '#fca5a5',
    glow: 'rgba(239, 68, 68, 0.4)'
  },
  MEDIUM: {
    bg: '#eab308',
    border: '#ca8a04',
    text: '#fde047',
    glow: 'rgba(234, 179, 8, 0.4)'
  },
  HARD: {
    bg: '#e2e8f0',
    border: '#cbd5e1',
    text: '#ffffff',
    glow: 'rgba(226, 232, 240, 0.4)'
  },
  INTERMEDIATE: {
    bg: '#10b981',
    border: '#059669',
    text: '#6ee7b7',
    glow: 'rgba(16, 185, 129, 0.4)'
  },
  WET: {
    bg: '#3b82f6',
    border: '#2563eb',
    text: '#93c5fd',
    glow: 'rgba(59, 130, 246, 0.4)'
  }
}

export default function RaceStintMacroBar({
  lapsSummary = [],
  activeLapNumber = 1,
  onSelectLap,
  totalLaps = 78,
  sessionType = 'R',
  circuitName = 'Circuit',
}) {
  const scrollContainerRef = useRef(null)

  // Find fastest lap in summary
  const fastestLap = useMemo(() => {
    if (!lapsSummary || lapsSummary.length === 0) return null
    return lapsSummary.find(l => l.is_fastest) || lapsSummary.reduce((best, cur) => {
      if (!cur.lap_time) return best
      if (!best || !best.lap_time) return cur
      return cur.lap_time < best.lap_time ? cur : best
    }, null)
  }, [lapsSummary])

  // Group into distinct stints based on stint property or pit flags
  const stints = useMemo(() => {
    if (!lapsSummary || lapsSummary.length === 0) return []
    const groups = []
    let currentStint = {
      id: 1,
      startLap: lapsSummary[0]?.lap_number || 1,
      endLap: lapsSummary[0]?.lap_number || 1,
      compound: lapsSummary[0]?.compound || 'MEDIUM',
      laps: []
    }

    for (let i = 0; i < lapsSummary.length; i++) {
      const lap = lapsSummary[i]
      const stintNum = lap.stint || 1

      if (stintNum !== currentStint.id) {
        groups.push(currentStint)
        currentStint = {
          id: stintNum,
          startLap: lap.lap_number,
          endLap: lap.lap_number,
          compound: lap.compound || 'HARD',
          laps: [lap]
        }
      } else {
        currentStint.endLap = lap.lap_number
        currentStint.laps.push(lap)
      }
    }
    groups.push(currentStint)
    return groups
  }, [lapsSummary])

  // Compute min/max valid lap times for height scaling (excluding in-laps and pit stops)
  const paceScale = useMemo(() => {
    const validTimes = lapsSummary
      .filter(l => l.lap_time && !l.pit && l.lap_time > 40 && l.lap_time < 180)
      .map(l => l.lap_time)

    if (validTimes.length === 0) return { min: 70, max: 80 }
    return {
      min: Math.min(...validTimes),
      max: Math.max(...validTimes)
    }
  }, [lapsSummary])

  // Auto-scroll active lap into view.
  // We use a short timeout so the DOM has painted before scrollIntoView is called.
  // The timeout is cleared on cleanup to prevent double-fire in React Strict Mode.
  useEffect(() => {
    if (!scrollContainerRef.current) return
    const id = setTimeout(() => {
      const activeEl = scrollContainerRef.current?.querySelector(`[data-lap="${activeLapNumber}"]`)
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
      }
    }, 50)
    return () => clearTimeout(id)
  }, [activeLapNumber])

  if (!lapsSummary || lapsSummary.length === 0) return null

  const isRace = sessionType.toUpperCase() === 'R'
  const activeLapObj = lapsSummary.find(l => l.lap_number === activeLapNumber) || lapsSummary[0]

  const handlePrevLap = () => {
    const prev = activeLapNumber > 1 ? activeLapNumber - 1 : 1
    onSelectLap?.(prev)
  }

  const handleNextLap = () => {
    const maxLap = lapsSummary[lapsSummary.length - 1]?.lap_number || totalLaps
    const next = activeLapNumber < maxLap ? activeLapNumber + 1 : maxLap
    onSelectLap?.(next)
  }

  const handleJumpToFastest = () => {
    if (fastestLap && onSelectLap) {
      onSelectLap(fastestLap.lap_number)
    }
  }

  return (
    <div className="bg-[#04060a] border border-zinc-800/80 rounded-sm p-3.5 space-y-3 font-mono shadow-xl relative overflow-hidden">
      {/* Background Subtle Track Glow */}
      <div className="absolute top-0 right-0 w-64 h-32 bg-amber-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* ─── Macro Bar Top Header ─── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2.5 border-b border-zinc-900 pb-2.5">
        
        {/* Left Title & Stint Meta */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-xs bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] font-bold">
            <Layers size={12} className="text-amber-400" />
            <span>{isRace ? 'RACE STINT TIMELINE' : 'QUALIFYING SESSIONS'}</span>
          </div>

          <span className="text-zinc-400 text-xs font-semibold">
            {circuitName} · <strong className="text-zinc-100">{lapsSummary.length} Laps</strong>
          </span>

          {/* Active Lap Badge */}
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-xs bg-zinc-900 border border-zinc-700 text-xs">
            <span className="text-zinc-400">ACTIVE:</span>
            <span className="text-amber-400 font-bold">Lap #{activeLapNumber}</span>
            {activeLapObj?.lap_time && (
              <span className="text-zinc-200">({activeLapObj.lap_time.toFixed(3)}s)</span>
            )}
            {activeLapObj?.compound && (
              <span
                className="px-1 py-0.2 rounded-2xs text-[9px] font-bold uppercase"
                style={{
                  backgroundColor: COMPOUND_COLORS[activeLapObj.compound]?.bg || '#71717a',
                  color: '#000000'
                }}
              >
                {activeLapObj.compound}
              </span>
            )}
          </div>
        </div>

        {/* Right Controls: Stepper, Jump to Fastest, Quick Lap Select */}
        <div className="flex items-center gap-1.5 flex-wrap">
          
          {/* Fastest Lap Shortcut */}
          {fastestLap && (
            <button
              type="button"
              onClick={handleJumpToFastest}
              className={`px-2 py-1 rounded-xs border text-[10px] font-bold transition-all flex items-center gap-1 ${
                activeLapNumber === fastestLap.lap_number
                  ? 'bg-purple-950/40 border-purple-500 text-purple-300 shadow-[0_0_10px_rgba(168,85,247,0.3)]'
                  : 'bg-[#090d14] border-purple-500/30 text-purple-400 hover:border-purple-500 hover:text-purple-200'
              }`}
              title={`Jump to Fastest Lap #${fastestLap.lap_number} (${fastestLap.lap_time}s)`}
            >
              <Zap size={11} className="text-purple-400 fill-purple-400" />
              <span>P1 LAP #{fastestLap.lap_number} ({fastestLap.lap_time}s)</span>
            </button>
          )}

          {/* Stepper Buttons */}
          <div className="flex items-center rounded-xs overflow-hidden border border-zinc-800 bg-[#080b11]">
            <button
              type="button"
              onClick={handlePrevLap}
              disabled={activeLapNumber <= 1}
              className="p-1 hover:bg-zinc-800 text-zinc-300 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title="Previous Lap"
            >
              <ChevronLeft size={13} />
            </button>
            <span className="px-2 text-[10px] text-zinc-300 select-none">
              {activeLapNumber} / {lapsSummary.length}
            </span>
            <button
              type="button"
              onClick={handleNextLap}
              disabled={activeLapNumber >= lapsSummary.length}
              className="p-1 hover:bg-zinc-800 text-zinc-300 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title="Next Lap"
            >
              <ChevronRight size={13} />
            </button>
          </div>

          {/* Direct Lap Jump Dropdown */}
          <select
            value={activeLapNumber}
            onChange={(e) => onSelectLap && onSelectLap(Number(e.target.value))}
            className="bg-[#080b11] border border-zinc-800 rounded-xs px-2 py-1 text-[11px] font-mono text-zinc-200 focus:outline-none focus:border-amber-500"
          >
            {lapsSummary.map(l => (
              <option key={l.lap_number} value={l.lap_number}>
                Lap {l.lap_number} {l.is_fastest ? '★ P1' : ''} {l.pit ? '🔧 PIT' : ''} {l.lap_time ? `(${l.lap_time.toFixed(2)}s)` : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ─── Stint Phase Markers (Stint 1, Pit Stop, Stint 2) ─── */}
      {isRace && stints.length > 1 && (
        <div className="flex items-center gap-2 text-[10px] text-zinc-400 overflow-x-auto pb-1">
          <span className="text-zinc-300 font-bold uppercase tracking-wider text-[9px]">STRATEGY:</span>
          {stints.map((stint, idx) => (
            <React.Fragment key={stint.id}>
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-2xs bg-zinc-900 border border-zinc-800">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: COMPOUND_COLORS[stint.compound]?.bg || '#71717a' }}
                />
                <span className="text-zinc-200 font-semibold">
                  STINT {stint.id} (L{stint.startLap}–L{stint.endLap})
                </span>
                <span className="text-zinc-300 capitalize">{stint.compound.toLowerCase()}</span>
              </div>
              {idx < stints.length - 1 && (
                <div className="flex items-center gap-1 text-amber-400/80 font-bold text-[9px]">
                  <Wrench size={10} />
                  <span>PIT STOP</span>
                  <span className="text-zinc-600">→</span>
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      )}

      {/* ─── Interactive Multi-Lap Visual Strip ─── */}
      <div
        ref={scrollContainerRef}
        className="relative overflow-x-auto overflow-y-hidden pb-1 scrollbar-thin scrollbar-thumb-zinc-800"
      >
        <div className="flex items-end gap-1 min-w-max py-2 px-1">
          {lapsSummary.map((lap) => {
            const isSelected = lap.lap_number === activeLapNumber
            const isFastest = lap.is_fastest
            const isPit = lap.pit
            const compoundInfo = COMPOUND_COLORS[lap.compound] || COMPOUND_COLORS.MEDIUM

            // Compute normalized pace bar height (higher pace = taller bar)
            let heightPercent = 65
            if (lap.lap_time && paceScale.max > paceScale.min) {
              const clamped = Math.max(paceScale.min, Math.min(paceScale.max, lap.lap_time))
              // Faster lap = taller bar (inverse of time)
              heightPercent = 35 + ((paceScale.max - clamped) / (paceScale.max - paceScale.min)) * 55
            }
            if (isPit) heightPercent = 28 // Pit laps rendered low to indicate in/out

            return (
              <div
                key={lap.lap_number}
                data-lap={lap.lap_number}
                tabIndex={0}
                role="button"
                onClick={() => onSelectLap?.(lap.lap_number)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onSelectLap?.(lap.lap_number)
                  }
                }}
                className={`group relative flex flex-col items-center justify-end cursor-pointer transition-all duration-150 focus:outline-none ${
                  isSelected ? 'scale-105 z-20' : 'hover:scale-105 hover:z-10 opacity-85 hover:opacity-100'
                }`}
                style={{ width: '22px', height: '68px' }}
                title={`Lap ${lap.lap_number}: ${lap.lap_time ? `${lap.lap_time.toFixed(3)}s` : 'Pit In/Out'} · ${lap.compound}${isFastest ? ' · FASTEST LAP' : ''}${isPit ? ' · PIT STOP' : ''}`}
              >
                {/* Fastest Lap Crown Badge */}
                {isFastest && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 text-purple-400 animate-bounce">
                    <Zap size={11} className="fill-purple-400" />
                  </div>
                )}

                {/* Pit Stop Wrench Icon */}
                {isPit && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 text-amber-400">
                    <Wrench size={10} />
                  </div>
                )}

                {/* Vertical Pace Bar */}
                <div
                  className={`w-full rounded-xs transition-all relative ${
                    isSelected
                      ? 'ring-2 ring-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.6)]'
                      : 'border border-zinc-900 group-hover:border-zinc-700'
                  }`}
                  style={{
                    height: `${heightPercent}%`,
                    backgroundColor: isSelected ? '#f59e0b' : (isFastest ? '#a855f7' : compoundInfo.bg),
                    opacity: isSelected ? 1.0 : (isPit ? 0.6 : 0.85)
                  }}
                >
                  {/* Inner compound stripe */}
                  <div
                    className="absolute inset-x-0 bottom-0 h-1.5 rounded-b-xs"
                    style={{ backgroundColor: compoundInfo.border }}
                  />
                </div>

                {/* Lap Number Label Below Bar */}
                <span
                  className={`mt-1 text-[8.5px] font-mono leading-none tracking-tighter ${
                    isSelected ? 'text-amber-400 font-extrabold' : 'text-zinc-500 group-hover:text-zinc-300'
                  }`}
                >
                  {lap.lap_number}
                </span>

                {/* Interactive Hover Tooltip */}
                <div className="absolute bottom-full mb-4 left-1/2 -translate-x-1/2 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-50 bg-[#090d14] border border-zinc-700 rounded-sm p-2 text-xs shadow-2xl min-w-[130px] whitespace-nowrap">
                  <div className="flex items-center justify-between gap-2 border-b border-zinc-800 pb-1 mb-1">
                    <span className="font-bold text-white">Lap #{lap.lap_number}</span>
                    <span
                      className="px-1 py-0.2 rounded-2xs text-[8px] font-bold uppercase"
                      style={{ backgroundColor: compoundInfo.bg, color: '#000000' }}
                    >
                      {lap.compound}
                    </span>
                  </div>
                  <div className="space-y-0.5 text-[10px]">
                    <div className="flex justify-between text-zinc-300">
                      <span>Lap Time:</span>
                      <strong className={isFastest ? 'text-purple-400' : 'text-amber-300'}>
                        {lap.lap_time ? `${lap.lap_time.toFixed(3)}s` : 'Pit In/Out'}
                      </strong>
                    </div>
                    {lap.s1 && (
                      <div className="flex justify-between text-zinc-400 text-[9px]">
                        <span>Sectors:</span>
                        <span>{lap.s1}s / {lap.s2}s / {lap.s3}s</span>
                      </div>
                    )}
                    {isFastest && (
                      <div className="text-purple-400 font-bold text-[9px] flex items-center gap-1 pt-0.5">
                        <Zap size={9} /> FASTEST RACE LAP
                      </div>
                    )}
                    {isPit && (
                      <div className="text-amber-400 font-bold text-[9px] flex items-center gap-1 pt-0.5">
                        <Wrench size={9} /> PIT STOP WINDOW
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* ─── Legend Footer ─── */}
      <div className="flex items-center justify-between text-[10px] text-zinc-400 pt-1 border-t border-zinc-900 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <span className="text-zinc-300 font-semibold uppercase text-[9px]">COMPOUNDS:</span>
          {Object.entries(COMPOUND_COLORS).slice(0, 3).map(([name, c]) => (
            <div key={name} className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: c.bg }} />
              <span className="capitalize">{name.toLowerCase()}</span>
            </div>
          ))}
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-purple-500" />
            <span>Fastest Lap</span>
          </div>
          <div className="flex items-center gap-1 text-amber-400">
            <Wrench size={10} />
            <span>Pit Stop</span>
          </div>
        </div>

        <div className="text-[10px] text-zinc-400">
          Click any lap bar to stream its telemetry
        </div>
      </div>
    </div>
  )
}

