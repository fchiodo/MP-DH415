function StatsCard({ title, value, icon, iconColor = 'text-primary', trend, trendUp = true, subtitle }) {
  return (
    <div className="flex flex-col gap-2 rounded-xl p-6 bg-white dark:bg-[#192633] border border-slate-200 dark:border-[#233648] shadow-sm">
      <div className="flex justify-between items-start">
        <p className="text-slate-500 dark:text-[#92adc9] text-sm font-semibold uppercase tracking-wider">{title}</p>
        <span className={`material-symbols-outlined ${iconColor}`}>{icon}</span>
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
