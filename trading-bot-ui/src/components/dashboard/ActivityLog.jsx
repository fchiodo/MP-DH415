const logTypeColors = {
  SUCCESS: 'text-accent-green',
  INFO: 'text-primary',
  WARNING: 'text-amber-400',
  SYSTEM: 'text-primary',
  ALERT: 'text-accent-red',
}

function ActivityLog({ logs, onClear }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between px-2">
        <h3 className="text-sm font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-widest flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">terminal</span>
          Activity Log
        </h3>
        <button onClick={onClear} className="text-xs font-bold text-primary hover:text-primary/80">
          Clear logs
        </button>
      </div>
      <div className="bg-slate-900 rounded-xl p-4 font-mono text-sm border border-slate-800 shadow-xl max-h-48 overflow-y-auto activity-log space-y-2">
        {logs.map((log) => (
          <div key={log.id} className="flex gap-4">
            <span className="text-slate-500">[{log.time}]</span>
            <span className={logTypeColors[log.type]}>{log.type}:</span>
            <span className="text-slate-300">{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ActivityLog
