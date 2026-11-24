import React, { useMemo } from 'react'
import { Navigation } from 'lucide-react'
import { MONACO_TRACK_PATH, MONACO_TRACK_POINTS, MONACO_CORNERS } from '../data/telemetryData'
import accurateCircuits from '../data/accurateCircuitMaps.json'

const CIRCUIT_ALIASES = {
  melbourne: 'australia',
  albert_park: 'australia',
  monte_carlo: 'monaco',
  interlagos: 'brazil',
  sao_paulo: 'brazil',
  cota: 'austin',
  usa: 'austin',
  united_states: 'austin',
  montreal: 'canada',
  gilles_villeneuve: 'canada',
  spielberg: 'austria',
  red_bull_ring: 'austria',
  sakhir: 'bahrain',
  jeddah: 'saudi_arabia',
  marina_bay: 'singapore',
  azerbaijan: 'baku',
  shanghai: 'china',
  catalunya: 'spain',
  barcelona: 'spain',
  emilia_romagna: 'imola',
  enzo_e_dino_ferrari: 'imola',
  mexico_city: 'mexico',
  hermanos_rodriguez: 'mexico',
  vegas: 'las_vegas',
  lusail: 'qatar',
  doha: 'qatar',
  yas_island: 'abu_dhabi',
  yas_marina: 'abu_dhabi',
  suzuka: 'japan',
  zandvoort: 'netherlands',
  hungaroring: 'hungary',
  silverstone: 'silverstone',
  great_britain: 'silverstone',
  british: 'silverstone',
  spa: 'spa',
  belgian: 'spa',
  belgium: 'spa',
  monza: 'monza',
  italian: 'monza',
  italy: 'monza',
  miami: 'miami'
}

function resolveCircuit(nameOrEvent) {
  if (!nameOrEvent) return 'monaco'
  const clean = String(nameOrEvent).toLowerCase().replace(/-/g, '_').replace(/\s+/g, '_')
  if (accurateCircuits && accurateCircuits[clean]) return clean
  if (CIRCUIT_ALIASES[clean]) return CIRCUIT_ALIASES[clean]
  for (const [alias, key] of Object.entries(CIRCUIT_ALIASES)) {
    if (clean.includes(alias) && accurateCircuits && accurateCircuits[key]) return key
  }
  if (accurateCircuits) {
    for (const [k, c] of Object.entries(accurateCircuits)) {
      if (c.circuit_name && clean.includes(c.circuit_name.toLowerCase())) return k
      if (c.location && clean.includes(c.location.toLowerCase())) return k
    }
  }
  return 'monaco'
}

export default function TrackMap({
  trackMap,
  hoverTime,
  selectedRange,
  onCornerClick,
  activeCorner,
  driver = '1',
  driverCode = 'VER',
  circuitName = 'Circuit de Monaco',
  eventName = 'Grand Prix',
  lapLength = '3.337 km',
  lapNumber = 1,
  // Dual-Driver Comparison props
  compareTrackMap = null,
  compareDriver = null,
  compareDriverCode = null,
  compareColor = '#00f0ff'
}) {
  // Gracefully fallback to baseline authentic circuit geometry if props are empty or loading
  const activeTrack = useMemo(() => {
    if (trackMap && trackMap.svg_path && trackMap.points?.length > 0) {
      return trackMap
    }
    const resolvedKey = resolveCircuit(circuitName || eventName)
    if (accurateCircuits && accurateCircuits[resolvedKey]) {
      return accurateCircuits[resolvedKey]
    }
    return accurateCircuits?.monaco || {
      viewBox: "0 0 320 380",
      svg_path: MONACO_TRACK_PATH,
      points: MONACO_TRACK_POINTS,
      corner_pins: MONACO_CORNERS,
      circuit_name: circuitName || "Circuit de Monaco",
      location: "Monte Carlo, Monaco",
      lap_len: lapLength || "3.337 km"
    }
  }, [trackMap, circuitName, eventName, lapLength])

  const displayName = activeTrack.circuit_name || circuitName || 'Grand Prix Circuit'
  const displayLen = activeTrack.lap_len || lapLength || '5.2 km'
  const displayDriverBadge = driverCode ? `#${driver} ${driverCode}` : `#${driver}`
  const displayCompareBadge = compareDriverCode ? `#${compareDriver} ${compareDriverCode}` : (compareDriver ? `#${compareDriver}` : null)

  // Find primary car coordinate at the current hover timestamp
  const currentPos = useMemo(() => {
    if (!activeTrack.points || activeTrack.points.length === 0) return null

    let targetTime = 0.0
    if (hoverTime != null) {
      targetTime = hoverTime
    } else if (selectedRange?.start != null) {
      targetTime = selectedRange.start
    }

    let closest = activeTrack.points[0]
    let minDelta = Math.abs(closest.t - targetTime)

    for (let i = 1; i < activeTrack.points.length; i++) {
      const pt = activeTrack.points[i]
      const delta = Math.abs(pt.t - targetTime)
      if (delta < minDelta) {
        minDelta = delta
        closest = pt
      }
    }
    return closest
  }, [activeTrack, hoverTime, selectedRange])

  // Find ghost/comparison car coordinate at the current hover timestamp
  const comparePos = useMemo(() => {
    if (!compareDriver) return null
    const pts = compareTrackMap?.points || activeTrack.points
    if (!pts || pts.length === 0) return null

    let targetTime = 0.0
    if (hoverTime != null) {
      targetTime = hoverTime
    } else if (selectedRange?.start != null) {
      targetTime = selectedRange.start
    }

    let closest = pts[0]
    let minDelta = Math.abs(closest.t - targetTime)

    for (let i = 1; i < pts.length; i++) {
      const pt = pts[i]
      const delta = Math.abs(pt.t - targetTime)
      if (delta < minDelta) {
        minDelta = delta
        closest = pt
      }
    }
    return closest
  }, [compareDriver, compareTrackMap, activeTrack, hoverTime, selectedRange])

  // Build SVG segment for active anomaly boundary
  const activeSegmentPath = useMemo(() => {
    if (!selectedRange || !activeTrack.points) return null

    const segmentPoints = activeTrack.points.filter(
      pt => pt.t >= selectedRange.start && pt.t <= selectedRange.end
    )

    if (segmentPoints.length < 2) return null

    return segmentPoints.reduce((path, pt, idx) => {
      return idx === 0 ? `M ${pt.x} ${pt.y}` : `${path} L ${pt.x} ${pt.y}`
    }, '')
  }, [selectedRange, activeTrack])

  // Start / finish point
  const startFinish = useMemo(() => {
    if (activeTrack.start_finish) return activeTrack.start_finish
    if (activeTrack.points && activeTrack.points.length > 0) return activeTrack.points[0]
    return null
  }, [activeTrack])

  return (
    <div
      className="command-card p-4 space-y-3"
      role="region"
      aria-label={`${displayName} Track Map`}
    >
      {/* Track Header */}
      <div className="flex items-center justify-between pb-2 border-b" style={{ borderColor: 'var(--border-dim)' }}>
        <div className="flex items-center gap-2 min-w-0">
          <Navigation size={13} style={{ color: 'var(--accent)' }} aria-hidden="true" className="flex-shrink-0" />
          <span className="mono-label font-semibold text-zinc-100 truncate" title={displayName}>
            {displayName}
          </span>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span className="live-beacon" aria-hidden="true" />
          <span className="font-mono text-[10px] uppercase tracking-widest text-emerald-400 font-semibold">
            GPS Live (100Hz)
          </span>
        </div>
      </div>

      {/* SVG Circuit Canvas */}
      <div className="relative flex items-center justify-center p-2 rounded-sm bg-[#040507] border border-zinc-900 overflow-hidden">
        <svg
          viewBox={activeTrack.viewBox || '0 0 320 380'}
          className="w-full h-auto max-h-72 select-none overflow-visible"
        >
          <defs>
            <filter id="glow-amber" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3.5" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <filter id="glow-car" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <linearGradient id="trackGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.8" />
              <stop offset="50%" stopColor="#818cf8" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.8" />
            </linearGradient>
          </defs>

          {/* Circuit Roadbed Outer Foundation */}
          <path
            d={activeTrack.svg_path}
            fill="none"
            stroke="#111622"
            strokeWidth="13"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Circuit Road Surface */}
          <path
            d={activeTrack.svg_path}
            fill="none"
            stroke="#1c2434"
            strokeWidth="8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Circuit Racing Line */}
          <path
            d={activeTrack.svg_path}
            fill="none"
            stroke="#3b82f6"
            strokeWidth="2.2"
            strokeDasharray="4 2"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity="0.85"
          />

          {/* Start / Finish Line Indicator */}
          {startFinish && (
            <g transform={`translate(${startFinish.x}, ${startFinish.y})`}>
              <circle r="7" fill="#000000" stroke="#f59e0b" strokeWidth="1.5" />
              <circle r="3" fill="#ffffff" />
              <text
                x="9"
                y="3"
                fill="#f59e0b"
                fontSize="8"
                fontFamily="'JetBrains Mono', monospace"
                fontWeight="bold"
              >
                S/F
              </text>
            </g>
          )}

          {/* Active Anomaly Highlighted Segment */}
          {activeSegmentPath && (
            <path
              d={activeSegmentPath}
              fill="none"
              stroke="var(--accent)"
              strokeWidth="6"
              strokeLinecap="round"
              filter="url(#glow-amber)"
              className="animate-pulse"
            />
          )}

          {/* Corner Anchor Pins */}
          {activeTrack.corner_pins?.map((pin, idx) => {
            const isCornerActive = activeCorner === pin.name
            const pinLabel = pin.id && pin.id !== 'Turn'
              ? pin.id
              : (pin.name ? `T${pin.name.replace(/^Turn\s*/i, '').split(' ')[0]}` : `T${idx + 1}`)
            return (
              <g
                key={idx}
                tabIndex={0}
                role="button"
                className="cursor-pointer transition-transform hover:scale-125 focus:outline-none"
                onClick={() => onCornerClick?.(pin)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onCornerClick?.(pin)
                  }
                }}
              >
                <title>{`${pin.name} · ${pin.type || 'Corner'} (${pin.speed ? `${pin.speed} km/h` : 'Apex'})`}</title>
                {/* 28px tap target */}
                <circle cx={pin.x} cy={pin.y} r="14" fill="transparent" />
                <circle
                  cx={pin.x}
                  cy={pin.y}
                  r={isCornerActive ? "7" : "4.5"}
                  fill={isCornerActive ? "var(--accent)" : "#090d14"}
                  stroke={isCornerActive ? "#ffffff" : "#64748b"}
                  strokeWidth="1.5"
                />
                <text
                  x={pin.x + 7}
                  y={pin.y + 3}
                  fill={isCornerActive ? "var(--accent)" : "#cbd5e1"}
                  fontSize="8.5"
                  fontFamily="'JetBrains Mono', monospace"
                  fontWeight="bold"
                >
                  {pinLabel}
                </text>
              </g>
            )
          })}

          {/* Live Car Position Dot with continuous idle motion pulse */}
          {currentPos && (
            <g transform={`translate(${currentPos.x}, ${currentPos.y})`}>
              <circle
                r="11"
                fill="none"
                stroke="var(--accent)"
                strokeWidth="1.5"
                opacity="0.8"
                filter="url(#glow-car)"
                className="animate-ping"
              />
              <circle
                r="5"
                fill="#ffffff"
                stroke="#000000"
                strokeWidth="1.5"
              />
              <g transform="translate(11, -9)">
                <rect
                  x="0"
                  y="0"
                  width="74"
                  height="18"
                  rx="3"
                  fill="#0a0d13"
                  stroke="var(--border-mid)"
                  strokeWidth="1"
                />
                <text
                  x="5"
                  y="12"
                  fill="var(--accent)"
                  fontSize="9"
                  fontFamily="'JetBrains Mono', monospace"
                  fontWeight="bold"
                >
                  {displayDriverBadge} · {currentPos.spd}k
                </text>
              </g>
            </g>
          )}

          {/* Ghost / Comparison Car Position Marker */}
          {comparePos && (
            <g transform={`translate(${comparePos.x}, ${comparePos.y})`}>
              <circle
                r="10"
                fill="none"
                stroke={compareColor || "#00f0ff"}
                strokeWidth="1.5"
                opacity="0.8"
                strokeDasharray="3 2"
              />
              <circle
                r="4.5"
                fill={compareColor || "#00f0ff"}
                stroke="#000000"
                strokeWidth="1.2"
              />
              <g transform="translate(11, -9)">
                <rect
                  x="0"
                  y="0"
                  width="74"
                  height="18"
                  rx="3"
                  fill="#06090e"
                  stroke={compareColor || "#00f0ff"}
                  strokeWidth="1"
                  opacity="0.95"
                />
                <text
                  x="5"
                  y="12"
                  fill={compareColor || "#00f0ff"}
                  fontSize="8.5"
                  fontFamily="'JetBrains Mono', monospace"
                  fontWeight="bold"
                >
                  {displayCompareBadge} · {comparePos.spd || 220}k
                </text>
              </g>
            </g>
          )}
        </svg>
      </div>

      {/* Position Telemetry Footer */}
      <div className="pt-2 border-t flex items-center justify-between font-mono text-[10px] text-zinc-300" style={{ borderColor: 'var(--border-dim)' }}>
        <div className="truncate max-w-[210px]">
          <span className="text-zinc-500">TRACK: </span>
          <span className="text-white font-semibold">{displayName.toUpperCase()}</span>
          <span className="text-zinc-400"> ({displayLen})</span>
          {lapNumber != null && (
            <span className="text-amber-400 font-bold ml-1">L{lapNumber}</span>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span className="w-2 h-2 rounded-full bg-emerald-400" />
          <span className="text-emerald-400 font-semibold">SECTOR GREEN</span>
        </div>
      </div>
    </div>
  )
}
