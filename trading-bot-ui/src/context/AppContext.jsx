import { createContext, useContext, useState, useEffect } from 'react'

const AppContext = createContext()

export function AppProvider({ children }) {
  // Theme management
  const [isDarkMode, setIsDarkMode] = useState(() => {
    // Check localStorage or default to dark
    const saved = localStorage.getItem('theme')
    return saved ? saved === 'dark' : true
  })

  // Apply theme class to HTML element
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }, [isDarkMode])

  const toggleTheme = () => setIsDarkMode(!isDarkMode)

  // Sidebar state
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen)

  const [isSimulationMode, setIsSimulationMode] = useState(true)
  const [botStatus, setBotStatus] = useState('stopped') // 'running' | 'stopped'
  const [activeTrades, setActiveTrades] = useState([
    { id: 1, pair: 'EUR/USD', status: 'active', direction: 'LONG', entryPrice: 1.08422, riskReward: '1:3.5' },
    { id: 2, pair: 'GBP/JPY', status: 'retest', direction: 'SHORT', entryPrice: 182.155, riskReward: '1:2.0' },
    { id: 3, pair: 'USD/CAD', status: 'active', direction: 'LONG', entryPrice: 1.35201, riskReward: '1:4.2' },
    { id: 4, pair: 'AUD/USD', status: 'waiting', direction: 'SHORT', entryPrice: 0.65408, riskReward: '1:2.5' },
  ])
  
  const [activityLogs, setActivityLogs] = useState([
    { id: 1, time: '14:22:01', type: 'SUCCESS', message: 'EUR/USD Long entry executed at 1.08422. TP set at 1.09100.' },
    { id: 2, time: '14:21:45', type: 'INFO', message: 'RSI oversold condition met for EUR/USD on 15m timeframe.' },
    { id: 3, time: '14:15:30', type: 'WARNING', message: 'GBP/JPY price approaching retest zone (182.15). Monitoring for reversal signals.' },
    { id: 4, time: '14:00:12', type: 'SYSTEM', message: 'Trading bot heart-beat active. Connection to API stable.' },
    { id: 5, time: '13:58:45', type: 'ALERT', message: 'Trailing stop-loss hit for USD/JPY. Trade closed with +15 pips.' },
  ])

  const [stats, setStats] = useState({
    activeTrades: 12,
    waitingRetest: 4,
    todayProfit: 1420.50,
    activeTrendup: '+2.4%',
    retestTrend: '-5.1%',
    winRateBoost: '14.2%'
  })

  const startBot = () => setBotStatus('running')
  const stopBot = () => setBotStatus('stopped')
  const toggleMode = () => setIsSimulationMode(!isSimulationMode)
  
  const addLog = (type, message) => {
    const now = new Date()
    const time = now.toTimeString().slice(0, 8)
    setActivityLogs(prev => [{ id: Date.now(), time, type, message }, ...prev])
  }

  const value = {
    isDarkMode,
    toggleTheme,
    isSidebarOpen,
    toggleSidebar,
    isSimulationMode,
    setIsSimulationMode,
    toggleMode,
    botStatus,
    startBot,
    stopBot,
    activeTrades,
    setActiveTrades,
    activityLogs,
    addLog,
    stats
  }

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const context = useContext(AppContext)
  if (!context) {
    throw new Error('useApp must be used within AppProvider')
  }
  return context
}
