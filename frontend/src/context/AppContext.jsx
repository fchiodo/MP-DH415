import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'

const AppContext = createContext()

// API URL - change this if backend runs on different port
const API_URL = 'http://localhost:5001'

export function AppProvider({ children }) {
  // Theme management
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('theme')
    return saved ? saved === 'dark' : true
  })

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

  // Bot state
  const [isSimulationMode, setIsSimulationMode] = useState(true)
  const [botStatus, setBotStatus] = useState('stopped')
  const [activeTrades, setActiveTrades] = useState([])
  const [isLoadingTrades, setIsLoadingTrades] = useState(true)
  
  // Activity Logs - Real-time via SSE
  const [activityLogs, setActivityLogs] = useState([])
  const [sseConnected, setSseConnected] = useState(false)
  const [includeDebugLogs, setIncludeDebugLogsState] = useState(false)
  const eventSourceRef = useRef(null)
  const includeDebugRef = useRef(false) // Ref to access current value in callbacks

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

  // Fetch initial logs from API - merges with existing logs to avoid losing any
  const fetchLogs = useCallback(async (includeDebug = false) => {
    try {
      const debugParam = includeDebug ? '&include_debug=true' : ''
      const response = await fetch(`${API_URL}/api/logs?limit=500${debugParam}`)
      const data = await response.json()
      if (data.logs) {
        // Transform to UI format
        const formattedLogs = data.logs.map(log => ({
          id: log.id,
          time: log.timestamp ? log.timestamp.split(' ')[1] || log.timestamp : '',
          type: log.type,
          message: log.message,
          pair: log.pair
        }))
        // Merge with existing logs to avoid losing any
        setActivityLogs(prev => {
          const existingIds = new Set(prev.map(l => l.id))
          const newLogs = formattedLogs.filter(l => !existingIds.has(l.id))
          // Combine and sort by id descending (newest first)
          const combined = [...prev, ...newLogs]
          combined.sort((a, b) => b.id - a.id)
          return combined.slice(0, 500)
        })
      }
    } catch (error) {
      console.error('Error fetching logs:', error)
    }
  }, [])

  // Connect to SSE for real-time logs
  const connectSSE = useCallback((includeDebug = false) => {
    // Close existing connection if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    const debugParam = includeDebug ? '?include_debug=true' : ''
    console.log('[SSE] Connecting to log stream...', includeDebug ? '(with debug logs)' : '')
    const eventSource = new EventSource(`${API_URL}/api/logs/stream${debugParam}`)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      console.log('[SSE] Connected to log stream')
      setSseConnected(true)
    }

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        // Handle connection message
        if (data.type === 'connected') {
          console.log('[SSE] Stream initialized, lastId:', data.lastId)
          return
        }
        
        // Handle new log
        if (data.id && data.message) {
          const newLog = {
            id: data.id,
            time: data.timestamp ? data.timestamp.split(' ')[1] || data.timestamp : '',
            type: data.type,
            message: data.message,
            pair: data.pair
          }
          
          setActivityLogs(prev => {
            // Avoid duplicates
            if (prev.some(log => log.id === newLog.id)) {
              return prev
            }
            // Add new log at the beginning
            return [newLog, ...prev].slice(0, 500) // Keep max 500 logs
          })
        }
      } catch (e) {
        console.error('[SSE] Error parsing message:', e)
      }
    }

    eventSource.onerror = (error) => {
      console.error('[SSE] Connection error:', error)
      setSseConnected(false)
      eventSource.close()
      
      // Reconnect after 3 seconds and refetch logs to catch any missed during disconnect
      setTimeout(() => {
        console.log('[SSE] Reconnecting...')
        fetchLogs(includeDebugRef.current)
        connectSSE(includeDebugRef.current)
      }, 3000)
    }

    return eventSource
  }, [])

  // Check bot status from API
  const checkBotStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/bot/status`)
      const data = await response.json()
      if (data.status === 'running' && botStatus !== 'running') {
        setBotStatus('running')
      } else if (data.status === 'stopped' && botStatus === 'running') {
        setBotStatus('stopped')
      }
    } catch (error) {
      console.error('Error checking bot status:', error)
    }
  }, [botStatus])

  // Load data on mount (run only once)
  useEffect(() => {
    fetchTrades()
    fetchStats()
    fetchLogs()
    checkBotStatus()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Connect SSE on mount
  useEffect(() => {
    const eventSource = connectSSE()
    
    return () => {
      if (eventSource) {
        eventSource.close()
      }
    }
  }, [connectSSE])

  // Check bot status periodically
  useEffect(() => {
    const statusInterval = setInterval(checkBotStatus, 5000)
    return () => clearInterval(statusInterval)
  }, [checkBotStatus])

  // Refresh data periodically when bot is running
  useEffect(() => {
    if (botStatus === 'running') {
      const refreshInterval = setInterval(() => {
        fetchTrades()
        fetchStats()
      }, 10000)
      
      return () => clearInterval(refreshInterval)
    }
  }, [botStatus, fetchTrades, fetchStats])

  // Add log to database via API
  const addLog = useCallback(async (type, message, pair = null) => {
    try {
      await fetch(`${API_URL}/api/logs/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, message, pair })
      })
    } catch (error) {
      console.error('Error adding log:', error)
      // Fallback: add locally if API fails
      const now = new Date()
      const time = now.toTimeString().slice(0, 8)
      setActivityLogs(prev => [{ id: Date.now(), time, type, message, pair }, ...prev])
    }
  }, [])

  // Clear logs via API
  const clearLogs = useCallback(async () => {
    try {
      await fetch(`${API_URL}/api/logs/clear`, { method: 'POST' })
      setActivityLogs([])
    } catch (error) {
      console.error('Error clearing logs:', error)
      setActivityLogs([])
    }
  }, [])

  // Start bot - calls the real Python bot
  const startBot = useCallback(async () => {
    if (botStatus === 'running') return
    
    try {
      const response = await fetch(`${API_URL}/api/bot/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      })
      
      const data = await response.json()
      
      if (data.success) {
        setBotStatus('running')
        console.log('Bot started, PID:', data.pid)
      } else {
        console.error('Failed to start bot:', data.error)
        // Add error log locally
        const now = new Date()
        const time = now.toTimeString().slice(0, 8)
        setActivityLogs(prev => [{ id: Date.now(), time, type: 'ERROR', message: `Failed to start bot: ${data.error}` }, ...prev])
      }
    } catch (error) {
      console.error('Error starting bot:', error)
      const now = new Date()
      const time = now.toTimeString().slice(0, 8)
      setActivityLogs(prev => [{ id: Date.now(), time, type: 'ERROR', message: `Connection error: ${error.message}` }, ...prev])
    }
  }, [botStatus])

  // Stop bot - stops the real Python bot
  const stopBot = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/bot/stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      
      const data = await response.json()
      
      if (data.success) {
        setBotStatus('stopped')
        console.log('Bot stopped')
      } else {
        console.error('Failed to stop bot:', data.error)
      }
    } catch (error) {
      console.error('Error stopping bot:', error)
    }
  }, [])

  const toggleMode = () => setIsSimulationMode(!isSimulationMode)

  // Toggle debug logs (TRADER type) - refetches and reconnects SSE
  const setIncludeDebugLogs = useCallback((include) => {
    console.log('[Logs] Setting include debug logs:', include)
    setIncludeDebugLogsState(include)
    includeDebugRef.current = include
    
    // Clear current logs and refetch with new setting
    setActivityLogs([])
    fetchLogs(include)
    
    // Reconnect SSE with new setting
    connectSSE(include)
  }, [fetchLogs, connectSSE])

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
    sseConnected,
    includeDebugLogs,
    setIncludeDebugLogs,
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
