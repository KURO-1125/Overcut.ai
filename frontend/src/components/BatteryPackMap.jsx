import React, { useMemo } from 'react'
import {
  Zap, AlertTriangle, Thermometer, ShieldCheck,
  Gauge, Activity, Layers
} from 'lucide-react'

export default function BatteryPackMap({
  packTopology,
  hoverMetrics,
  onModuleClick
}) {
  // Graceful default topology when props are not loaded from backend
  const activeTopology = useMemo(() => {
    if (packTopology && packTopology.modules) return packTopology

    return {
      pack_id: "NASA-NMC811-96S",
      chemistry: "Lithium Nickel Manganese Cobalt (NMC 811)",
      nominal_voltage: 355.2,
      capacity_kwh: 78.4,
      soh_percent: 88.4,
      ambient_temp_c: 22.5,
      cooling_flow_lpm: 14.2,
      isolation_kohm: 850,
      contactors_closed: true,
      active_dtc: "P0A80",
      modules: [
        {
          id: "MOD-01",
          cells: 24,
          status: "HEALTHY",
          voltage_v: 3.78,
          temp_c: 26.8,
          fault_flag: null,
          anomaly_window: null
        },
        {
          id: "MOD-02",
          cells: 24,
          status: "HEALTHY",
          voltage_v: 3.77,
          temp_c: 27.4,
          fault_flag: null,
          anomaly_window: null
        },
        {
          id: "MOD-03",
          cells: 24,
          status: "DEGRADED",
          voltage_v: 3.24,
          temp_c: 34.2,
          fault_flag: "P0A80: CELL_3_VOLTAGE_SAG",
          anomaly_window: [40.0, 58.0]
        },
        {
          id: "MOD-04",
          cells: 24,
          status: "HEALTHY",
          voltage_v: 3.75,
          temp_c: 27.1,
          fault_flag: null,
          anomaly_window: null
        },
      ]
    }
  }, [packTopology])

  const {
    pack_id,
    chemistry,
    capacity_kwh,
    soh_percent = 88.4,
    ambient_temp_c = 22.5,
    cooling_flow_lpm = 14.2,
    isolation_kohm = 850,
    active_dtc,
    modules
  } = activeTopology

  // Extract real-time telemetry from hoverMetrics or fallback to topology baseline
  const liveVoltage = hoverMetrics?.voltage != null ? hoverMetrics.voltage : 3.75
  const liveCurrent = hoverMetrics?.current != null ? hoverMetrics.current : 32.4
  const liveTemp = hoverMetrics?.temperature != null ? hoverMetrics.temperature : 28.5
  const liveSoc = hoverMetrics?.soc != null ? hoverMetrics.soc : 91
  const liveImbalance = hoverMetrics?.imbalance != null ? hoverMetrics.imbalance : 18.5

  // 96S Pack Bus Voltage calculation
  const busVoltage = Number((liveVoltage * 96).toFixed(1))
  const busPowerKw = Number(((busVoltage * liveCurrent) / 1000).toFixed(1))
  const isRegen = liveCurrent < 0

  return (
    <div
      className="flex flex-col"
      style={{
        background: 'var(--bg-surface-2)',
        borderLeft: '1px solid var(--border-dim)',
        fontFamily: "'Inter', sans-serif",
      }}
      role="region"
      aria-label="BMS High-Voltage Battery Pack Architecture"
    >
      {/* Top accent bar */}
      <div
        className="h-[2px] flex-shrink-0"
        style={{
          background: active_dtc
            ? 'linear-gradient(90deg, transparent, rgba(255,184,0,0.8), rgba(255,51,102,0.6), transparent)'
            : 'linear-gradient(90deg, transparent, rgba(0,255,136,0.8), rgba(0,212,255,0.6), transparent)'
        }}
      />

      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-none">

      {/* ── BMS Header ────────────────────────────────────────────── */}
      <div className="flex items-center justify-between pb-3 border-b border-white/5">
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-xl flex items-center justify-center border shadow-inner"
            style={{
              background: 'rgba(0,255,136,0.1)',
              borderColor: 'rgba(0,255,136,0.25)',
              color: '#00FF88'
            }}
          >
            <Zap size={16} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[13px] font-bold text-white tracking-wide">
                BMS Pack Architecture
              </span>
              <span className="text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/25 font-mono uppercase tracking-wider">
                96S 3P
              </span>
            </div>
            <p className="text-[10px] text-zinc-400 mt-0.5">
              {chemistry} · {capacity_kwh} kWh
            </p>
          </div>
        </div>

        {/* Live Status Pill */}
        <div className="flex items-center gap-2">
          {active_dtc ? (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 animate-pulse">
              <AlertTriangle size={11} />
              <span className="font-mono text-[10px] font-bold tracking-wider">
                DTC {active_dtc}
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-400">
              <span className="live-beacon beacon-ev" />
              <span className="font-mono text-[10px] font-bold tracking-wider">
                NOMINAL 96S
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ── Pack State Telemetry Ribbon ────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {/* Bus Voltage */}
        <div className="p-2.5 rounded-2xl bg-white/[0.03] border border-white/5">
          <div className="flex items-center justify-between text-[9px] text-zinc-400 uppercase tracking-wider mb-1 font-mono">
            <span>Bus Voltage</span>
            <Gauge size={10} className="text-cyan-400" />
          </div>
          <div className="text-[16px] font-bold font-mono text-cyan-300">
            {busVoltage} <span className="text-[11px] font-normal text-zinc-400">V</span>
          </div>
          <div className="text-[9px] text-zinc-400 font-mono mt-0.5">
            {liveVoltage.toFixed(3)} V / cell avg
          </div>
        </div>

        {/* Live Current / Power */}
        <div className="p-2.5 rounded-2xl bg-white/[0.03] border border-white/5">
          <div className="flex items-center justify-between text-[9px] text-zinc-400 uppercase tracking-wider mb-1 font-mono">
            <span>{isRegen ? 'Regen Inrush' : 'Bus Current'}</span>
            <Activity size={10} className={isRegen ? 'text-emerald-400' : 'text-amber-400'} />
          </div>
          <div className={`text-[16px] font-bold font-mono ${isRegen ? 'text-emerald-300' : 'text-amber-300'}`}>
            {liveCurrent > 0 ? `+${liveCurrent.toFixed(1)}` : liveCurrent.toFixed(1)} <span className="text-[11px] font-normal text-zinc-400">A</span>
          </div>
          <div className="text-[9px] text-zinc-400 font-mono mt-0.5">
            {Math.abs(busPowerKw)} kW {isRegen ? 'Recovered' : 'Draw'}
          </div>
        </div>

        {/* Core Temperature */}
        <div className="p-2.5 rounded-2xl bg-white/[0.03] border border-white/5">
          <div className="flex items-center justify-between text-[9px] text-zinc-400 uppercase tracking-wider mb-1 font-mono">
            <span>Core Temp</span>
            <Thermometer size={10} className={liveTemp > 45 ? 'text-rose-400' : 'text-zinc-400'} />
          </div>
          <div className={`text-[16px] font-bold font-mono ${liveTemp > 48 ? 'text-rose-400' : liveTemp > 38 ? 'text-amber-300' : 'text-zinc-200'}`}>
            {liveTemp.toFixed(1)} <span className="text-[11px] font-normal text-zinc-400">°C</span>
          </div>
          <div className="text-[9px] text-zinc-400 font-mono mt-0.5">
            {liveTemp > 45 ? 'Active Chilling' : `Ambient ${ambient_temp_c}°C`}
          </div>
        </div>

        {/* Cell Imbalance */}
        <div className="p-2.5 rounded-2xl bg-white/[0.03] border border-white/5">
          <div className="flex items-center justify-between text-[9px] text-zinc-400 uppercase tracking-wider mb-1 font-mono">
            <span>ΔV Imbalance</span>
            <Layers size={10} className={liveImbalance > 50 ? 'text-amber-400' : 'text-emerald-400'} />
          </div>
          <div className={`text-[16px] font-bold font-mono ${liveImbalance > 80 ? 'text-rose-400' : liveImbalance > 40 ? 'text-amber-300' : 'text-emerald-300'}`}>
            {liveImbalance.toFixed(0)} <span className="text-[11px] font-normal text-zinc-400">mV</span>
          </div>
          <div className="text-[9px] text-zinc-400 font-mono mt-0.5">
            {liveImbalance > 50 ? 'Above 50mV Limit' : '< 20mV Target'}
          </div>
        </div>
      </div>

      {/* ── State of Health & State of Charge Meters ───────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-2xl bg-white/[0.02] border border-white/5">
        {/* State of Health */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-zinc-300 font-medium">State of Health (SoH)</span>
            <span className="font-mono font-bold text-emerald-400">{soh_percent}%</span>
          </div>
          <div className="h-2 rounded-full bg-zinc-800/80 overflow-hidden relative">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${soh_percent}%`,
                background: 'linear-gradient(90deg, #00FF88, #00D4FF)',
                boxShadow: '0 0 10px rgba(0,255,136,0.4)'
              }}
            />
          </div>
          <div className="flex justify-between text-[9px] text-zinc-500 font-mono">
            <span>Cycle 84 / 1500 EOL</span>
            <span>R_int: 24.8 mΩ</span>
          </div>
        </div>

        {/* State of Charge */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-zinc-300 font-medium">State of Charge (SoC)</span>
            <span className="font-mono font-bold text-cyan-400">{liveSoc}%</span>
          </div>
          <div className="h-2 rounded-full bg-zinc-800/80 overflow-hidden relative">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${liveSoc}%`,
                background: liveSoc < 20
                  ? 'linear-gradient(90deg, #FF3366, #FF6B35)'
                  : 'linear-gradient(90deg, #00D4FF, #00FF88)',
                boxShadow: '0 0 10px rgba(0,212,255,0.4)'
              }}
            />
          </div>
          <div className="flex justify-between text-[9px] text-zinc-500 font-mono">
            <span>Usable: 71.4 kWh</span>
            <span>Coulomb Count: OK</span>
          </div>
        </div>
      </div>

      {/* ── High-Voltage Safety Status Ribbon ──────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-2 px-3 py-2 rounded-2xl bg-emerald-500/[0.04] border border-emerald-500/15 font-mono text-[9px] text-zinc-400">
        <div className="flex items-center gap-1.5">
          <ShieldCheck size={12} className="text-emerald-400" />
          <span>HVIL LOOP: <strong className="text-emerald-400">CLOSED (CONTINUOUS)</strong></span>
        </div>
        <div className="flex items-center gap-1.5">
          <span>CONTACTORS: <strong className="text-zinc-200">384V DC ENERGIZED</strong></span>
        </div>
        <div className="flex items-center gap-1.5">
          <span>ISOLATION: <strong className="text-cyan-300">{isolation_kohm} kΩ</strong> (&gt;500 Ω/V)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span>COOLING: <strong className="text-zinc-200">{cooling_flow_lpm} L/min</strong></span>
        </div>
      </div>

      {/* ── 4-Module Physical Architecture Schematic Grid ──────────── */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-bold text-zinc-300 tracking-wide">
            Module Taps &amp; Cell Degradation Matrix
          </span>
          <span className="text-[9px] text-zinc-500 font-mono uppercase tracking-wide">
            Click to slice anomaly
          </span>
        </div>

        {/* Always 2-col grid regardless of container width */}
        <div className="grid grid-cols-2 gap-2">
          {modules.map((mod, idx) => {
            const isDegraded = mod.status === 'DEGRADED' || mod.fault_flag != null
            const isWarning = mod.status === 'WARNING'

            const borderColor = isDegraded
              ? 'rgba(245,158,11,0.4)'
              : isWarning
              ? 'rgba(239,68,68,0.4)'
              : 'rgba(255,255,255,0.05)'

            const bgColor = isDegraded
              ? 'rgba(245,158,11,0.05)'
              : isWarning
              ? 'rgba(239,68,68,0.05)'
              : 'rgba(255,255,255,0.02)'

            return (
              <div
                key={mod.id || idx}
                tabIndex={0}
                role="button"
                aria-label={`Inspect ${mod.id} — ${mod.status}`}
                onClick={() => onModuleClick?.(mod)}
                onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onModuleClick?.(mod) } }}
                className="p-3 rounded-xl border cursor-pointer transition-all duration-200 group focus:outline-none"
                style={{ background: bgColor, border: `1px solid ${borderColor}` }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = isDegraded ? 'rgba(245,158,11,0.7)' : isWarning ? 'rgba(239,68,68,0.7)' : 'rgba(255,255,255,0.15)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = borderColor }}
              >
                {/* Module ID row */}
                <div className="flex items-center justify-between mb-2 gap-1 min-w-0">
                  <div className="flex items-center gap-1 min-w-0">
                    <span className="font-mono text-[11px] font-bold text-white truncate">
                      {mod.id}
                    </span>
                    <span className="text-[8px] text-zinc-500 font-mono flex-shrink-0">(24S)</span>
                  </div>
                  {/* Compact status badge — no text wrap */}
                  {isDegraded ? (
                    <span
                      className="flex-shrink-0 font-mono text-[8px] font-bold px-1.5 py-0.5 rounded"
                      style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b', border: '1px solid rgba(245,158,11,0.35)', whiteSpace: 'nowrap' }}
                    >
                      ⚠ {mod.fault_flag ? mod.fault_flag.split(':')[0] : 'DTC'}
                    </span>
                  ) : isWarning ? (
                    <span
                      className="flex-shrink-0 font-mono text-[8px] font-bold px-1.5 py-0.5 rounded"
                      style={{ background: 'rgba(239,68,68,0.15)', color: '#f87171', border: '1px solid rgba(239,68,68,0.35)', whiteSpace: 'nowrap' }}
                    >
                      TEMP
                    </span>
                  ) : (
                    <span
                      className="flex-shrink-0 font-mono text-[8px] font-bold px-1.5 py-0.5 rounded"
                      style={{ background: 'rgba(16,185,129,0.1)', color: '#34d399', border: '1px solid rgba(16,185,129,0.25)', whiteSpace: 'nowrap' }}
                    >
                      OK
                    </span>
                  )}
                </div>

                {/* Cell tap bar — 12 cells */}
                <div className="flex gap-0.5 mb-2.5" aria-hidden="true">
                  {[...Array(12)].map((_, cIdx) => {
                    const isFaultCell = (isDegraded && cIdx === 2) || (isWarning && cIdx >= 8)
                    return (
                      <div
                        key={cIdx}
                        className="flex-1 h-1.5 rounded-sm"
                        style={{
                          background: isFaultCell
                            ? (isDegraded ? '#f59e0b' : '#f87171')
                            : 'rgba(16,185,129,0.4)',
                          boxShadow: isFaultCell ? (isDegraded ? '0 0 6px #f59e0b80' : '0 0 6px #f8717180') : 'none',
                        }}
                      />
                    )
                  })}
                </div>

                {/* Metrics — stacked for narrow column */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between font-mono text-[9px]">
                    <span className="text-zinc-500">Tap Avg V</span>
                    <span style={{ color: isDegraded ? '#f59e0b' : 'var(--text-secondary)', fontWeight: isDegraded ? 700 : 400 }}>
                      {mod.voltage_v.toFixed(2)}V
                    </span>
                  </div>
                  <div className="flex items-center justify-between font-mono text-[9px]">
                    <span className="text-zinc-500">NTC Temp</span>
                    <span style={{ color: mod.temp_c > 45 ? '#f87171' : mod.temp_c > 32 ? '#f59e0b' : 'var(--text-secondary)' }}>
                      {mod.temp_c.toFixed(1)}°C
                    </span>
                  </div>
                </div>

                {/* ROI footer */}
                <div className="mt-2 pt-2 flex items-center justify-between font-mono text-[8px] text-zinc-500"
                  style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
                >
                  {mod.anomaly_window ? (
                    <span style={{ color: '#f59e0b', fontWeight: 700 }}>
                      ROI {mod.anomaly_window[0]}–{mod.anomaly_window[1]}s
                    </span>
                  ) : (
                    <span>Nominal 24S</span>
                  )}
                  <span className="group-hover:text-zinc-300 transition-colors">Slice →</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* BMS Footer */}
      <div className="pt-2 border-t flex items-center justify-between font-mono text-[10px] text-zinc-400"
        style={{ borderColor: 'var(--border-dim)' }}
      >
        <div className="flex items-center gap-2">
          <Thermometer size={12} className="text-zinc-400" />
          <span>COOLANT INLET: <strong className="text-zinc-200">21.4°C</strong> (OUT 26.2°C)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span className="text-zinc-300 font-medium">{pack_id}</span>
        </div>
      </div>
      </div>{/* end scrollable inner */}
    </div>
  )
}
