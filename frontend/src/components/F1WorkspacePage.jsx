import React from 'react'
import {
  Flag,
} from 'lucide-react'
import TimelineWorkspace from './TimelineWorkspace'
import ErrorBoundary from './ErrorBoundary'
import { StyledSelect, SettingsPopover, ResultsPanel } from './WorkspaceShared'
import { SEASONS, SESSION_TYPES } from '../App'

const MODE = 'motorsport'
const ACCENT = '#E8FF00'

export default function F1WorkspacePage({
  selectedYear, setSelectedYear,
  selectedEvent, setSelectedEvent,
  selectedSessionType, setSelectedSessionType,
  selectedDriver, setSelectedDriver,
  availableDrivers, availableEvents,
  reasoningMode, setReasoningMode,
  loading, data, error, elapsedMs,
  vlmStatus, onAnalyze, onOpenDossier,
}) {
  return (
    <main className="flex-1 flex flex-col">

      {/* ── Command Bar ─────────────────────────────────────────── */}
      <div
        className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 px-4 sm:px-6 py-3"
        style={{
          background: 'rgba(8,12,16,0.9)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid var(--border-mid)',
          minHeight: '52px',
          position: 'sticky',
          top: '56px',
          zIndex: 40,
        }}
      >
        <div className="flex flex-wrap items-center gap-2">
          {/* Domain badge */}
          <div
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-bold flex-shrink-0"
            style={{
              background: `${ACCENT}12`,
              color: ACCENT,
              border: `1px solid ${ACCENT}28`,
              fontFamily: "'Space Grotesk', sans-serif",
            }}
          >
            <Flag size={11} />
            <span>FORMULA 1</span>
          </div>

          <div className="w-[1px] h-5 flex-shrink-0" style={{ background: 'var(--border-dim)' }} />

          <StyledSelect value={selectedYear} onChange={e => setSelectedYear(Number(e.target.value))}>
            {SEASONS.map(y => <option key={y} value={y}>{y}</option>)}
          </StyledSelect>

          <StyledSelect value={selectedEvent} onChange={e => setSelectedEvent(e.target.value)} style={{ maxWidth: '200px' }}>
            {availableEvents.map(ev => (
              <option key={ev.id} value={ev.id}>{ev.name}</option>
            ))}
          </StyledSelect>

          <div
            className="flex items-center p-0.5 rounded-md gap-0.5"
            style={{ background: 'var(--bg-surface-3)', border: '1px solid var(--border-dim)' }}
          >
            {SESSION_TYPES.slice(0, 2).map(st => (
              <button
                key={st.id}
                type="button"
                onClick={() => setSelectedSessionType(st.id)}
                className="px-2.5 py-1 rounded text-[11px] font-semibold cursor-pointer transition-all"
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  background: selectedSessionType === st.id ? 'rgba(255,255,255,0.08)' : 'transparent',
                  color: selectedSessionType === st.id ? 'var(--text-bright)' : 'var(--text-muted)',
                  border: selectedSessionType === st.id ? '1px solid var(--border-bright)' : '1px solid transparent',
                }}
              >
                {st.id}
              </button>
            ))}
          </div>
        </div>

        <SettingsPopover
          reasoningMode={reasoningMode}
          setReasoningMode={setReasoningMode}
          vlmStatus={vlmStatus}
          accentColor={ACCENT}
        />
      </div>

      {/* ── Driver Strip ─────────────────────────────────────────── */}
      <div
        style={{ borderBottom: '1px solid var(--border-dim)', background: 'var(--bg-surface-1)', position: 'relative' }}
      >
        <div
          className="flex items-center gap-1 px-4 sm:px-6 py-2 overflow-x-auto scrollbar-none"
          style={{ WebkitOverflowScrolling: 'touch' }}
        >
          <span
            className="text-[9px] font-bold tracking-[0.1em] uppercase whitespace-nowrap flex-shrink-0 mr-1"
            style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
          >
            Driver
          </span>
          <div className="w-[1px] h-4 mr-1 flex-shrink-0" style={{ background: 'var(--border-dim)' }} />
          {availableDrivers.map(d => {
            const isActive = String(d.number) === String(selectedDriver)
            return (
              <button
                key={d.id || d.number}
                type="button"
                onClick={() => setSelectedDriver(String(d.number))}
                className="flex items-center gap-1.5 px-2 py-1.5 rounded-md text-[11px] font-semibold flex-shrink-0 cursor-pointer transition-all whitespace-nowrap"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  background: isActive ? 'rgba(255,255,255,0.07)' : 'transparent',
                  color: isActive ? 'var(--text-bright)' : 'var(--text-muted)',
                  border: isActive ? `1px solid ${d.color || 'var(--border-bright)'}40` : '1px solid transparent',
                  minWidth: 'max-content',
                }}
              >
                <span
                  className="w-2 h-2 rounded-full flex-shrink-0"
                  style={{
                    background: d.color || 'var(--accent)',
                    boxShadow: isActive ? `0 0 6px ${d.color || 'var(--accent)'}` : 'none',
                  }}
                />
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: 'var(--text-muted)' }}>
                  #{d.number}
                </span>
                <span>{d.code}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* ── Main Content ─────────────────────────────────────────── */}
      <div className="flex-1 px-4 sm:px-6 py-5 space-y-5 max-w-7xl w-full mx-auto">

        <ErrorBoundary context="Telemetry Canvas">
          <TimelineWorkspace
            onSelectAnomaly={onAnalyze}
            isAnalyzing={loading}
            mode={MODE}
            useVLM={reasoningMode === 'local_vlm'}
            driver={selectedDriver}
            year={selectedYear}
            event={selectedEvent}
            sessionType={selectedSessionType}
            availableDrivers={availableDrivers}
          />
        </ErrorBoundary>

        <ErrorBoundary context="Diagnostic Results">
          <ResultsPanel
            data={data}
            loading={loading}
            elapsedMs={elapsedMs}
            isEV={false}
            onOpenDossier={onOpenDossier}
            error={error}
          />
        </ErrorBoundary>
      </div>
    </main>
  )
}
