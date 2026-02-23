import { useState, useCallback } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001'

export function useApi() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async (endpoint, options = {}) => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const getTrades = useCallback(() => fetchData('/api/trades'), [fetchData])
  const getSignals = useCallback(() => fetchData('/api/signals'), [fetchData])
  const getStats = useCallback(() => fetchData('/api/stats'), [fetchData])
  const getPerformance = useCallback(() => fetchData('/api/performance'), [fetchData])

  const startBot = useCallback(() => 
    fetchData('/api/bot/start', { method: 'POST' }), [fetchData])
  
  const stopBot = useCallback(() => 
    fetchData('/api/bot/stop', { method: 'POST' }), [fetchData])

  const updateSettings = useCallback((settings) => 
    fetchData('/api/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    }), [fetchData])

  return {
    loading,
    error,
    getTrades,
    getSignals,
    getStats,
    getPerformance,
    startBot,
    stopBot,
    updateSettings,
  }
}
