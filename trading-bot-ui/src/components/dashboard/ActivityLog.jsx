import { useEffect, useRef } from 'react'

const logTypeColors = {
  SUCCESS: 'text-accent-green',
  INFO: 'text-primary',
  WARNING: 'text-amber-400',
  SYSTEM: 'text-cyan-400',
  ALERT: 'text-accent-red',
}

const logTypeIcons = {
  SUCCESS: '✓',
  INFO: '●',
  WARNING: '⚠',
  SYSTEM: '⚙',
  ALERT: '!',
}

function ActivityLog({ logs, onClear }) {
  const logContainerRef = useRef(null)

  // Auto-scroll to top when new logs are added
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = 0
    }
  }, [logs.length])

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between px-2">
        <h3 className="text-sm font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-widest flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">terminal</span>
          Activity Log
          {logs.length > 0 && (
            <span className="text-xs font-normal text-slate-400">({logs.length})</span>
          )}
        </h3>
        <button 
          onClick={onClear} 
          className="text-xs font-bold text-primary hover:text-primary/80 disabled:opacity-50"
          disabled={logs.length === 0}
        >
          Clear logs
        </button>
      </div>
      <div 
        ref={logContainerRef}
        className="bg-slate-900 rounded-xl p-4 font-mono text-xs border border-slate-800 shadow-xl max-h-64 overflow-y-auto activity-log space-y-1.5"
      >
        {logs.length === 0 ? (
          <div className="text-slate-500 text-center py-4">
            No activity yet. Start the bot to see logs here.
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="flex gap-2 items-start">
              <span className="text-slate-600 shrink-0">[{log.time}]</span>
              <span className={`shrink-0 ${logTypeColors[log.type]}`}>
                {logTypeIcons[log.type]} {log.type}:
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
