const variants = {
  primary: 'bg-primary text-white hover:bg-primary/90 shadow-lg shadow-primary/20',
  secondary: 'bg-slate-200 dark:bg-[#233648] text-slate-900 dark:text-white hover:bg-slate-300 dark:hover:bg-[#324d67]',
  danger: 'bg-red-600 hover:bg-red-700 text-white shadow-lg shadow-red-900/20',
  outline: 'border border-slate-300 dark:border-[#324d67] bg-white dark:bg-[#192633] text-slate-700 dark:text-white hover:bg-slate-100 dark:hover:bg-[#233648]',
}

function Button({ variant = 'primary', children, icon, className = '', ...props }) {
  return (
    <button
      className={`flex cursor-pointer items-center justify-center gap-2 rounded-lg h-10 px-4 text-sm font-bold transition-all ${variants[variant]} ${className}`}
      {...props}
    >
      {icon && <span className="material-symbols-outlined text-[18px]">{icon}</span>}
      {children}
    </button>
  )
}

export default Button
