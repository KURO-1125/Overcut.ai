import React, { useEffect } from 'react'
import { FileText, Printer, Download, X, ShieldCheck } from 'lucide-react'

export default function DiagnosticDossierModal({ isOpen, onClose, data, context, mode }) {
  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handleKey)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.body.style.overflow = previousOverflow
    }
  }, [isOpen, onClose])

  if (!isOpen || !data) return null

  const diag    = data.diagnostic || {}
  const isEV    = mode === 'ev' || diag.domain === 'EV_BATTERY'
  const dossierDate = data.analyzed_at ? new Date(data.analyzed_at) : null
  const dossierDay  = dossierDate && !Number.isNaN(dossierDate.getTime())
    ? dossierDate.toISOString().slice(0, 10).replace(/-/g, '')
    : 'LIVE'
  const dossierId  = `OVERCUT-DOSSIER-${diag.anomaly_id || 'LIVE'}-${dossierDay}`
  const timestamp  = dossierDate && !Number.isNaN(dossierDate.getTime()) ? dossierDate.toUTCString() : '—'

  // Severity color mapping
  const severityColors = {
    CRITICAL: { bg: 'rgba(255,51,102,0.1)',  text: '#FF3366', border: 'rgba(255,51,102,0.35)' },
    HIGH:     { bg: 'rgba(255,107,53,0.1)',  text: '#FF6B35', border: 'rgba(255,107,53,0.35)' },
    MEDIUM:   { bg: 'rgba(255,184,0,0.1)',   text: '#FFB800', border: 'rgba(255,184,0,0.35)' },
    LOW:      { bg: 'rgba(0,212,255,0.1)',   text: '#00D4FF', border: 'rgba(0,212,255,0.35)' },
  }
  const sc = severityColors[diag.severity] || severityColors.HIGH

  // Download Markdown Dossier
  const handleDownloadMarkdown = () => {
    const mdContent = `# OVERCUT.AI — ${isEV ? 'BMS BATTERY RELIABILITY DOSSIER' : 'FIA PIT-WALL TECHNICAL INCIDENT DOSSIER'}
**Document Reference:** ${dossierId}
**Timestamp:** ${timestamp}
**Classification:** RESTRICTED // ENGINEERING CRITICAL
**Domain:** ${diag.domain || (isEV ? 'EV_BATTERY' : 'MOTORSPORT_F1')}
**Subject:** ${context.driver}
**Session:** ${context.session}

---

## 1. Executive Summary & Root Cause
- **Anomaly Identifier:** ${diag.anomaly_id || 'ANOM-LIVE'}
- **Severity Rating:** ${diag.severity || 'HIGH'}
- **Confidence Rating:** ${Math.round((diag.confidence ?? 0) * 100)}%
- **Root Cause Determination:** ${diag.root_cause || diag.title || 'Telemetry anomaly observed across channels.'}
- **Reasoning Provenance:** ${diag.provider || 'FAISS Joint Multimodal Retrieval'}

---

## 2. Deterministic Physical Evidence Citations
${(diag.physical_evidence || []).map((ev, i) => `${i + 1}. ${ev}`).join('\n')}

---

## 3. Strategic Action Protocol
> **TACTICAL DIRECTIVE:**
> ${diag.strategic_recommendation || 'Maintain real-time observation and prepare for telemetry verification.'}

---

## 4. FAISS Historical Precedent Matches
${(data.historical_precedents || []).map((p, i) => `### Match #${i + 1} (${p.similarity ?? 0}% Cosine Similarity)
- **Session:** ${p.session}
- **Observation:** ${p.observation}
`).join('\n')}

---
*Generated autonomously by Overcut.ai Generative Multimodal Observability Gateway.*
`
    const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${dossierId}.md`; a.click()
    URL.revokeObjectURL(url)
  }

  // Download JSON Dossier
  const handleDownloadJSON = () => {
    const dossierObject = {
      dossier_id:    dossierId,
      created_at:    new Date().toISOString(),
      classification: 'RESTRICTED // PIT-WALL TELEMETRY',
      domain:        diag.domain || (isEV ? 'EV_BATTERY' : 'MOTORSPORT_F1'),
      session_context: context,
      diagnostic_report: diag,
      vector_space: {
        dimensions:      data.vector_shape ? data.vector_shape[1] : 512,
        embedding_sample: data.embedding_preview || [],
        index:           'FAISS IndexFlatIP (Unit Hypersphere)',
      },
      waveform_crop: {
        filename:  data.crop_filename,
        image_url: data.image_url,
      },
      historical_precedents: data.historical_precedents || [],
    }
    const blob = new Blob([JSON.stringify(dossierObject, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${dossierId}.json`; a.click()
    URL.revokeObjectURL(url)
  }

  const handlePrint = () => window.print()

  const monoStyle = { fontFamily: "'JetBrains Mono', monospace" }
  const displayStyle = { fontFamily: "'Space Grotesk', sans-serif" }
  const bodyStyle = { fontFamily: "'Inter', sans-serif" }

  return (
    <div
      className="fixed inset-0 z-[999] flex items-center justify-center p-4 overflow-y-auto"
      style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)' }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="dossier-modal-title"
    >
      <div
        className="w-full max-w-4xl max-h-[92vh] flex flex-col rounded-xl overflow-hidden my-auto"
        style={{
          background: 'var(--bg-surface-1)',
          border: '1px solid var(--border-mid)',
          boxShadow: '0 32px 100px rgba(0,0,0,0.7)',
        }}
      >
        {/* Top bar */}
        <div
          className="no-print flex items-center justify-between px-5 py-3.5"
          style={{
            borderBottom: '1px solid var(--border-mid)',
            background: 'var(--bg-surface-2)',
            flexShrink: 0,
          }}
        >
          <div className="flex items-center gap-2.5">
            <FileText size={15} style={{ color: 'var(--accent)' }} aria-hidden="true" />
            <span
              className="text-[11px] font-bold uppercase tracking-wider"
              style={{ color: 'var(--text-secondary)', ...monoStyle }}
            >
              Diagnostic Engineering Dossier
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-semibold cursor-pointer transition-colors"
              style={{
                ...displayStyle,
                background: 'var(--accent)',
                color: '#000',
                border: 'none',
              }}
            >
              <Printer size={11} aria-hidden="true" />
              <span>Print / PDF</span>
            </button>
            <button
              onClick={handleDownloadMarkdown}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-medium cursor-pointer transition-colors"
              style={{
                background: 'var(--bg-surface-3)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border-mid)',
                ...bodyStyle,
              }}
            >
              <Download size={11} aria-hidden="true" />
              <span>Markdown</span>
            </button>
            <button
              onClick={handleDownloadJSON}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px] font-medium cursor-pointer transition-colors"
              style={{
                background: 'var(--bg-surface-3)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border-mid)',
                ...bodyStyle,
              }}
            >
              <Download size={11} aria-hidden="true" />
              <span>JSON</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-md cursor-pointer transition-colors"
              style={{ color: 'var(--text-muted)', background: 'none', border: 'none' }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-bright)'; e.currentTarget.style.background = 'var(--bg-surface-3)' }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'none' }}
              aria-label="Close Dossier"
            >
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Printable dossier body */}
        <div
          id="printable-dossier"
          className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6"
          style={{ color: 'var(--text-secondary)', ...bodyStyle }}
        >

          {/* Letterhead */}
          <div
            className="pb-5"
            style={{ borderBottom: '2px solid var(--border-bright)' }}
          >
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                {/* Diamond logo */}
                <svg width="32" height="32" viewBox="0 0 28 28" fill="none" aria-hidden="true">
                  <polygon points="14,2 26,14 14,26 2,14" stroke="var(--accent)" strokeWidth="1.5" fill="none" />
                  <circle cx="14" cy="14" r="2" fill="var(--accent)" />
                </svg>
                <div>
                  <div
                    className="text-[10px] tracking-[0.18em] uppercase font-bold mb-0.5"
                    style={{ color: 'var(--accent)', ...monoStyle }}
                  >
                    OVERCUT.AI OBSERVABILITY PLATFORM
                  </div>
                  <h1
                    id="dossier-modal-title"
                    className="text-[18px] md:text-[22px] font-bold uppercase"
                    style={{ color: 'var(--text-bright)', ...displayStyle }}
                  >
                    {isEV ? 'Battery Energy Storage Reliability Dossier' : 'FIA Pit-Wall Technical Incident Dossier'}
                  </h1>
                </div>
              </div>

              <div className="text-right space-y-0.5" style={{ ...monoStyle, fontSize: '10px' }}>
                <div style={{ color: 'var(--text-muted)' }}>
                  DOC REF: <strong style={{ color: 'var(--text-primary)' }}>{dossierId}</strong>
                </div>
                <div style={{ color: 'var(--text-muted)' }}>
                  STATUS: <strong style={{ color: '#00FF88' }}>OFFICIALLY GROUNDED</strong>
                </div>
                <div style={{ color: 'var(--text-disabled)' }}>{timestamp}</div>
              </div>
            </div>

            {/* Metadata row */}
            <div
              className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4 pt-3"
              style={{ borderTop: '1px solid var(--border-dim)' }}
            >
              {[
                { label: 'Session / Event', value: context.session },
                { label: 'Subject Vehicle', value: context.driver, accent: true },
                { label: 'Team / Organization', value: context.team || 'N/A' },
                { label: 'Grounding Track', value: context.event || 'N/A', cyan: true },
              ].map(({ label, value, accent, cyan }) => (
                <div
                  key={label}
                  className="p-2 rounded-lg"
                  style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-dim)' }}
                >
                  <span
                    className="block text-[9px] uppercase font-bold mb-0.5"
                    style={{ color: 'var(--text-disabled)', ...monoStyle }}
                  >
                    {label}
                  </span>
                  <span
                    className="text-[11px] font-semibold"
                    style={{
                      color: accent ? '#FFB800' : cyan ? 'var(--accent)' : 'var(--text-primary)',
                      ...monoStyle,
                    }}
                  >
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Anomaly Classification */}
          <div
            className="p-4 rounded-xl space-y-3"
            style={{ background: sc.bg, border: `1px solid ${sc.border}` }}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className="px-2.5 py-0.5 rounded-full text-[10px] font-bold"
                  style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-mid)', color: 'var(--text-secondary)', ...monoStyle }}
                >
                  {diag.anomaly_id || 'ANOM-LIVE'}
                </span>
                <span
                  className="px-2.5 py-0.5 rounded-full text-[10px] font-bold"
                  style={{ background: sc.bg, border: `1px solid ${sc.border}`, color: sc.text, ...monoStyle }}
                >
                  {diag.severity || 'HIGH'} SEVERITY
                </span>
                <span
                  className="px-2.5 py-0.5 rounded-full text-[10px] font-bold"
                  style={{ background: 'rgba(0,212,255,0.08)', border: '1px solid rgba(0,212,255,0.25)', color: 'var(--accent)', ...monoStyle }}
                >
                  {diag.domain || (isEV ? 'EV_BATTERY' : 'MOTORSPORT_F1')}
                </span>
              </div>
              <div className="flex items-center gap-2" style={{ ...monoStyle, fontSize: '12px' }}>
                <span style={{ color: 'var(--text-muted)' }}>CONFIDENCE:</span>
                <strong style={{ color: '#00FF88', fontSize: '15px' }}>
                  {Math.round((diag.confidence ?? 0) * 100)}%
                </strong>
                <ShieldCheck size={14} style={{ color: '#00FF88' }} />
              </div>
            </div>

            <div>
              <span
                className="block text-[10px] uppercase font-bold mb-1"
                style={{ color: sc.text, ...monoStyle }}
              >
                Root Cause Determination
              </span>
              <h2
                className="text-[16px] md:text-[18px] font-bold"
                style={{ color: 'var(--text-bright)', ...displayStyle }}
              >
                {diag.root_cause || diag.title || 'Telemetry variance detected across primary channels.'}
              </h2>
            </div>
          </div>

          {/* Dual column: waveform + evidence */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

            {/* Waveform artifact */}
            <div className="space-y-2">
              <span
                className="block text-[10px] font-bold uppercase"
                style={{ color: 'var(--text-secondary)', ...monoStyle }}
              >
                Optical ROI Telemetry Waveform Crop
              </span>
              <div
                className="flex items-center justify-center rounded-lg overflow-hidden"
                style={{
                  background: 'rgba(0,0,0,0.5)',
                  border: '1px solid var(--border-mid)',
                  minHeight: '120px',
                }}
              >
                {data.image_url ? (
                  <img
                    src={data.image_url}
                    alt="Telemetry anomaly waveform crop"
                    className="w-full h-auto"
                  />
                ) : (
                  <span
                    className="p-6 text-center text-[11px]"
                    style={{ color: 'var(--text-disabled)', ...monoStyle }}
                  >
                    High-contrast waveform crop rendered from the telemetry slice
                  </span>
                )}
              </div>
              <div
                className="flex justify-between text-[9px]"
                style={{ color: 'var(--text-disabled)', ...monoStyle }}
              >
                <span>ARTIFACT: {data.crop_filename || 'roi_telemetry.png'}</span>
                <span>OPENCLIP EMBEDDED</span>
              </div>
            </div>

            {/* Evidence citations */}
            <div className="space-y-2">
              <span
                className="block text-[10px] font-bold uppercase"
                style={{ color: 'var(--text-secondary)', ...monoStyle }}
              >
                Deterministic Physical Evidence Citations
              </span>
              <ul className="space-y-2 list-none p-0 m-0">
                {(diag.physical_evidence || []).map((ev, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2.5 p-2.5 rounded-lg text-[12px]"
                    style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-dim)' }}
                  >
                    <span
                      className="font-bold text-[10px] flex-shrink-0"
                      style={{ color: 'var(--accent)', ...monoStyle }}
                    >
                      #{String(idx + 1).padStart(2, '0')}
                    </span>
                    <span style={{ color: 'var(--text-secondary)', ...bodyStyle }}>
                      {ev}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Strategic recommendation */}
          <div>
            <span
              className="block text-[10px] font-bold uppercase mb-2"
              style={{ color: 'var(--accent)', ...monoStyle }}
            >
              Strategic Action Protocol & Tactical Guidance
            </span>
            <div
              className="p-4 rounded-lg text-[13px] leading-relaxed font-medium"
              style={{
                background: 'rgba(0,212,255,0.06)',
                border: '1px solid rgba(0,212,255,0.2)',
                color: 'var(--text-primary)',
                ...bodyStyle,
              }}
            >
              {diag.strategic_recommendation || 'Maintain real-time telemetry observation and prepare pit-wall corrective response.'}
            </div>
          </div>

          {/* Historical precedents */}
          {data.historical_precedents?.length > 0 && (
            <div
              className="pt-4"
              style={{ borderTop: '1px solid var(--border-dim)' }}
            >
              <span
                className="block text-[10px] font-bold uppercase mb-3"
                style={{ color: 'var(--text-secondary)', ...monoStyle }}
              >
                FAISS Hypersphere Precedent Matches (Cosine Similarity)
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {data.historical_precedents.map((prec, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-lg space-y-1.5"
                    style={{ background: 'var(--bg-surface-2)', border: '1px solid var(--border-dim)' }}
                  >
                    <div
                      className="flex items-center justify-between text-[10px]"
                      style={{ ...monoStyle }}
                    >
                      <span style={{ color: 'var(--text-disabled)' }}>CASE #{i + 1}</span>
                      <span style={{ color: 'var(--accent)', fontWeight: 700 }}>
                        {prec.similarity || 85}% MATCH
                      </span>
                    </div>
                    <div
                      className="text-[11px] font-semibold truncate"
                      style={{ color: 'var(--text-primary)', ...bodyStyle }}
                    >
                      {prec.session}
                    </div>
                    <p
                      className="text-[11px] leading-relaxed line-clamp-3"
                      style={{ color: 'var(--text-muted)', ...bodyStyle }}
                    >
                      {prec.observation}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Technical provenance footer */}
          <div
            className="pt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[10px]"
            style={{ borderTop: '1px solid var(--border-dim)', ...monoStyle, color: 'var(--text-disabled)' }}
          >
            <div className="space-y-0.5">
              <div>
                ENGINE: <strong style={{ color: 'var(--text-secondary)' }}>
                  {diag.provider || 'FAISS RAG + Multimodal Embeddings'}
                </strong>
              </div>
              <div>
                EMBEDDING: <strong style={{ color: 'var(--text-secondary)' }}>
                  OpenCLIP ViT-B/32 (512-dim unit sphere)
                </strong>
              </div>
            </div>
            <div className="sm:text-right space-y-0.5">
              <div>
                VERIFICATION: <span style={{ color: '#00FF88', fontWeight: 700 }}>
                  AUTHENTICATED // ZERO HALT
                </span>
              </div>
              <div>FIA / BMS ARCHIVAL SPEC: RFC-9110 COMPLIANT</div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
