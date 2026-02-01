import { useEffect, useRef, useState } from 'react'
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

const LOG_TYPES = ['SYSTEM', 'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'TRADE', 'SIGNAL']

function ActivityLog({ logs, onClear, isExpanded = false, onToggleExpand }) {
  const logContainerRef = useRef(null)
  const { sseConnected } = useApp()
  const [showFilterMenu, setShowFilterMenu] = useState(false)
  const [activeFilters, setActiveFilters] = useState(() => {
    // All types enabled by default
    const filters = {}
    LOG_TYPES.forEach(type => filters[type] = true)
    return filters
  })

  const toggleFilter = (type) => {
    setActiveFilters(prev => ({ ...prev, [type]: !prev[type] }))
  }

  const filteredLogs = logs.filter(log => activeFilters[log.type] !== false)
  const activeFilterCount = Object.values(activeFilters).filter(Boolean).length

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
            <span className="text-xs font-normal text-slate-400">
              ({filteredLogs.length}{filteredLogs.length !== logs.length ? `/${logs.length}` : ''})
            </span>
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
          {/* Filter Dropdown */}
          <div className="relative">
            <button
              onClick={() => setShowFilterMenu(!showFilterMenu)}
              className={`flex items-center gap-1 text-xs font-bold transition-colors ${
                activeFilterCount < LOG_TYPES.length 
                  ? 'text-amber-500 hover:text-amber-400' 
                  : 'text-slate-400 hover:text-slate-300'
              }`}
              title="Filter log types"
            >
              <span className="material-symbols-outlined text-[16px]">filter_list</span>
              Filter
              {activeFilterCount < LOG_TYPES.length && (
                <span className="text-[10px]">({activeFilterCount})</span>
              )}
            </button>
            {showFilterMenu && (
              <>
                <div 
                  className="fixed inset-0 z-40" 
                  onClick={() => setShowFilterMenu(false)}
                />
                <div className="absolute right-0 top-6 z-50 bg-slate-800 border border-slate-700 rounded-lg shadow-xl p-2 min-w-[140px]">
                  {LOG_TYPES.map(type => (
                    <label
                      key={type}
                      className="flex items-center gap-2 px-2 py-1.5 hover:bg-slate-700 rounded cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={activeFilters[type]}
                        onChange={() => toggleFilter(type)}
                        className="w-3.5 h-3.5 rounded text-primary bg-slate-900 border-slate-600 focus:ring-primary focus:ring-offset-0"
                      />
                      <span className={`text-xs font-medium ${logTypeColors[type]}`}>
                        {logTypeIcons[type]} {type}
                      </span>
                    </label>
                  ))}
                </div>
              </>
            )}
          </div>
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
        {filteredLogs.length === 0 ? (
          <div className="text-slate-500 text-center py-4">
            {logs.length === 0 ? (
              <>
                <p>No activity yet.</p>
                <p className="text-slate-600 text-[10px] mt-1">
                  Logs from the Python bot will appear here in real-time.
                </p>
              </>
            ) : (
              <>
                <p>No logs match current filters.</p>
                <p className="text-slate-600 text-[10px] mt-1">
                  Adjust filters to see {logs.length} hidden log{logs.length !== 1 ? 's' : ''}.
                </p>
              </>
            )}
          </div>
        ) : (
          filteredLogs.map((log) => (
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
