import React from 'react'
import {
  Zap,
} from 'lucide-react'
import TimelineWorkspace from './TimelineWorkspace'
import ErrorBoundary from './ErrorBoundary'
import { StyledSelect, SettingsPopover, ResultsPanel } from './WorkspaceShared'
import { EV_CYCLES } from '../App'

const MODE = 'ev'
const ACCENT = '#00FF88'

export default function EVWorkspacePage({
  selectedCycle, setSelectedCycle,
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
            <Zap size={11} />
            <span>EV FLEET</span>
          </div>

          <div className="w-[1px] h-5 flex-shrink-0" style={{ background: 'var(--border-dim)' }} />

          <StyledSelect value={selectedCycle} onChange={e => setSelectedCycle(e.target.value)} style={{ maxWidth: '260px' }}>
            {EV_CYCLES.map(c => (
              <option key={c.id} value={c.id}>{c.name} — {c.tag}</option>
            ))}
          </StyledSelect>
        </div>

        <SettingsPopover
          reasoningMode={reasoningMode}
          setReasoningMode={setReasoningMode}
          vlmStatus={vlmStatus}
          accentColor={ACCENT}
        />
      </div>

      {/* ── Pack Strip ───────────────────────────────────────────── */}
      <div
        className="flex items-center gap-1.5 px-4 sm:px-6 py-2 overflow-x-auto scrollbar-none"
        style={{ borderBottom: '1px solid var(--border-dim)', background: 'var(--bg-surface-1)' }}
      >
        <span
          className="text-[9px] font-bold tracking-[0.1em] uppercase whitespace-nowrap flex-shrink-0"
          style={{ color: 'var(--text-disabled)', fontFamily: "'JetBrains Mono', monospace" }}
        >
          Pack
        </span>
        <div className="w-[1px] h-4 mx-1 flex-shrink-0" style={{ background: 'var(--border-dim)' }} />
        {EV_CYCLES.map(c => {
          const isActive = c.id === selectedCycle
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => setSelectedCycle(c.id)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[11px] font-semibold flex-shrink-0 cursor-pointer transition-all"
              style={{
                fontFamily: "'Inter', sans-serif",
                background: isActive ? 'rgba(0,255,136,0.07)' : 'transparent',
                color: isActive ? 'var(--text-bright)' : 'var(--text-muted)',
                border: isActive ? `1px solid ${ACCENT}40` : '1px solid transparent',
              }}
            >
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{
                  background: ACCENT,
                  boxShadow: isActive ? `0 0 6px ${ACCENT}` : 'none',
                  opacity: isActive ? 1 : 0.4,
                }}
              />
              <span>{c.name}</span>
              <span
                className="text-[9px] px-1.5 py-0.5 rounded"
                style={{
                  background: isActive ? `${ACCENT}18` : 'var(--bg-surface-3)',
                  color: isActive ? ACCENT : 'var(--text-disabled)',
                  fontFamily: "'JetBrains Mono', monospace",
                  border: `1px solid ${isActive ? ACCENT + '30' : 'var(--border-dim)'}`,
                }}
              >
                {c.tag}
              </span>
            </button>
          )
        })}
      </div>

      {/* ── Main Content ─────────────────────────────────────────── */}
      <div className="flex-1 px-4 sm:px-6 py-5 space-y-5 max-w-7xl w-full mx-auto">

        <ErrorBoundary context="Telemetry Canvas">
          <TimelineWorkspace
            onSelectAnomaly={onAnalyze}
            isAnalyzing={loading}
            mode={MODE}
            useVLM={reasoningMode === 'local_vlm'}
            cycleKey={selectedCycle}
          />
        </ErrorBoundary>

        <ErrorBoundary context="Diagnostic Results">
          <ResultsPanel
            data={data}
            loading={loading}
            elapsedMs={elapsedMs}
            isEV={true}
            onOpenDossier={onOpenDossier}
            error={error}
          />
        </ErrorBoundary>
      </div>
    </main>
  )
}
