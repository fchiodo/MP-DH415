import { useState } from 'react'

function StatsCard({ title, value, icon, iconColor = 'text-primary', trend, trendUp = true, subtitle, tooltip }) {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div className="flex flex-col gap-2 rounded-xl p-6 bg-white dark:bg-[#192633] border border-slate-200 dark:border-[#233648] shadow-sm">
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-1.5">
          <p className="text-slate-500 dark:text-[#92adc9] text-sm font-semibold uppercase tracking-wider">{title}</p>
          {tooltip && (
            <div className="relative">
              <button
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
                onClick={() => setShowTooltip(!showTooltip)}
                className="text-slate-400 hover:text-primary transition-colors"
              >
                <span className="material-symbols-outlined text-[16px]">info</span>
              </button>
              {showTooltip && (
                <div className="absolute left-0 top-full mt-2 z-50 w-64 p-3 rounded-lg shadow-xl 
                  bg-slate-800 dark:bg-slate-900 text-white text-xs leading-relaxed
                  border border-slate-700 animate-in fade-in duration-200">
                  <div className="absolute -top-1.5 left-3 w-3 h-3 bg-slate-800 dark:bg-slate-900 
                    border-l border-t border-slate-700 rotate-45"></div>
                  {tooltip}
                </div>
              )}
            </div>
          )}
        </div>
        {icon && <span className={`material-symbols-outlined ${iconColor}`}>{icon}</span>}
      </div>
      <p className={`tracking-tight text-4xl font-extrabold ${trendUp ? 'text-slate-900 dark:text-white' : ''}`}>{value}</p>
      {trend && (
        <div className="flex items-center gap-1">
          <span className={`material-symbols-outlined text-[18px] ${trendUp ? 'text-accent-green' : 'text-accent-red'}`}>
            {trendUp ? 'trending_up' : 'trending_down'}
          </span>
          <p className={`text-sm font-bold ${trendUp ? 'text-accent-green' : 'text-accent-red'}`}>{trend}</p>
        </div>
      )}
      {subtitle && <p className="text-xs text-slate-400 font-bold">{subtitle}</p>}
    </div>
  )
}

export default StatsCard
