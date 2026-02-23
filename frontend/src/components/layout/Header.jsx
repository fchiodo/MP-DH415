import { useState, useEffect } from 'react'
import { useApp } from '../../context/AppContext'

function Header({ title, subtitle }) {
  const { botStatus, startBot, stopBot, isDarkMode, toggleTheme, toggleSidebar, isSidebarOpen } = useApp()
  const [isStarting, setIsStarting] = useState(false)
  const [isStopping, setIsStopping] = useState(false)

  // Reset isStopping when bot actually stops
  useEffect(() => {
    if (botStatus === 'stopped' && isStopping) {
      setIsStopping(false)
    }
  }, [botStatus, isStopping])

  const handleStart = async () => {
    if (isStarting || botStatus === 'running') return
    setIsStarting(true)
    await startBot()
    setTimeout(() => setIsStarting(false), 1000)
  }

  const handleStop = async () => {
    if (isStopping || botStatus === 'stopped') return
    setIsStopping(true)
    await stopBot()
  }

  return (
    <header className="flex items-center justify-between whitespace-nowrap border-b border-solid border-slate-200 dark:border-[#233648] px-6 py-4 bg-white dark:bg-background-dark sticky top-0 z-40">
      {/* Left: Hamburger + Page Title or Search */}
      <div className="flex items-center gap-4">
        {/* Hamburger Menu */}
        <button
          onClick={toggleSidebar}
          className="flex items-center justify-center rounded-lg h-10 w-10 bg-slate-100 dark:bg-[#233648] text-slate-600 dark:text-white hover:bg-slate-200 dark:hover:bg-[#324d67] transition-all"
          title={isSidebarOpen ? 'Close sidebar' : 'Open sidebar'}
        >
          <span className="material-symbols-outlined text-[22px]">
            {isSidebarOpen ? 'menu_open' : 'menu'}
          </span>
        </button>

        {title ? (
          <div>
            <h1 className="text-slate-900 dark:text-white text-xl font-bold">{title}</h1>
            {subtitle && <p className="text-slate-500 dark:text-[#92adc9] text-sm">{subtitle}</p>}
          </div>
        ) : (
          <label className="flex flex-col min-w-72 h-10">
            <div className="flex w-full flex-1 items-stretch rounded-lg h-full overflow-hidden">
              <div className="text-slate-400 dark:text-[#92adc9] flex border-none bg-slate-100 dark:bg-[#233648] items-center justify-center pl-4">
                <span className="material-symbols-outlined text-[20px]">search</span>
              </div>
              <input
                className="flex w-full min-w-0 flex-1 resize-none overflow-hidden text-slate-900 dark:text-white focus:outline-none focus:ring-0 border-none bg-slate-100 dark:bg-[#233648] h-full placeholder:text-slate-400 dark:placeholder:text-[#92adc9] px-4 pl-2 text-base font-normal"
                placeholder="Search pairs, trades..."
              />
            </div>
          </label>
        )}
      </div>
      
      {/* Right: Actions */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <button className="flex items-center justify-center rounded-lg h-10 w-10 bg-slate-100 dark:bg-[#233648] text-slate-600 dark:text-white hover:bg-slate-200 dark:hover:bg-[#324d67] transition-all relative">
          <span className="material-symbols-outlined text-[20px]">notifications</span>
          <span className="absolute top-2 right-2 size-2 bg-accent-red rounded-full"></span>
        </button>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="flex items-center justify-center rounded-lg h-10 w-10 bg-slate-100 dark:bg-[#233648] text-slate-600 dark:text-white hover:bg-slate-200 dark:hover:bg-[#324d67] transition-all"
          title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          <span className="material-symbols-outlined text-[20px]">
            {isDarkMode ? 'light_mode' : 'dark_mode'}
          </span>
        </button>

        <div className="h-8 w-px bg-slate-200 dark:bg-[#233648]"></div>
        
        {/* Bot Controls */}
        <div className="flex gap-2">
          <button
            onClick={handleStart}
            disabled={isStarting || botStatus === 'running'}
            className={`flex items-center justify-center gap-2 rounded-lg h-10 px-4 text-sm font-bold transition-all ${
              botStatus === 'running'
                ? 'bg-accent-green/20 text-accent-green cursor-default'
                : isStarting
                ? 'bg-primary/50 text-white cursor-wait'
                : 'bg-primary text-white hover:bg-primary/90 shadow-lg shadow-primary/20'
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">
              {botStatus === 'running' ? 'radio_button_checked' : isStarting ? 'hourglass_empty' : 'play_arrow'}
            </span>
            <span>{botStatus === 'running' ? 'Running' : isStarting ? 'Starting...' : 'Start'}</span>
          </button>
          <button
            onClick={handleStop}
            disabled={isStopping || botStatus === 'stopped'}
            className={`flex items-center justify-center rounded-lg h-10 w-10 transition-all ${
              isStopping 
                ? 'bg-red-500/20 text-red-500 cursor-wait'
                : 'bg-slate-100 dark:bg-[#233648] text-slate-600 dark:text-white hover:bg-red-500/10 hover:text-red-500 disabled:opacity-50 disabled:hover:bg-slate-100 disabled:hover:text-slate-600 dark:disabled:hover:bg-[#233648] dark:disabled:hover:text-white'
            }`}
          >
            <span className={`material-symbols-outlined text-[18px] ${isStopping ? 'animate-spin' : ''}`}>
              {isStopping ? 'progress_activity' : 'stop'}
            </span>
          </button>
        </div>
      </div>
    </header>
  )
}

export default Header
