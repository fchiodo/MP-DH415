import { useState, useEffect, useCallback } from 'react'
import StatsCard from '../components/common/StatsCard'
import Button from '../components/common/Button'

const API_URL = 'http://localhost:5001'

function Simulation() {
  const [signals, setSignals] = useState([])
  const [modifications, setModifications] = useState([])
  const [closures, setClosures] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState(null)

  // Fetch simulation data from API
  const fetchSignals = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/signals`)
      const data = await response.json()
      
      if (data.signals) setSignals(data.signals)
      if (data.modifications) setModifications(data.modifications)
      if (data.closures) setClosures(data.closures)
      setLastUpdate(new Date())
    } catch (error) {
      console.error('Error fetching signals:', error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Clear all logs
  const clearLogs = async () => {
    try {
      await fetch(`${API_URL}/api/signals/clear`, { method: 'POST' })
      setSignals([])
      setModifications([])
      setClosures([])
    } catch (error) {
      console.error('Error clearing signals:', error)
    }
  }

  // Load data on mount and refresh every 5 seconds
  useEffect(() => {
    fetchSignals()
    const interval = setInterval(fetchSignals, 5000)
    return () => clearInterval(interval)
  }, [fetchSignals])

  // Format time ago
  const getTimeAgo = () => {
    if (!lastUpdate) return 'Never'
    const seconds = Math.floor((new Date() - lastUpdate) / 1000)
    if (seconds < 5) return 'Just now'
    if (seconds < 60) return `${seconds}s ago`
    return `${Math.floor(seconds / 60)}m ago`
  }

  const getOrderTypeBadge = (type) => {
    const isBuy = type.includes('BUY')
    return (
      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
        isBuy
          ? 'bg-blue-100 text-blue-700 dark:bg-primary/20 dark:text-primary'
          : 'bg-orange-100 text-orange-700 dark:bg-orange-900/20 dark:text-orange-400'
      }`}>
        {type}
      </span>
    )
  }

  const getChangeBadgeColor = (type) => {
    if (type.includes('Trailing')) return 'bg-green-500/10 dark:bg-green-500/20 text-green-500'
    if (type.includes('Breakeven')) return 'bg-blue-500/10 dark:bg-blue-500/20 text-blue-500'
    return 'bg-primary/10 dark:bg-primary/20 text-primary'
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex flex-wrap justify-between items-end gap-4">
        <div className="flex flex-col gap-2">
          <h1 className="text-slate-900 dark:text-white text-2xl font-extrabold leading-tight">
            Simulation Signal Log
          </h1>
          <p className="text-slate-500 dark:text-[#92adc9] text-sm font-normal">
            Tracking hypothetical order flow and SL/TP modifications for strategy verification.
          </p>
        </div>
        <Button variant="secondary" icon="delete_sweep" onClick={clearLogs}>Clear All Logs</Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatsCard
          title="Pending Signals"
          value={isLoading ? '...' : signals.length}
          icon="schedule"
          iconColor="text-primary"
          subtitle="MT5 orders queued"
          tooltip="Number of trading signals that would be sent to MetaTrader 5. In simulation mode, these are logged to the database instead of executing real trades."
        />
        <StatsCard
          title="Modifications"
          value={isLoading ? '...' : modifications.length}
          icon="edit_note"
          iconColor="text-primary"
          subtitle="SL/TP changes logged"
          tooltip="Stop Loss and Take Profit modifications that would be applied to open positions. Includes trailing stops and breakeven adjustments."
        />
        <StatsCard
          title="Closures"
          value={isLoading ? '...' : closures.length}
          icon="cancel"
          iconColor="text-primary"
          subtitle="Positions closed"
          tooltip="Orders and positions that would be closed or cancelled. This includes profit target hits, stop loss triggers, and manual closures."
        />
      </div>

      {/* Pending Signals Table */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-slate-900 dark:text-white text-xl font-bold tracking-tight flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">list_alt</span>
            Pending Signals (MT5 Orders)
          </h2>
          <span className="text-xs font-mono text-slate-500 dark:text-[#92adc9] uppercase">Updated {getTimeAgo()}</span>
        </div>
        <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-[#324d67] bg-white dark:bg-[#192633]">
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-50 dark:bg-[#1a2733] border-b border-slate-200 dark:border-[#324d67]">
              <tr>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Timestamp</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Pair</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Direction</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Entry</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">SL</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">TP</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">R:R</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-[#233648]">
              {isLoading ? (
                <tr>
                  <td colSpan="8" className="px-4 py-8 text-center text-slate-500">
                    <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span>
                    Loading signals...
                  </td>
                </tr>
              ) : signals.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-4 py-8 text-center text-slate-500">
                    <div className="flex flex-col items-center gap-2">
                      <span className="material-symbols-outlined text-3xl opacity-50">inbox</span>
                      <span>No pending signals</span>
                      <span className="text-xs">Signals will appear here when the bot generates MT5 orders in simulation mode</span>
                    </div>
                  </td>
                </tr>
              ) : (
                signals.map((signal) => {
                  const isLong = signal.order_type?.includes('BUY')
                  const direction = isLong ? 'LONG' : 'SHORT'
                  // Calculate R:R from price, SL, TP
                  const rr = signal.price && signal.stop_loss && signal.take_profit
                    ? Math.abs((signal.take_profit - signal.price) / (signal.price - signal.stop_loss)).toFixed(2)
                    : '-'
                  return (
                    <tr key={signal.id} className="hover:bg-slate-50 dark:hover:bg-[#16232e] transition-colors">
                      <td className="px-4 py-4 text-sm font-mono text-slate-500 dark:text-slate-400">{signal.timestamp}</td>
                      <td className="px-4 py-4 text-sm font-bold text-slate-900 dark:text-white">{signal.pair || signal.symbol}</td>
                      <td className="px-4 py-4 text-sm">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          isLong
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400'
                            : 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400'
                        }`}>
                          {direction}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-sm">
                        <span className="px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400">
                          {signal.status || signal.action || 'PENDING'}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-sm font-mono text-slate-900 dark:text-white">{signal.price || '-'}</td>
                      <td className="px-4 py-4 text-sm font-mono text-red-500">{signal.stop_loss || '-'}</td>
                      <td className="px-4 py-4 text-sm font-mono text-emerald-500">{signal.take_profit || '-'}</td>
                      <td className="px-4 py-4 text-sm font-mono font-bold text-primary">{rr}</td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* SL/TP Modifications Table */}
      <div className="flex flex-col gap-3">
        <h2 className="text-slate-900 dark:text-white text-xl font-bold tracking-tight flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">edit_square</span>
          SL/TP Modifications
        </h2>
        <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-[#324d67] bg-white dark:bg-[#192633]">
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-50 dark:bg-[#1a2733] border-b border-slate-200 dark:border-[#324d67]">
              <tr>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Timestamp</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Ticket</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Symbol</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Type</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">New SL</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">New TP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-[#233648]">
              {isLoading ? (
                <tr>
                  <td colSpan="6" className="px-4 py-8 text-center text-slate-500">
                    <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span>
                    Loading...
                  </td>
                </tr>
              ) : modifications.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-4 py-8 text-center text-slate-500">
                    <div className="flex flex-col items-center gap-2">
                      <span className="material-symbols-outlined text-3xl opacity-50">edit_off</span>
                      <span>No modifications logged</span>
                      <span className="text-xs">SL/TP changes will appear here when trailing stops or breakeven are triggered</span>
                    </div>
                  </td>
                </tr>
              ) : (
                modifications.map((mod) => (
                  <tr key={mod.id} className="hover:bg-slate-50 dark:hover:bg-[#16232e] transition-colors">
                    <td className="px-4 py-4 text-sm font-mono text-slate-500 dark:text-slate-400">{mod.timestamp}</td>
                    <td className="px-4 py-4 text-sm font-mono text-slate-900 dark:text-white">#{mod.ticket || mod.id}</td>
                    <td className="px-4 py-4 text-sm font-bold text-slate-900 dark:text-white">{mod.pair || mod.symbol}</td>
                    <td className="px-4 py-4 text-sm">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${getChangeBadgeColor(mod.modification_type || mod.type || '')}`}>
                        {mod.modification_type || mod.type || 'Update'}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-sm font-mono text-red-500">{mod.new_stop_loss || mod.stop_loss || '-'}</td>
                    <td className="px-4 py-4 text-sm font-mono text-green-500">{mod.new_take_profit || mod.take_profit || '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Closures Table */}
      <div className="flex flex-col gap-3">
        <h2 className="text-slate-900 dark:text-white text-xl font-bold tracking-tight flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">cancel</span>
          Position Closures
        </h2>
        <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-[#324d67] bg-white dark:bg-[#192633]">
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-50 dark:bg-[#1a2733] border-b border-slate-200 dark:border-[#324d67]">
              <tr>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Timestamp</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Pair</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Action</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Comment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-[#233648]">
              {isLoading ? (
                <tr>
                  <td colSpan="4" className="px-4 py-8 text-center text-slate-500">
                    <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span>
                    Loading...
                  </td>
                </tr>
              ) : closures.length === 0 ? (
                <tr>
                  <td colSpan="4" className="px-4 py-8 text-center text-slate-500">
                    <div className="flex flex-col items-center gap-2">
                      <span className="material-symbols-outlined text-3xl opacity-50">check_circle</span>
                      <span>No closures logged</span>
                      <span className="text-xs">Position closures will appear here when trades hit TP/SL or are manually closed</span>
                    </div>
                  </td>
                </tr>
              ) : (
                closures.map((closure) => (
                  <tr key={closure.id} className="hover:bg-slate-50 dark:hover:bg-[#16232e] transition-colors">
                    <td className="px-4 py-4 text-sm font-mono text-slate-500 dark:text-slate-400">{closure.timestamp}</td>
                    <td className="px-4 py-4 text-sm font-bold text-slate-900 dark:text-white">{closure.pair || closure.symbol || '-'}</td>
                    <td className="px-4 py-4 text-sm">
                      <span className="px-2 py-0.5 rounded text-xs font-bold bg-orange-100 text-orange-700 dark:bg-orange-900/20 dark:text-orange-400">
                        {closure.action || 'CLOSE'}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-sm text-slate-600 dark:text-slate-400">{closure.comment || '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer Status */}
      <div className="border-t border-slate-200 dark:border-[#233648] pt-6 flex flex-col md:flex-row justify-between items-center gap-4 text-slate-500 dark:text-[#92adc9]">
        <div className="flex items-center gap-4">
          <p className="text-xs">Mode: <span className="text-amber-500 font-bold uppercase">Simulation</span></p>
          <p className="text-xs">MT5 Status: <span className="text-slate-400 font-bold uppercase">Bypassed</span></p>
          <p className="text-xs">Last Refresh: <span className="text-slate-900 dark:text-white font-medium">{getTimeAgo()}</span></p>
        </div>
        <div className="flex gap-4">
          <button 
            onClick={fetchSignals}
            className="text-xs hover:text-primary transition-colors flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-[14px]">refresh</span>
            Refresh
          </button>
          <button 
            onClick={clearLogs}
            className="text-xs hover:text-red-500 transition-colors flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-[14px]">delete</span>
            Clear All
          </button>
        </div>
      </div>
    </div>
  )
}

export default Simulation
