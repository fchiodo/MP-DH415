import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'

const AppContext = createContext()

// API URL - change this if backend runs on different port
const API_URL = 'http://localhost:5001'

// Module-level flag to prevent double-start (survives re-renders and HMR)
let isBotStarting = false

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
  const [botTimeouts, setBotTimeouts] = useState([])
  const isStartingRef = useRef(false) // Immediate check to prevent double-start

  const addLog = (type, message) => {
    const now = new Date()
    const time = now.toTimeString().slice(0, 8)
    setActivityLogs(prev => [{ id: Date.now() + Math.random(), time, type, message }, ...prev])
  }

  const clearLogs = () => {
    setActivityLogs([])
  }

  // Clear all pending timeouts
  const clearBotTimeouts = () => {
    botTimeouts.forEach(t => clearTimeout(t))
    setBotTimeouts([])
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
    // Triple check: module-level flag, ref, and state
    if (isBotStarting || isStartingRef.current || botStatus === 'running') {
      console.log('Bot already starting or running, ignoring start request')
      return
    }
    
    // Set both flags immediately
    isBotStarting = true
    isStartingRef.current = true
    
    // Clear any existing interval and timeouts
    if (botInterval) {
      clearInterval(botInterval)
      setBotInterval(null)
    }
    clearBotTimeouts()
    
    setBotStatus('running')
    
    // Add all startup logs in a SINGLE state update to prevent batching issues
    const now = new Date()
    const time = now.toTimeString().slice(0, 8)
    const startupLogs = [
      { id: Date.now() + 4, time, type: 'SUCCESS', message: 'Bot initialized. Starting market scan...' },
      { id: Date.now() + 3, time, type: 'INFO', message: 'Loading active currency pairs configuration...' },
      { id: Date.now() + 2, time, type: 'INFO', message: `Mode: ${isSimulationMode ? 'SIMULATION' : 'LIVE TRADING'}` },
      { id: Date.now() + 1, time, type: 'SUCCESS', message: 'Connected to FXCM API successfully' },
      { id: Date.now(), time, type: 'SYSTEM', message: 'Trading bot starting...' },
    ]
    setActivityLogs(prev => [...startupLogs, ...prev])

    // Start periodic activity simulation after 3 seconds
    const timeout = setTimeout(() => {
      const interval = setInterval(() => {
        const randomActivity = simulatedActivities[Math.floor(Math.random() * simulatedActivities.length)]
        addLog(randomActivity.type, randomActivity.message)
      }, 5000) // Every 5 seconds
      
      setBotInterval(interval)
    }, 3000)
    
    setBotTimeouts([timeout])
  }

  const stopBot = () => {
    // Clear the interval and pending timeouts
    if (botInterval) {
      clearInterval(botInterval)
      setBotInterval(null)
    }
    clearBotTimeouts()
    
    // Reset all starting flags
    isBotStarting = false
    isStartingRef.current = false
    
    // Add stop logs synchronously
    addLog('WARNING', 'Stop signal received...')
    addLog('INFO', 'Closing open connections...')
    addLog('SYSTEM', 'Trading bot stopped successfully')
    setBotStatus('stopped')
  }

  // Cleanup interval and timeouts on unmount
  useEffect(() => {
    return () => {
      if (botInterval) {
        clearInterval(botInterval)
      }
      botTimeouts.forEach(t => clearTimeout(t))
    }
  }, [botInterval, botTimeouts])

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
