function ModeToggle({ isSimulation, onToggle }) {
  return (
    <div className="flex bg-slate-100 dark:bg-[#233648] p-1 rounded-xl w-64 h-11 shadow-inner">
      <label className={`flex cursor-pointer h-full grow items-center justify-center rounded-lg px-2 text-sm font-bold transition-all ${
        !isSimulation 
          ? 'bg-white dark:bg-background-dark text-primary shadow-sm' 
          : 'text-slate-500 dark:text-[#92adc9]'
      }`}>
        <span className="truncate">Live Mode</span>
        <input
          type="radio"
          name="mode-toggle"
          value="live"
          checked={!isSimulation}
          onChange={onToggle}
          className="hidden"
        />
      </label>
      <label className={`flex cursor-pointer h-full grow items-center justify-center rounded-lg px-2 text-sm font-bold transition-all ${
        isSimulation 
          ? 'bg-white dark:bg-background-dark text-primary shadow-sm' 
          : 'text-slate-500 dark:text-[#92adc9]'
      }`}>
        <span className="truncate">Simulation</span>
        <input
          type="radio"
          name="mode-toggle"
          value="simulation"
          checked={isSimulation}
          onChange={onToggle}
          className="hidden"
        />
      </label>
    </div>
  )
}

export default ModeToggle
