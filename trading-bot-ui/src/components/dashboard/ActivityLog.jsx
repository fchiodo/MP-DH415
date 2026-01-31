import { useEffect, useRef } from 'react'
import { useApp } from '../../context/AppContext'

const logTypeColors = {
  SUCCESS: 'text-accent-green',
  INFO: 'text-primary',
  WARNING: 'text-amber-400',
  SYSTEM: 'text-cyan-400',
  ALERT: 'text-accent-red',
  ERROR: 'text-red-500',
  TRADE: 'text-emerald-400',
  SIGNAL: 'text-violet-400',
}

const logTypeIcons = {
  SUCCESS: '✓',
  INFO: '●',
  WARNING: '⚠',
  SYSTEM: '⚙',
  ALERT: '!',
  ERROR: '✕',
  TRADE: '📈',
  SIGNAL: '🎯',
}

function ActivityLog({ logs, onClear, isExpanded = false, onToggleExpand }) {
  const logContainerRef = useRef(null)
  const { sseConnected } = useApp()

  // Auto-scroll to top when new logs are added
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = 0
    }
  }, [logs.length])

  return (
    <div className={`flex flex-col gap-3 ${isExpanded ? 'h-full' : ''}`}>
      <div className="flex items-center justify-between px-2">
        <h3 className="text-sm font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-widest flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">terminal</span>
          Activity Log
          {logs.length > 0 && (
            <span className="text-xs font-normal text-slate-400">({logs.length})</span>
          )}
          {/* SSE Connection Status */}
          <span className={`inline-flex items-center gap-1 text-[10px] font-normal px-1.5 py-0.5 rounded ${
            sseConnected 
              ? 'bg-emerald-500/20 text-emerald-400' 
              : 'bg-amber-500/20 text-amber-400'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${sseConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></span>
            {sseConnected ? 'LIVE' : 'CONNECTING...'}
          </span>
        </h3>
        <div className="flex items-center gap-3">
          <button 
            onClick={onClear} 
            className="text-xs font-bold text-primary hover:text-primary/80 disabled:opacity-50"
            disabled={logs.length === 0}
          >
            Clear logs
          </button>
          {onToggleExpand && (
            <button
              onClick={onToggleExpand}
              className="text-slate-400 hover:text-primary transition-colors"
              title={isExpanded ? 'Exit fullscreen' : 'Fullscreen'}
            >
              <span className="material-symbols-outlined text-[18px]">
                {isExpanded ? 'close_fullscreen' : 'open_in_full'}
              </span>
            </button>
          )}
        </div>
      </div>
      <div 
        ref={logContainerRef}
        className={`bg-slate-900 rounded-xl p-4 font-mono text-xs border border-slate-800 shadow-xl overflow-y-auto activity-log space-y-1.5 ${
          isExpanded ? 'flex-1' : 'max-h-80'
        }`}
      >
        {logs.length === 0 ? (
          <div className="text-slate-500 text-center py-4">
            <p>No activity yet.</p>
            <p className="text-slate-600 text-[10px] mt-1">
              Logs from the Python bot will appear here in real-time.
            </p>
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="flex gap-2 items-start hover:bg-slate-800/50 -mx-2 px-2 py-0.5 rounded">
              <span className="text-slate-600 shrink-0">[{log.time}]</span>
              {log.pair && (
                <span className="text-slate-400 shrink-0">[{log.pair}]</span>
              )}
              <span className={`shrink-0 ${logTypeColors[log.type] || 'text-slate-400'}`}>
                {logTypeIcons[log.type] || '●'} {log.type}:
              </span>
              <span className="text-slate-300 break-words">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default ActivityLog
