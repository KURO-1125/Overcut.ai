import React from 'react'
import { RefreshCw, AlertTriangle } from 'lucide-react'

/**
 * ErrorBoundary — catches render errors inside the workspace subtree and
 * shows a recoverable inline error state instead of a blank screen.
 *
 * Usage:
 *   <ErrorBoundary context="Telemetry Workspace">
 *     <TimelineWorkspace ... />
 *   </ErrorBoundary>
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, errorMessage: '' }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, errorMessage: error?.message || 'Unknown render error' }
  }

  componentDidCatch(error, info) {
    console.error(`[ErrorBoundary — ${this.props.context || 'Component'}]`, error, info)
  }

  handleReset = () => {
    this.setState({ hasError: false, errorMessage: '' })
  }

  render() {
    if (!this.state.hasError) return this.props.children

    const { context = 'Component' } = this.props

    return (
      <div
        className="flex flex-col items-center justify-center gap-4 p-8 rounded-xl text-center"
        style={{
          background: 'var(--bg-surface-2)',
          border: '1px solid rgba(255,51,102,0.25)',
          minHeight: '240px',
        }}
      >
        {/* Icon */}
        <div
          className="w-12 h-12 rounded-xl flex items-center justify-center"
          style={{ background: 'rgba(255,51,102,0.08)', border: '1px solid rgba(255,51,102,0.2)' }}
        >
          <AlertTriangle size={22} style={{ color: 'var(--severity-critical)' }} />
        </div>

        {/* Title */}
        <div>
          <p
            className="text-[14px] font-semibold mb-1"
            style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-bright)' }}
          >
            {context} Render Error
          </p>
          <p
            className="text-[12px] max-w-sm"
            style={{ color: 'var(--text-muted)', fontFamily: "'Inter', sans-serif" }}
          >
            A runtime error occurred in this panel. The rest of the application is unaffected.
          </p>
        </div>

        {/* Error detail */}
        {this.state.errorMessage && (
          <code
            className="text-[11px] px-3 py-2 rounded-md max-w-sm truncate block w-full text-center"
            style={{
              background: 'var(--bg-surface-3)',
              border: '1px solid var(--border-dim)',
              color: 'var(--severity-critical)',
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            {this.state.errorMessage}
          </code>
        )}

        {/* Retry */}
        <button
          type="button"
          onClick={this.handleReset}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-[12px] font-semibold cursor-pointer transition-all"
          style={{
            fontFamily: "'Space Grotesk', sans-serif",
            background: 'var(--accent)',
            color: '#000',
            border: 'none',
          }}
        >
          <RefreshCw size={13} />
          Retry
        </button>
      </div>
    )
  }
}
