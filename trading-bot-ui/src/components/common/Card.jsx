function Card({ children, className = '' }) {
  return (
    <div className={`rounded-xl bg-white dark:bg-[#192633] border border-slate-200 dark:border-[#233648] shadow-sm ${className}`}>
      {children}
    </div>
  )
}

export default Card
