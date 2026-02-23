import { useState, useEffect, useCallback } from 'react'
import StatsCard from '../components/common/StatsCard'
import Button from '../components/common/Button'

const API_URL = 'http://localhost:5001'

function Performance() {
  const [activeTab, setActiveTab] = useState('all')
  const [timeFilter, setTimeFilter] = useState('all')
  const [isLoading, setIsLoading] = useState(true)
  
  // Data from API
  const [stats, setStats] = useState({
    totalTrades: 0,
    wins: 0,
    losses: 0,
    winRate: 0,
    avgRR: 0,
    totalProfitR: 0
  })
  const [recentTrades, setRecentTrades] = useState([])
  const [pairPerformance, setPairPerformance] = useState([])
  const [equityCurve, setEquityCurve] = useState([])

  const tabs = [
    { id: 'all', label: 'All Trades' },
    { id: 'long', label: 'Long Only' },
    { id: 'short', label: 'Short Only' },
  ]

  const timeFilters = [
    { id: 'all', label: 'All Time' },
    { id: '24h', label: 'Last 24h' },
    { id: '7d', label: 'Last 7d' },
    { id: 'month', label: 'Last Month' },
    { id: 'quarter', label: 'Last Quarter' },
    { id: 'ytd', label: 'Year to Date' },
  ]

  // Fetch performance data
  const fetchPerformance = useCallback(async () => {
    setIsLoading(true)
    try {
      const params = new URLSearchParams()
      if (timeFilter !== 'all') params.append('period', timeFilter)
      if (activeTab !== 'all') params.append('direction', activeTab)
      
      const response = await fetch(`${API_URL}/api/performance?${params}`)
      const data = await response.json()
      
      if (data.stats) setStats(data.stats)
      if (data.recentTrades) setRecentTrades(data.recentTrades)
      if (data.pairPerformance) setPairPerformance(data.pairPerformance)
      if (data.equityCurve) setEquityCurve(data.equityCurve)
    } catch (error) {
      console.error('Error fetching performance:', error)
    } finally {
      setIsLoading(false)
    }
  }, [timeFilter, activeTab])

  // Fetch data on mount and when filters change
  useEffect(() => {
    fetchPerformance()
  }, [fetchPerformance])

  // Normalize equity curve for chart display
  const normalizedEquity = equityCurve.length > 0
    ? (() => {
        const values = equityCurve.map(e => e.value)
        const min = Math.min(...values, 0)
        const max = Math.max(...values)
        const range = max - min || 1
        return values.map(v => Math.max(5, ((v - min) / range) * 100))
      })()
    : []

  // Export data to CSV
  const exportToCSV = () => {
    // Build CSV content
    let csvContent = ''
    
    // Add summary section
    csvContent += 'PERFORMANCE SUMMARY\n'
    csvContent += `Generated,${new Date().toISOString()}\n`
    csvContent += `Filter Period,${timeFilter}\n`
    csvContent += `Direction Filter,${activeTab}\n`
    csvContent += '\n'
    
    // Add stats
    csvContent += 'STATISTICS\n'
    csvContent += 'Metric,Value\n'
    csvContent += `Total Trades,${stats.totalTrades}\n`
    csvContent += `Wins,${stats.wins}\n`
    csvContent += `Losses,${stats.losses}\n`
    csvContent += `Win Rate,${stats.winRate}%\n`
    csvContent += `Average R:R,1:${stats.avgRR}\n`
    csvContent += `Total Profit (R),${stats.totalProfitR}\n`
    csvContent += '\n'
    
    // Add pair performance
    if (pairPerformance.length > 0) {
      csvContent += 'PERFORMANCE BY PAIR\n'
      csvContent += 'Pair,Total Trades,Wins,Win Rate\n'
      pairPerformance.forEach(p => {
        csvContent += `${p.pair},${p.total},${p.wins},${p.winRate}%\n`
      })
      csvContent += '\n'
    }
    
    // Add recent trades
    if (recentTrades.length > 0) {
      csvContent += 'RECENT TRADES\n'
      csvContent += 'Pair,Direction,Entry Price,Open Date,Close Date,Result,Profit (R)\n'
      recentTrades.forEach(t => {
        csvContent += `${t.asset},${t.type},${t.entry},${t.entryDate || ''},${t.closeDate || ''},${t.result},${t.profit}\n`
      })
      csvContent += '\n'
    }
    
    // Add equity curve
    if (equityCurve.length > 0) {
      csvContent += 'EQUITY CURVE\n'
      csvContent += 'Date,Cumulative P/L (R)\n'
      equityCurve.forEach(e => {
        csvContent += `${e.date},${e.value}\n`
      })
    }
    
    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    
    link.setAttribute('href', url)
    link.setAttribute('download', `performance_${timeFilter}_${activeTab}_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'
    
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex flex-wrap justify-between items-end gap-3 mb-2">
        <div className="flex min-w-72 flex-col gap-1">
          <h1 className="text-slate-900 dark:text-white text-2xl font-extrabold leading-tight">
            Performance Analytics
          </h1>
          <p className="text-slate-500 dark:text-[#92adc9] text-sm font-normal leading-normal">
            Track and analyze your bot's historical trade data across all markets.
          </p>
        </div>
        <Button variant="primary" icon="download" onClick={exportToCSV} disabled={isLoading}>
          Export CSV
        </Button>
      </div>

      {/* Tabs */}
      <div className="pb-2">
        <div className="flex border-b border-slate-200 dark:border-[#324d67] gap-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex flex-col items-center justify-center pb-[13px] pt-4 border-b-[3px] ${
                activeTab === tab.id
                  ? 'border-b-primary text-slate-900 dark:text-white'
                  : 'border-b-transparent text-slate-500 dark:text-[#92adc9]'
              }`}
            >
              <p className="text-sm font-bold leading-normal tracking-[0.015em]">{tab.label}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Time Filters */}
      <div className="flex gap-3 flex-wrap">
        {timeFilters.map((filter) => (
          <button
            key={filter.id}
            onClick={() => setTimeFilter(filter.id)}
            className={`flex h-9 shrink-0 items-center justify-center gap-x-2 rounded-lg px-4 cursor-pointer transition-colors ${
              timeFilter === filter.id
                ? 'bg-primary text-white shadow-lg shadow-primary/20'
                : 'bg-slate-200 dark:bg-[#233648] text-slate-900 dark:text-white hover:bg-primary/20'
            }`}
          >
            <p className="text-sm font-medium">{filter.label}</p>
          </button>
        ))}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Trades"
          value={isLoading ? '...' : stats.totalTrades.toLocaleString()}
          trend={`${stats.wins}W / ${stats.losses}L`}
          trendUp={stats.wins > stats.losses}
          tooltip="The total number of trades that have been closed. This includes both winning trades (W) and losing trades (L)."
        />
        <StatsCard
          title="Win Rate"
          value={isLoading ? '...' : `${stats.winRate}%`}
          trend={stats.winRate >= 50 ? 'Profitable' : 'Needs improvement'}
          trendUp={stats.winRate >= 50}
          tooltip="The percentage of trades that hit the profit target (wins) compared to total trades. A win rate above 50% means you win more often than you lose. However, even a lower win rate can be profitable if your average reward is higher than your risk."
        />
        <StatsCard
          title="Avg R:R"
          value={isLoading ? '...' : `1:${stats.avgRR}`}
          trend={stats.avgRR >= 2 ? 'Good ratio' : 'Below target'}
          trendUp={stats.avgRR >= 2}
          tooltip="Risk-to-Reward Ratio. Shows how much you expect to gain for every unit you risk. For example, 1:2 means for every $1 you risk, you aim to make $2. A ratio of 1:2 or higher is generally considered good, as you can be profitable even with a win rate below 50%."
        />
        <StatsCard
          title="Total Profit"
          value={isLoading ? '...' : `${stats.totalProfitR >= 0 ? '+' : ''}${stats.totalProfitR} R`}
          trend={stats.totalProfitR >= 0 ? 'In profit' : 'In loss'}
          trendUp={stats.totalProfitR >= 0}
          tooltip="Total profit expressed in 'R' units (Risk units). Each 'R' represents the amount you risked per trade. For example, +10R means you've made 10 times your standard risk amount. This metric standardizes profit regardless of position size."
        />
      </div>

      {/* Tables Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Trades Table */}
        <div className="lg:col-span-2 bg-white dark:bg-[#111a22] border border-slate-200 dark:border-[#324d67] rounded-xl overflow-hidden">
          <div className="p-6 border-b border-slate-200 dark:border-[#324d67] flex justify-between items-center">
            <h3 className="font-bold text-lg">Recent Trades</h3>
            <button className="text-primary text-sm font-bold">View All</button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-slate-500 dark:text-[#92adc9] text-xs uppercase bg-slate-50 dark:bg-[#111a22]">
                  <th className="px-4 py-4 font-semibold">Asset</th>
                  <th className="px-4 py-4 font-semibold">Type</th>
                  <th className="px-4 py-4 font-semibold">Entry Price</th>
                  <th className="px-4 py-4 font-semibold">Open Date</th>
                  <th className="px-4 py-4 font-semibold">Close Date</th>
                  <th className="px-4 py-4 font-semibold">Result</th>
                  <th className="px-4 py-4 font-semibold">Profit (R)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-[#233648]">
                {isLoading ? (
                  <tr>
                    <td colSpan="7" className="px-4 py-8 text-center text-slate-500">
                      <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span>
                      Loading trades...
                    </td>
                  </tr>
                ) : recentTrades.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-4 py-8 text-center text-slate-500">
                      No closed trades found for the selected filters
                    </td>
                  </tr>
                ) : (
                  recentTrades.map((trade) => (
                    <tr key={trade.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <td className="px-4 py-4 font-bold">{trade.asset}</td>
                      <td className={`px-4 py-4 font-bold ${trade.type === 'LONG' ? 'text-emerald-500' : 'text-rose-500'}`}>
                        {trade.type}
                      </td>
                      <td className="px-4 py-4 text-sm font-mono">{trade.entry}</td>
                      <td className="px-4 py-4 text-xs text-slate-500 dark:text-slate-400">{trade.entryDate || '-'}</td>
                      <td className="px-4 py-4 text-xs text-slate-500 dark:text-slate-400">{trade.closeDate || '-'}</td>
                      <td className="px-4 py-4">
                        <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
                          trade.result === 'win'
                            ? 'bg-emerald-500/10 text-emerald-500'
                            : 'bg-rose-500/10 text-rose-500'
                        }`}>
                          {trade.result}
                        </span>
                      </td>
                      <td className={`px-4 py-4 font-bold ${
                        trade.profit.startsWith('+') ? 'text-emerald-500' : 'text-rose-500'
                      }`}>
                        {trade.profit}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Performance per Pair */}
        <div className="bg-white dark:bg-[#111a22] border border-slate-200 dark:border-[#324d67] rounded-xl p-6">
          <h3 className="font-bold text-lg mb-6">Performance per Pair</h3>
          <div className="space-y-6">
            {isLoading ? (
              <div className="text-center text-slate-500 py-4">
                <span className="material-symbols-outlined animate-spin">progress_activity</span>
              </div>
            ) : pairPerformance.length === 0 ? (
              <div className="text-center text-slate-500 py-4">No pair data available</div>
            ) : (
              pairPerformance.map((item) => (
                <div key={item.pair} className="space-y-2">
                  <div className="flex justify-between items-center text-sm">
                    <span className="font-bold">{item.pair}</span>
                    <span className={`font-bold ${item.winRate >= 50 ? 'text-emerald-500' : 'text-rose-500'}`}>
                      {item.winRate}% ({item.wins}/{item.total})
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${item.color === 'primary' ? 'bg-primary' : 'bg-rose-500'}`}
                      style={{ width: `${item.winRate}%` }}
                    ></div>
                  </div>
                </div>
              ))
            )}
          </div>
          {pairPerformance.length > 0 && (
            <div className="mt-10 p-4 rounded-lg bg-primary/5 border border-primary/20">
              <div className="flex gap-3">
                <span className="material-symbols-outlined text-primary">info</span>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  {pairPerformance[0]?.pair} is your most traded pair with {pairPerformance[0]?.total} trades 
                  and a {pairPerformance[0]?.winRate}% win rate.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Equity Curve */}
      <div className="bg-white dark:bg-[#111a22] border border-slate-200 dark:border-[#324d67] rounded-xl p-6">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-lg">Equity Curve (Cumulative P/L in R)</h3>
            <div className="relative group">
              <button className="text-slate-400 hover:text-primary transition-colors">
                <span className="material-symbols-outlined text-[18px]">info</span>
              </button>
              <div className="absolute left-0 top-full mt-2 z-50 w-72 p-3 rounded-lg shadow-xl 
                bg-slate-800 dark:bg-slate-900 text-white text-xs leading-relaxed
                border border-slate-700 opacity-0 invisible group-hover:opacity-100 group-hover:visible
                transition-all duration-200">
                <div className="absolute -top-1.5 left-3 w-3 h-3 bg-slate-800 dark:bg-slate-900 
                  border-l border-t border-slate-700 rotate-45"></div>
                <p className="mb-2"><strong>Equity Curve</strong> shows your account balance growth over time.</p>
                <p className="mb-2">Each bar represents a trading day. The height shows your cumulative profit/loss in R (Risk units) up to that day.</p>
                <p>An upward trend means your strategy is profitable. Sharp drops indicate losing periods. Hover over each bar to see the exact date and profit value.</p>
              </div>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex items-center gap-2">
              <div className="size-3 bg-primary rounded-full"></div>
              <span className="text-xs text-slate-500 dark:text-slate-400">Profit (R)</span>
            </div>
          </div>
        </div>
        {isLoading ? (
          <div className="h-64 flex items-center justify-center text-slate-500">
            <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span>
            Loading chart...
          </div>
        ) : normalizedEquity.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-slate-500">
            No equity data available for the last 30 days
          </div>
        ) : (
          <>
            <div className="h-64 flex items-end justify-between gap-1 group/chart">
              {normalizedEquity.map((height, index) => (
                <div
                  key={index}
                  className="bg-primary/20 w-full hover:bg-primary transition-colors rounded-t-sm relative group"
                  style={{ height: `${height}%` }}
                >
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-slate-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                    {equityCurve[index]?.date}: {equityCurve[index]?.value}R
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-between mt-4 text-xs text-slate-500 dark:text-[#92adc9] px-2">
              {equityCurve.length > 0 && (
                <>
                  <span>{equityCurve[0]?.date}</span>
                  {equityCurve.length > 4 && <span>{equityCurve[Math.floor(equityCurve.length / 4)]?.date}</span>}
                  {equityCurve.length > 2 && <span>{equityCurve[Math.floor(equityCurve.length / 2)]?.date}</span>}
                  {equityCurve.length > 4 && <span>{equityCurve[Math.floor(equityCurve.length * 3 / 4)]?.date}</span>}
                  <span>{equityCurve[equityCurve.length - 1]?.date}</span>
                </>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default Performance
