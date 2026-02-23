const variants = {
  active: 'bg-accent-green/10 text-accent-green',
  retest: 'bg-amber-500/10 text-amber-500',
  waiting: 'bg-slate-200 dark:bg-white/10 text-slate-500 dark:text-[#92adc9]',
  win: 'bg-emerald-500/10 text-emerald-500',
  loss: 'bg-rose-500/10 text-rose-500',
  buy: 'bg-blue-100 text-blue-700 dark:bg-primary/20 dark:text-primary',
  sell: 'bg-orange-100 text-orange-700 dark:bg-orange-900/20 dark:text-orange-400',
}

function Badge({ variant = 'active', children, icon, pulse = false }) {
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold ${variants[variant]}`}>
      {pulse && <span className="w-2 h-2 rounded-full bg-current animate-pulse"></span>}
      {icon && <span className="material-symbols-outlined text-[14px]">{icon}</span>}
      {children}
    </div>
  )
}

export default Badge
