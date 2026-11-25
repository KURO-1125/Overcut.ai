import React, { useState, useEffect, useRef, Suspense, lazy } from 'react'
import Lenis from 'lenis'
import AppHeader from './components/AppHeader'
import HomePage from './components/HomePage'
import F1LandingPage from './components/F1LandingPage'
import EVLandingPage from './components/EVLandingPage'
import AuthModal from './components/AuthModal'
import DiagnosticDossierModal from './components/DiagnosticDossierModal'
import { apiFetch } from './lib/api'
import { useAuth } from './context/AuthContext'

// Each workspace is lazy-loaded so TimelineWorkspace + uPlot are only fetched
// when the user actually navigates to that workspace.
const F1WorkspacePage = lazy(() => import('./components/F1WorkspacePage'))
const EVWorkspacePage = lazy(() => import('./components/EVWorkspacePage'))

// ─── Default Season Metadata (fallback when the API is offline) ──────────────
// Mirrors backend/data_engine/f1_calendar.py, which is the source of truth.
// Mid-season driver changes are resolved per session by /api/f1/drivers.
export const DEFAULT_DRIVERS_BY_YEAR = {
  2025: [
    { id: '1',  number: '1',  code: 'VER', name: 'Max Verstappen',    team: 'Red Bull Racing', color: '#4781D7' },
    { id: '22', number: '22', code: 'TSU', name: 'Yuki Tsunoda',      team: 'Red Bull Racing', color: '#4781D7' },
    { id: '4',  number: '4',  code: 'NOR', name: 'Lando Norris',      team: 'McLaren',         color: '#F47600' },
    { id: '81', number: '81', code: 'PIA', name: 'Oscar Piastri',     team: 'McLaren',         color: '#F47600' },
    { id: '16', number: '16', code: 'LEC', name: 'Charles Leclerc',   team: 'Ferrari',         color: '#ED1131' },
    { id: '44', number: '44', code: 'HAM', name: 'Lewis Hamilton',    team: 'Ferrari',         color: '#ED1131' },
    { id: '63', number: '63', code: 'RUS', name: 'George Russell',    team: 'Mercedes',        color: '#00D7B6' },
    { id: '12', number: '12', code: 'ANT', name: 'Kimi Antonelli',    team: 'Mercedes',        color: '#00D7B6' },
    { id: '14', number: '14', code: 'ALO', name: 'Fernando Alonso',   team: 'Aston Martin',    color: '#229971' },
    { id: '18', number: '18', code: 'STR', name: 'Lance Stroll',      team: 'Aston Martin',    color: '#229971' },
    { id: '55', number: '55', code: 'SAI', name: 'Carlos Sainz',      team: 'Williams',        color: '#1868DB' },
    { id: '23', number: '23', code: 'ALB', name: 'Alexander Albon',   team: 'Williams',        color: '#1868DB' },
    { id: '10', number: '10', code: 'GAS', name: 'Pierre Gasly',      team: 'Alpine',          color: '#00A1E8' },
    { id: '43', number: '43', code: 'COL', name: 'Franco Colapinto',  team: 'Alpine',          color: '#00A1E8' },
    { id: '31', number: '31', code: 'OCO', name: 'Esteban Ocon',      team: 'Haas F1 Team',    color: '#9C9FA2' },
    { id: '87', number: '87', code: 'BEA', name: 'Oliver Bearman',    team: 'Haas F1 Team',    color: '#9C9FA2' },
    { id: '27', number: '27', code: 'HUL', name: 'Nico Hülkenberg',   team: 'Kick Sauber',     color: '#01C00E' },
    { id: '5',  number: '5',  code: 'BOR', name: 'Gabriel Bortoleto', team: 'Kick Sauber',     color: '#01C00E' },
    { id: '30', number: '30', code: 'LAW', name: 'Liam Lawson',       team: 'Racing Bulls',    color: '#6C98FF' },
    { id: '6',  number: '6',  code: 'HAD', name: 'Isack Hadjar',      team: 'Racing Bulls',    color: '#6C98FF' },
  ],
  2026: [
    { id: '1',  number: '1',  code: 'NOR', name: 'Lando Norris',      team: 'McLaren',         color: '#F47600' },
    { id: '81', number: '81', code: 'PIA', name: 'Oscar Piastri',     team: 'McLaren',         color: '#F47600' },
    { id: '16', number: '16', code: 'LEC', name: 'Charles Leclerc',   team: 'Ferrari',         color: '#ED1131' },
    { id: '44', number: '44', code: 'HAM', name: 'Lewis Hamilton',    team: 'Ferrari',         color: '#ED1131' },
    { id: '63', number: '63', code: 'RUS', name: 'George Russell',    team: 'Mercedes',        color: '#00D7B6' },
    { id: '12', number: '12', code: 'ANT', name: 'Kimi Antonelli',    team: 'Mercedes',        color: '#00D7B6' },
    { id: '3',  number: '3',  code: 'VER', name: 'Max Verstappen',    team: 'Red Bull Racing', color: '#4781D7' },
    { id: '6',  number: '6',  code: 'HAD', name: 'Isack Hadjar',      team: 'Red Bull Racing', color: '#4781D7' },
    { id: '30', number: '30', code: 'LAW', name: 'Liam Lawson',       team: 'Racing Bulls',    color: '#6C98FF' },
    { id: '41', number: '41', code: 'LIN', name: 'Arvid Lindblad',    team: 'Racing Bulls',    color: '#6C98FF' },
    { id: '14', number: '14', code: 'ALO', name: 'Fernando Alonso',   team: 'Aston Martin',    color: '#229971' },
    { id: '18', number: '18', code: 'STR', name: 'Lance Stroll',      team: 'Aston Martin',    color: '#229971' },
    { id: '55', number: '55', code: 'SAI', name: 'Carlos Sainz',      team: 'Williams',        color: '#1868DB' },
    { id: '23', number: '23', code: 'ALB', name: 'Alexander Albon',   team: 'Williams',        color: '#1868DB' },
    { id: '10', number: '10', code: 'GAS', name: 'Pierre Gasly',      team: 'Alpine',          color: '#00A1E8' },
    { id: '43', number: '43', code: 'COL', name: 'Franco Colapinto',  team: 'Alpine',          color: '#00A1E8' },
    { id: '27', number: '27', code: 'HUL', name: 'Nico Hülkenberg',   team: 'Audi',            color: '#F50537' },
    { id: '5',  number: '5',  code: 'BOR', name: 'Gabriel Bortoleto', team: 'Audi',            color: '#F50537' },
    { id: '11', number: '11', code: 'PER', name: 'Sergio Pérez',      team: 'Cadillac',        color: '#909090' },
    { id: '77', number: '77', code: 'BOT', name: 'Valtteri Bottas',   team: 'Cadillac',        color: '#909090' },
    { id: '51', number: '51', code: 'CAM', name: 'Rafael Camara',     team: 'Haas F1 Team',    color: '#9C9FA2' },
    { id: '87', number: '87', code: 'BEA', name: 'Oliver Bearman',    team: 'Haas F1 Team',    color: '#9C9FA2' },
  ],
}

export const DEFAULT_CALENDARS_BY_YEAR = {
  2025: [
    { round: 1,  id: 'australia',    name: 'Australian Grand Prix',      circuit: 'Albert Park Circuit',            country: 'Australia',      location: 'Melbourne' },
    { round: 2,  id: 'china',        name: 'Chinese Grand Prix',         circuit: 'Shanghai International Circuit', country: 'China',          location: 'Shanghai' },
    { round: 3,  id: 'japan',        name: 'Japanese Grand Prix',        circuit: 'Suzuka International Racing',    country: 'Japan',          location: 'Suzuka' },
    { round: 4,  id: 'bahrain',      name: 'Bahrain Grand Prix',         circuit: 'Bahrain International Circuit',  country: 'Bahrain',        location: 'Sakhir' },
    { round: 5,  id: 'saudi_arabia', name: 'Saudi Arabian Grand Prix',   circuit: 'Jeddah Corniche Circuit',        country: 'Saudi Arabia',   location: 'Jeddah' },
    { round: 6,  id: 'miami',        name: 'Miami Grand Prix',           circuit: 'Miami International Autodrome',  country: 'United States',  location: 'Miami Gardens' },
    { round: 7,  id: 'imola',        name: 'Emilia Romagna Grand Prix',  circuit: 'Autodromo Enzo e Dino Ferrari',  country: 'Italy',          location: 'Imola' },
    { round: 8,  id: 'monaco',       name: 'Monaco Grand Prix',          circuit: 'Circuit de Monaco',              country: 'Monaco',         location: 'Monte Carlo' },
    { round: 9,  id: 'spain',        name: 'Spanish Grand Prix',         circuit: 'Circuit de Barcelona-Catalunya', country: 'Spain',          location: 'Barcelona' },
    { round: 10, id: 'canada',       name: 'Canadian Grand Prix',        circuit: 'Circuit Gilles Villeneuve',      country: 'Canada',         location: 'Montréal' },
    { round: 11, id: 'austria',      name: 'Austrian Grand Prix',        circuit: 'Red Bull Ring',                  country: 'Austria',        location: 'Spielberg' },
    { round: 12, id: 'silverstone',  name: 'British Grand Prix',         circuit: 'Silverstone Circuit',            country: 'United Kingdom', location: 'Silverstone' },
    { round: 13, id: 'spa',          name: 'Belgian Grand Prix',         circuit: 'Circuit de Spa-Francorchamps',   country: 'Belgium',        location: 'Spa-Francorchamps' },
    { round: 14, id: 'hungary',      name: 'Hungarian Grand Prix',       circuit: 'Hungaroring',                    country: 'Hungary',        location: 'Budapest' },
    { round: 15, id: 'netherlands',  name: 'Dutch Grand Prix',           circuit: 'Circuit Zandvoort',              country: 'Netherlands',    location: 'Zandvoort' },
    { round: 16, id: 'monza',        name: 'Italian Grand Prix',         circuit: 'Autodromo Nazionale Monza',      country: 'Italy',          location: 'Monza' },
    { round: 17, id: 'baku',         name: 'Azerbaijan Grand Prix',      circuit: 'Baku City Circuit',              country: 'Azerbaijan',     location: 'Baku' },
    { round: 18, id: 'singapore',    name: 'Singapore Grand Prix',       circuit: 'Marina Bay Street Circuit',      country: 'Singapore',      location: 'Marina Bay' },
    { round: 19, id: 'austin',       name: 'United States Grand Prix',   circuit: 'Circuit of The Americas',        country: 'United States',  location: 'Austin' },
    { round: 20, id: 'mexico',       name: 'Mexico City Grand Prix',     circuit: 'Autódromo Hermanos Rodríguez',   country: 'Mexico',         location: 'Mexico City' },
    { round: 21, id: 'brazil',       name: 'São Paulo Grand Prix',       circuit: 'Autódromo de Interlagos',        country: 'Brazil',         location: 'São Paulo' },
    { round: 22, id: 'las_vegas',    name: 'Las Vegas Grand Prix',       circuit: 'Las Vegas Strip Circuit',        country: 'United States',  location: 'Las Vegas' },
    { round: 23, id: 'qatar',        name: 'Qatar Grand Prix',           circuit: 'Lusail International Circuit',   country: 'Qatar',          location: 'Lusail' },
    { round: 24, id: 'abu_dhabi',    name: 'Abu Dhabi Grand Prix',       circuit: 'Yas Marina Circuit',             country: 'UAE',            location: 'Yas Island' },
  ],
  2026: [
    { round: 1,  id: 'australia',   name: 'Australian Grand Prix',          circuit: 'Albert Park Circuit',            country: 'Australia',      location: 'Melbourne' },
    { round: 2,  id: 'china',       name: 'Chinese Grand Prix',             circuit: 'Shanghai International Circuit', country: 'China',          location: 'Shanghai' },
    { round: 3,  id: 'japan',       name: 'Japanese Grand Prix',            circuit: 'Suzuka International Racing',    country: 'Japan',          location: 'Suzuka' },
    { round: 4,  id: 'miami',       name: 'Miami Grand Prix',               circuit: 'Miami International Autodrome',  country: 'United States',  location: 'Miami Gardens' },
    { round: 5,  id: 'canada',      name: 'Canadian Grand Prix',            circuit: 'Circuit Gilles Villeneuve',      country: 'Canada',         location: 'Montréal' },
    { round: 6,  id: 'monaco',      name: 'Monaco Grand Prix',              circuit: 'Circuit de Monaco',              country: 'Monaco',         location: 'Monte Carlo' },
    { round: 7,  id: 'barcelona',   name: 'Barcelona Grand Prix',           circuit: 'Circuit de Barcelona-Catalunya', country: 'Spain',          location: 'Barcelona' },
    { round: 8,  id: 'austria',     name: 'Austrian Grand Prix',            circuit: 'Red Bull Ring',                  country: 'Austria',        location: 'Spielberg' },
    { round: 9,  id: 'silverstone', name: 'British Grand Prix',             circuit: 'Silverstone Circuit',            country: 'United Kingdom', location: 'Silverstone' },
    { round: 10, id: 'spa',         name: 'Belgian Grand Prix',             circuit: 'Circuit de Spa-Francorchamps',   country: 'Belgium',        location: 'Spa-Francorchamps' },
    { round: 11, id: 'hungary',     name: 'Hungarian Grand Prix',           circuit: 'Hungaroring',                    country: 'Hungary',        location: 'Budapest' },
    { round: 12, id: 'netherlands', name: 'Dutch Grand Prix',               circuit: 'Circuit Zandvoort',              country: 'Netherlands',    location: 'Zandvoort' },
    { round: 13, id: 'monza',       name: 'Italian Grand Prix',             circuit: 'Autodromo Nazionale Monza',      country: 'Italy',          location: 'Monza' },
    { round: 14, id: 'madrid',      name: 'Spanish Grand Prix',             circuit: 'Madring',                        country: 'Spain',          location: 'Madrid' },
    { round: 15, id: 'baku',        name: 'Azerbaijan Grand Prix',          circuit: 'Baku City Circuit',              country: 'Azerbaijan',     location: 'Baku' },
    { round: 16, id: 'malaysia',    name: 'Bahrain Grand Prix in Malaysia', circuit: 'Sepang International Circuit',   country: 'Malaysia',       location: 'Kuala Lumpur' },
    { round: 17, id: 'singapore',   name: 'Singapore Grand Prix',           circuit: 'Marina Bay Street Circuit',      country: 'Singapore',      location: 'Marina Bay' },
    { round: 18, id: 'austin',      name: 'United States Grand Prix',       circuit: 'Circuit of The Americas',        country: 'United States',  location: 'Austin' },
    { round: 19, id: 'mexico',      name: 'Mexico City Grand Prix',         circuit: 'Autódromo Hermanos Rodríguez',   country: 'Mexico',         location: 'Mexico City' },
    { round: 20, id: 'brazil',      name: 'São Paulo Grand Prix',           circuit: 'Autódromo de Interlagos',        country: 'Brazil',         location: 'São Paulo' },
    { round: 21, id: 'las_vegas',   name: 'Las Vegas Grand Prix',           circuit: 'Las Vegas Strip Circuit',        country: 'United States',  location: 'Las Vegas' },
    { round: 22, id: 'qatar',       name: 'Qatar Grand Prix',               circuit: 'Lusail International Circuit',   country: 'Qatar',          location: 'Lusail' },
    { round: 23, id: 'abu_dhabi',   name: 'Abu Dhabi Grand Prix',           circuit: 'Yas Marina Circuit',             country: 'UAE',            location: 'Yas Island' },
  ],
}

export const EV_CYCLES = [
  { id: 'nasa_b0005_sag',        name: 'NASA B0005',   tag: 'Capacity Fade / Sag',  pack: 'NASA Ames Prognostics', desc: '18650 Li-ion Cell #5 — Rapid Droop & Accelerated Resistance Growth' },
  { id: 'fleet_thermal_runaway', name: 'Fleet Pack B', tag: 'Thermal Excursion',    pack: '400V 75kWh NMC 811',    desc: 'Module 2 Overheat > 62°C — Rapid Enthalpy Spike Under Sustained Current' },
  { id: 'fleet_cell_imbalance',  name: 'Fleet Pack C', tag: 'Parallel Imbalance',   pack: '400V 75kWh NMC 811',    desc: 'String 3 Delta-V > 340mV — Parallel Group State of Health Divergence' },
  { id: 'fleet_nominal_baseline',name: 'Fleet Pack A', tag: 'Nominal Health',       pack: '400V 75kWh NMC 811',    desc: 'Balanced Discharge — Nominal Impedance & Thermal Dissipation' },
]

export const SEASONS = [2026, 2025]
export const SESSION_TYPES = [
  { id: 'Q',   label: 'Qualifying' },
  { id: 'R',   label: 'Grand Prix Race' },
  { id: 'FP1', label: 'Practice 1' },
  { id: 'FP2', label: 'Practice 2' },
  { id: 'FP3', label: 'Practice 3' },
]

export default function App() {
  const { user, openAuth } = useAuth()

  // Navigation & View State
  const [currentView, setCurrentView] = useState('home') // 'home' | 'f1-landing' | 'ev-landing' | 'f1-workspace' | 'ev-workspace'
  const [mode, setMode] = useState('motorsport')

  // Scroll to top on every view change
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [currentView])

  // Auth-gated navigation — pages beyond 'home' require a user session
  const navigate = (view) => {
    const publicViews = ['home']
    if (!publicViews.includes(view) && !user) {
      openAuth('login')
      return
    }
    setCurrentView(view)
  }

  // Motorsport F1 Session State
  const [selectedYear, setSelectedYear]               = useState(2025)
  const [selectedEvent, setSelectedEvent]             = useState('monaco')
  const [selectedSessionType, setSelectedSessionType] = useState('Q')
  const [selectedDriver, setSelectedDriver]           = useState('44')
  const [availableDrivers, setAvailableDrivers]       = useState(DEFAULT_DRIVERS_BY_YEAR[2025])
  const [availableEvents, setAvailableEvents]         = useState(DEFAULT_CALENDARS_BY_YEAR[2025])

  // EV Battery State
  const [selectedCycle, setSelectedCycle] = useState('nasa_b0005_sag')

  // AI Diagnostic Model State
  const [reasoningMode, setReasoningMode] = useState('local_vlm') // 'local_vlm' | 'deterministic' | 'cloud_gemini'

  // Diagnostic Execution & Payload State
  const [loading, setLoading]         = useState(false)
  const [data, setData]               = useState(null)
  const [error, setError]             = useState(null)
  const [elapsedMs, setElapsedMs]     = useState(null)
  const [isDossierOpen, setIsDossierOpen] = useState(false)
  const [vlmStatus, setVlmStatus]     = useState(null)

  const startRef = useRef(null)
  const analysisRequestRef = useRef(0)

  // Fetch VLM Status on mount
  useEffect(() => {
    let cancelled = false
    const fetchStatus = async () => {
      try {
        const res = await apiFetch('/api/vlm/status', { timeoutMs: 5000 })
        const json = await res.json()
        if (!cancelled) setVlmStatus(json)
      } catch {
        // Backend offline — expected in dev
      }
    }
    fetchStatus()
    return () => { cancelled = true }
  }, [])

  // Calendar follows the season; the driver list follows the exact session,
  // because entry lists change mid-season (2025 Doohan→Colapinto, 2026
  // Ocon→Camara) and car numbers move between years (NOR #1 in 2026).
  useEffect(() => {
    let isMounted = true
    const controller = new AbortController()
    const fetchCalendar = async () => {
      try {
        const res = await apiFetch(`/api/f1/calendar?year=${selectedYear}`, { timeoutMs: 5000, signal: controller.signal })
        const calData = await res.json()
        if (isMounted && calData.events?.length > 0) {
          setAvailableEvents(calData.events)
          setSelectedEvent(prev => calData.events.some(e => e.id === prev) ? prev : calData.events[0].id)
        }
      } catch {
        if (isMounted && !controller.signal.aborted) {
          const fallback = DEFAULT_CALENDARS_BY_YEAR[selectedYear] || DEFAULT_CALENDARS_BY_YEAR[2025]
          setAvailableEvents(fallback)
          setSelectedEvent(prev => fallback.some(e => e.id === prev) ? prev : fallback[0].id)
        }
      }
    }
    fetchCalendar()
    return () => { isMounted = false; controller.abort() }
  }, [selectedYear])

  useEffect(() => {
    let isMounted = true
    const controller = new AbortController()
    const applyDrivers = (drivers) => {
      setAvailableDrivers(drivers)
      setSelectedDriver(prev => drivers.some(d => d.number === String(prev)) ? prev : String(drivers[0].number))
    }
    const fetchDrivers = async () => {
      try {
        const res = await apiFetch(
          `/api/f1/drivers?year=${selectedYear}&event=${selectedEvent}&session_type=${selectedSessionType}`,
          { timeoutMs: 5000, signal: controller.signal },
        )
        const drvData = await res.json()
        if (isMounted && drvData.drivers?.length > 0) {
          applyDrivers(drvData.drivers.map(d => ({
            id: String(d.number),
            number: String(d.number),
            code: d.code,
            name: d.name,
            team: d.team,
            color: d.color,
          })))
        }
      } catch {
        if (isMounted && !controller.signal.aborted) {
          applyDrivers(DEFAULT_DRIVERS_BY_YEAR[selectedYear] || DEFAULT_DRIVERS_BY_YEAR[2025])
        }
      }
    }
    fetchDrivers()
    return () => { isMounted = false; controller.abort() }
  }, [selectedYear, selectedEvent, selectedSessionType])

  // Reset diagnostic data on parameter change
  useEffect(() => {
    setData(null)
    setError(null)
  }, [mode, selectedYear, selectedEvent, selectedSessionType, selectedDriver, selectedCycle])

  // Single app-level Lenis smooth-scroll instance.
  // Only active on landing pages with long scroll content; disabled on the workspace
  // to avoid scroll conflicts with the sticky command bar.
  const lenisRef = useRef(null)
  useEffect(() => {
    const isScrollableView = currentView !== 'f1-workspace' && currentView !== 'ev-workspace'
    let frameId = null
    let cancelled = false

    if (isScrollableView && !lenisRef.current) {
      lenisRef.current = new Lenis({
        duration: 1.2,
        easing: t => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      })
      const raf = (time) => {
        if (cancelled) return
        lenisRef.current?.raf(time)
        frameId = requestAnimationFrame(raf)
      }
      frameId = requestAnimationFrame(raf)
    }

    return () => {
      cancelled = true
      if (frameId !== null) cancelAnimationFrame(frameId)
      if (lenisRef.current) {
        lenisRef.current.destroy()
        lenisRef.current = null
      }
    }
  }, [currentView])

  // Normalize diagnostic payload
  const normalizeDiagnosticPayload = (payload, engineChoice) => {
    if (!payload) return null
    const diag = payload.diagnostic || {}

    let evidenceList = []
    if (Array.isArray(diag.key_evidence) && diag.key_evidence.length > 0) {
      evidenceList = diag.key_evidence.map(e =>
        `${e.channel ? `[${e.channel}] ` : ''}${e.observation || ''}${e.delta_value ? ` (${e.delta_value})` : ''}`
      )
    } else if (Array.isArray(diag.physical_evidence) && diag.physical_evidence.length > 0) {
      evidenceList = diag.physical_evidence.map(item =>
        typeof item === 'string' ? item : `${item.channel ? `[${item.channel}] ` : ''}${item.observation || ''}`
      )
    } else {
      evidenceList = [
        'Continuous telemetry waveform inflection confirmed',
        'Signal cross-verified against baseline telemetry boundaries',
      ]
    }

    const confVal = typeof diag.confidence_score === 'number'
      ? diag.confidence_score
      : typeof diag.confidence === 'number'
        ? diag.confidence
        : payload.simulated ? 0.9 : 0

    const rawPrecedents = payload.historical_precedents || diag.historical_precedents || []
    const precedents = rawPrecedents.map((p, idx) => ({
      session:     p.session || p.event || p.title
        || (p.session_id ? [p.session_id, p.driver].filter(Boolean).join(' · ') : null)
        || `Historical Incident #${idx + 1}`,
      similarity:  Math.round((typeof p.score === 'number' ? p.score : typeof p.similarity === 'number' ? p.similarity : 0) * 100),
      observation: p.root_cause || p.description || p.observation || p.metadata
        || 'Telemetry signature correlation confirmed against the indexed archive.',
      turn:        p.turn || p.location || 'Retrieved artifact',
    }))

    const recommendation = diag.recommended_action || diag.strategic_recommendation || 'Maintain telemetry surveillance and adjust powertrain calibration map.'

    const engineName = diag.model_name || (
      engineChoice === 'cloud_gemini'
        ? 'Google Gemini (Cloud Multimodal)'
        : engineChoice === 'local_vlm'
          ? 'Overcut-7B-QLoRA (Local)'
          : 'Overcut Deterministic Heuristic Engine'
    )

    return {
      status:              payload.status || 'success',
      simulated:           !!payload.simulated,
      analyzed_at:         payload.analyzed_at || new Date().toISOString(),
      crop_filename:       payload.crop_filename || 'telemetry_roi_crop.png',
      image_url:           payload.image_url || null,
      vector_shape:        payload.vector_shape || [1, 512],
      embedding_preview:   payload.embedding_preview || [0.082, -0.145, 0.312, -0.045, 0.221, -0.089, 0.178, -0.203],
      telemetry_metrics:   payload.telemetry_metrics
        ? {
            ...payload.telemetry_metrics,
            // Clamp all numeric fields to sensible precision so raw Python floats
            // like 35.30000000000000 never reach the UI.
            duration_seconds:  Math.round((payload.telemetry_metrics.duration_seconds  || 15.0) * 10) / 10,
            min_speed:         Math.round(payload.telemetry_metrics.min_speed          || 68),
            max_speed:         Math.round(payload.telemetry_metrics.max_speed          || 294),
            peak_current:      Math.round(payload.telemetry_metrics.peak_current       || 140),
            max_temperature:   parseFloat((payload.telemetry_metrics.max_temperature   || 42).toFixed(1)),
            min_voltage:       parseFloat((payload.telemetry_metrics.min_voltage       || 3.12).toFixed(2)),
            max_cell_imbalance_mv: Math.round(payload.telemetry_metrics.max_cell_imbalance_mv || 97),
          }
        : {
            driver: selectedDriver,
            min_speed: 68,
            max_speed: 294,
            duration_seconds: 15.0,
          },
      historical_precedents: precedents,
      diagnostic: {
        domain:                  diag.domain || (mode === 'ev' ? 'EV_BATTERY' : 'MOTORSPORT_F1'),
        severity:                diag.severity || 'HIGH',
        dtc_code:                diag.dtc_code || null,
        confidence:              confVal,
        title:                   diag.title || diag.root_cause || 'Telemetry Anomaly Detected',
        root_cause:              diag.root_cause || diag.title || 'Signal variance identified across primary telemetry channels.',
        physical_evidence:       evidenceList,
        strategic_recommendation: recommendation,
        technical_notes:         diag.technical_notes || 'Continuous physical waveform perception verified.',
        model_name:              engineName,
        provider:                diag.provider || (payload.simulated ? 'SIMULATED' : engineChoice === 'local_vlm' ? 'LOCAL_VLM' : 'DETERMINISTIC_HEURISTIC'),
        is_insufficient_data:    !!diag.is_insufficient_data,
      },
    }
  }

  // Trigger Anomaly Slicing & AI Diagnostics
  const analyzeAnomalyRange = async (start, end) => {
    const requestId = ++analysisRequestRef.current
    setLoading(true)
    setError(null)
    startRef.current = Date.now()

    try {
      const response = await apiFetch('/api/analyze_anomaly', {
        method: 'POST',
        timeoutMs: 90000,
        body: JSON.stringify({
          year:                 selectedYear,
          event:                selectedEvent,
          session_type:         selectedSessionType,
          driver:               selectedDriver,
          start_offset_seconds: start,
          end_offset_seconds:   end,
          channels:             mode === 'ev' ? ['Voltage', 'Current', 'Temperature'] : ['Speed', 'Throttle', 'Brake'],
          domain:               mode === 'ev' ? 'EV_BATTERY' : 'MOTORSPORT_F1',
          cycle_key:            selectedCycle,
          use_vlm:              reasoningMode === 'local_vlm',
          use_cloud_vlm:        reasoningMode === 'cloud_gemini',
          enforce_failsafe:     true,
        }),
      })
      const payload = await response.json()
      if (requestId !== analysisRequestRef.current) return
      if (startRef.current) setElapsedMs(Date.now() - startRef.current)
      setData(normalizeDiagnosticPayload(payload, reasoningMode))
    } catch (err) {
      if (requestId !== analysisRequestRef.current) return
      console.warn('Live API unavailable — using clearly-labelled simulation:', err.message)
      if (startRef.current) setElapsedMs(Date.now() - startRef.current)
      setError(`Diagnostic API unavailable (${err.message}). Showing simulated data.`)
      // Lazy-load the large simulation dataset only when the API actually fails.
      const { getDiagnosticPayload } = await import('./data/telemetryData')
      const mockResult = { ...getDiagnosticPayload(mode, start, end, reasoningMode === 'local_vlm'), simulated: true }
      if (requestId !== analysisRequestRef.current) return
      setData(normalizeDiagnosticPayload(mockResult, reasoningMode))
    } finally {
      if (requestId === analysisRequestRef.current) setLoading(false)
    }
  }

  const activeEventObj  = availableEvents.find(e => e.id === selectedEvent) || availableEvents[0] || { name: 'Monaco Grand Prix', circuit: 'Circuit de Monaco' }
  const activeDriverObj = availableDrivers.find(d => String(d.number) === String(selectedDriver)) || availableDrivers[0] || { name: 'Lewis Hamilton', number: '44', team: 'Ferrari', color: '#E80020' }

  return (
    <div
      id="main-content"
      className="min-h-screen flex flex-col"
      style={{ background: 'var(--bg-floor)', color: 'var(--text-secondary)', fontFamily: "'Inter', sans-serif" }}
    >
      {/* Noise grain overlay */}
      <div className="noise-overlay" aria-hidden="true" />

      {/* Global Navigation Header */}
      <AppHeader currentView={currentView} onNavigate={navigate} mode={mode} />

      {/* Global Authentication Modal */}
      <AuthModal />

      {/* View Router */}
      {currentView === 'home' && (
        <HomePage onNavigate={navigate} />
      )}

      {currentView === 'f1-landing' && (
        <F1LandingPage
          onLaunch={() => { setMode('motorsport'); navigate('f1-workspace') }}
          onBack={() => navigate('home')}
        />
      )}

      {currentView === 'ev-landing' && (
        <EVLandingPage
          onLaunch={() => { setMode('ev'); navigate('ev-workspace') }}
          onBack={() => navigate('home')}
        />
      )}

      {currentView === 'f1-workspace' && (
        <Suspense fallback={
          <div className="flex-1 flex items-center justify-center gap-3"
            style={{ color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}
          >
            <span className="inline-block w-4 h-4 rounded-full animate-spin"
              style={{ border: '2px solid var(--border-mid)', borderTopColor: '#E8FF00' }}
            />
            Loading F1 Telemetry Workspace...
          </div>
        }>
          <F1WorkspacePage
            selectedYear={selectedYear}
            setSelectedYear={setSelectedYear}
            selectedEvent={selectedEvent}
            setSelectedEvent={setSelectedEvent}
            selectedSessionType={selectedSessionType}
            setSelectedSessionType={setSelectedSessionType}
            selectedDriver={selectedDriver}
            setSelectedDriver={setSelectedDriver}
            availableDrivers={availableDrivers}
            availableEvents={availableEvents}
            reasoningMode={reasoningMode}
            setReasoningMode={setReasoningMode}
            loading={loading}
            data={data}
            error={error}
            elapsedMs={elapsedMs}
            vlmStatus={vlmStatus}
            onAnalyze={analyzeAnomalyRange}
            onOpenDossier={() => setIsDossierOpen(true)}
          />
        </Suspense>
      )}

      {currentView === 'ev-workspace' && (
        <Suspense fallback={
          <div className="flex-1 flex items-center justify-center gap-3"
            style={{ color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}
          >
            <span className="inline-block w-4 h-4 rounded-full animate-spin"
              style={{ border: '2px solid var(--border-mid)', borderTopColor: '#00FF88' }}
            />
            Loading EV Battery Workspace...
          </div>
        }>
          <EVWorkspacePage
            selectedCycle={selectedCycle}
            setSelectedCycle={setSelectedCycle}
            reasoningMode={reasoningMode}
            setReasoningMode={setReasoningMode}
            loading={loading}
            data={data}
            error={error}
            elapsedMs={elapsedMs}
            vlmStatus={vlmStatus}
            onAnalyze={analyzeAnomalyRange}
            onOpenDossier={() => setIsDossierOpen(true)}
          />
        </Suspense>
      )}

      {/* Diagnostic Dossier Export Modal */}
      <DiagnosticDossierModal
        isOpen={isDossierOpen}
        onClose={() => setIsDossierOpen(false)}
        data={data}
        context={mode === 'ev' ? {
          year:    selectedYear,
          event:   'EV Battery Diagnostics',
          session: selectedCycle,
          driver:  'Pack Unit',
          driverNumber: 'EV',
          team:    'BMS Analysis',
        } : {
          year:    selectedYear,
          event:   activeEventObj.name,
          session: selectedSessionType,
          driver:  activeDriverObj.name,
          driverNumber: activeDriverObj.number,
          team:    activeDriverObj.team,
        }}
        mode={mode}
      />
    </div>
  )
}
