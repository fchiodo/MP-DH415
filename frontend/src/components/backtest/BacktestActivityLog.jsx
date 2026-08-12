import { useEffect, useRef, useState } from 'react'
import { API_URL } from '../../config'

const logTypeColors = {
  SUCCESS: 'text-accent-green',
  INFO: 'text-primary',
  WARNING: 'text-amber-400',
  SYSTEM: 'text-cyan-400',
  ERROR: 'text-red-500',
}

const logTypeIcons = {
  SUCCESS: '✓',
  INFO: '●',
  WARNING: '⚠',
  SYSTEM: '⚙',
  ERROR: '✕',
}

const MAX_LOGS = 300

function BacktestActivityLog() {
  const [logs, setLogs] = useState([])
  const [sseConnected, setSseConnected] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const logContainerRef = useRef(null)

  // Initial load of recent logs
  useEffect(() => {
    fetch(`${API_URL}/api/backtest/logs?limit=150`)
      .then((r) => r.json())
      .then((data) => setLogs(data.logs || []))
      .catch(() => {})
  }, [])

  // Live updates via SSE (same protocol as the dashboard activity log)
  useEffect(() => {
    const eventSource = new EventSource(`${API_URL}/api/backtest/logs/stream`)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (!data.id) {
          // 'connected' handshake message
          setSseConnected(true)
          return
        }
        setLogs((prev) => {
          if (prev.some((l) => l.id === data.id)) return prev
          return [data, ...prev].slice(0, MAX_LOGS)
        })
      } catch {
        // ignore malformed events
      }
    }

    eventSource.onerror = () => {
      setSseConnected(false)
      eventSource.close()
      const timer = setTimeout(() => setRetryCount((c) => c + 1), 3000)
      return () => clearTimeout(timer)
    }

    return () => eventSource.close()
  }, [retryCount])

  // Auto-scroll to top when new logs arrive (newest first)
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = 0
    }
  }, [logs.length])

  const clearLogs = async () => {
    try {
      await fetch(`${API_URL}/api/backtest/logs/clear`, { method: 'POST' })
      setLogs([])
    } catch {
      // ignore
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between px-2">
        <h3 className="text-sm font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-widest flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">science</span>
          Backtest Log
          {logs.length > 0 && (
            <span className="text-xs font-normal text-slate-400">({logs.length})</span>
          )}
          <span className={`inline-flex items-center gap-1 text-[10px] font-normal px-1.5 py-0.5 rounded ${
            sseConnected
              ? 'bg-emerald-500/20 text-emerald-400'
              : 'bg-amber-500/20 text-amber-400'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${sseConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></span>
            {sseConnected ? 'LIVE' : 'CONNECTING...'}
          </span>
        </h3>
        <button
          onClick={clearLogs}
          className="text-xs font-bold text-primary hover:text-primary/80 disabled:opacity-50"
          disabled={logs.length === 0}
        >
          Clear logs
        </button>
      </div>
      <div
        ref={logContainerRef}
        className="bg-slate-900 rounded-xl p-4 font-mono text-xs border border-slate-800 shadow-xl overflow-y-auto space-y-1.5 max-h-80"
      >
        {logs.length === 0 ? (
          <div className="text-slate-500 text-center py-4">
            <p>No backtest activity yet.</p>
            <p className="text-slate-600 text-[10px] mt-1">
              Start a backtest with the Run Backtest button: progress will appear here in real-time.
            </p>
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="flex gap-2 items-start hover:bg-slate-800/50 -mx-2 px-2 py-0.5 rounded">
              <span className="text-slate-600 shrink-0">
                [{(log.timestamp || '').split(' ')[1] || log.timestamp}]
              </span>
              {log.pair && (
                <span className="text-slate-400 shrink-0">[{log.pair}]</span>
              )}
              <span className={`shrink-0 ${logTypeColors[log.type] || 'text-slate-400'}`}>
                {logTypeIcons[log.type] || '●'} {log.type}:
              </span>
              <span className="text-slate-300 break-words">
                {log.message}
                {log.details && (
                  <span className="block text-slate-500 whitespace-pre-wrap">{log.details}</span>
                )}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default BacktestActivityLog
