import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const AppContext = createContext()

// API URL - change this if backend runs on different port
const API_URL = 'http://localhost:5001'

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
  const [activeTrades, setActiveTrades] = useState([])
  const [isLoadingTrades, setIsLoadingTrades] = useState(true)
  
  const [activityLogs, setActivityLogs] = useState([])

  const [stats, setStats] = useState({
    activeTrades: 0,
    waitingRetest: 0,
    todayProfit: 0,
    activeTrendup: '-',
    retestTrend: '-',
    winRateBoost: '-'
  })

  // Fetch active trades from API
  const fetchTrades = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/trades/active`)
      const data = await response.json()
      if (data.trades) {
        setActiveTrades(data.trades)
      }
    } catch (error) {
      console.error('Error fetching trades:', error)
    } finally {
      setIsLoadingTrades(false)
    }
  }, [])

  // Fetch stats from API
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/trades/stats`)
      const data = await response.json()
      setStats(prev => ({
        ...prev,
        activeTrades: data.activeTrades || 0,
        waitingRetest: data.waitingRetest || 0,
        todayProfit: data.todayProfit || 0,
        winRateBoost: data.winRate ? `${data.winRate}%` : '-'
      }))
    } catch (error) {
      console.error('Error fetching stats:', error)
    }
  }, [])

  // Load data on mount
  useEffect(() => {
    fetchTrades()
    fetchStats()
  }, [fetchTrades, fetchStats])

  // Refresh data periodically when bot is running
  useEffect(() => {
    if (botStatus === 'running') {
      const refreshInterval = setInterval(() => {
        fetchTrades()
        fetchStats()
      }, 10000) // Refresh every 10 seconds
      
      return () => clearInterval(refreshInterval)
    }
  }, [botStatus, fetchTrades, fetchStats])

  const [botInterval, setBotInterval] = useState(null)

  const addLog = (type, message) => {
    const now = new Date()
    const time = now.toTimeString().slice(0, 8)
    setActivityLogs(prev => [{ id: Date.now(), time, type, message }, ...prev])
  }

  const clearLogs = () => {
    setActivityLogs([])
  }

  // Simulated bot activities
  const simulatedActivities = [
    { type: 'INFO', message: 'Scanning EUR/USD for entry signals on M15 timeframe...' },
    { type: 'INFO', message: 'Analyzing GBP/JPY support/resistance zones...' },
    { type: 'INFO', message: 'Checking USD/CAD Kijun-sen alignment on H4...' },
    { type: 'INFO', message: 'Monitoring AUD/USD for retest confirmation...' },
    { type: 'INFO', message: 'Fetching price history from FXCM API...' },
    { type: 'INFO', message: 'Calculating risk/reward for potential entries...' },
    { type: 'WARNING', message: 'EUR/USD approaching daily resistance zone at 1.0890' },
    { type: 'WARNING', message: 'GBP/JPY volatility increasing, widening stop-loss buffer' },
    { type: 'INFO', message: 'USD/JPY: No valid setup found, continuing scan...' },
    { type: 'INFO', message: 'Checking open positions for trailing stop adjustment...' },
    { type: 'SUCCESS', message: 'EUR/USD: Bullish engulfing pattern detected on M15' },
    { type: 'INFO', message: 'Validating entry conditions against strategy rules...' },
    { type: 'SYSTEM', message: 'Heartbeat: Connection to FXCM API stable' },
    { type: 'INFO', message: 'NZD/USD: Waiting for price to reach 78.6% Fibonacci level' },
    { type: 'WARNING', message: 'AUD/JPY: Risk/reward below minimum threshold (1:1.8)' },
  ]

  const startBot = async () => {
    setBotStatus('running')
    addLog('SYSTEM', 'Trading bot starting...')
    
    // Simulate connection
    setTimeout(() => {
      addLog('SUCCESS', 'Connected to FXCM API successfully')
      addLog('INFO', `Mode: ${isSimulationMode ? 'SIMULATION' : 'LIVE TRADING'}`)
      addLog('INFO', 'Loading active currency pairs configuration...')
    }, 500)

    setTimeout(() => {
      addLog('SUCCESS', 'Bot initialized. Starting market scan...')
    }, 1500)

    // Start periodic activity simulation
    const interval = setInterval(() => {
      const randomActivity = simulatedActivities[Math.floor(Math.random() * simulatedActivities.length)]
      addLog(randomActivity.type, randomActivity.message)
    }, 5000) // Every 5 seconds

    setBotInterval(interval)
  }

  const stopBot = () => {
    // Clear the interval
    if (botInterval) {
      clearInterval(botInterval)
      setBotInterval(null)
    }
    
    addLog('WARNING', 'Stop signal received...')
    
    setTimeout(() => {
      addLog('INFO', 'Closing open connections...')
    }, 300)
    
    setTimeout(() => {
      addLog('SYSTEM', 'Trading bot stopped successfully')
      setBotStatus('stopped')
    }, 800)
  }

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (botInterval) {
        clearInterval(botInterval)
      }
    }
  }, [botInterval])

  const toggleMode = () => setIsSimulationMode(!isSimulationMode)

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
    isLoadingTrades,
    activityLogs,
    addLog,
    clearLogs,
    stats,
    fetchTrades,
    fetchStats
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
