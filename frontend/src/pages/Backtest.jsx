import { useState, useEffect, useCallback } from 'react'
import StatsCard from '../components/common/StatsCard'
import Button from '../components/common/Button'
import { API_URL } from '../config'

const PAGE_SIZE = 50

// Columns as saved by the MP-DH415-BT engine (table `trades`)
const COLUMNS = [
  { key: 'pair', label: 'Pair' },
  { key: 'status', label: 'Status' },
  { key: 'trade_type', label: 'Type' },
  { key: 'entry_date', label: 'Entry Date' },
  { key: 'close_date', label: 'Close Date' },
  { key: 'entry_price', label: 'Entry Price' },
  { key: 'entry_price_index', label: 'Entry Idx' },
  { key: 'stop_loss', label: 'Stop Loss' },
  { key: 'target', label: 'Target' },
  { key: 'direction', label: 'Direction' },
  { key: 'initial_risk_reward', label: 'R:R Init' },
  { key: 'final_risk_reward', label: 'R:R Final' },
  { key: 'profit', label: 'Profit (R)' },
  { key: 'result', label: 'Result' },
  { key: 'zones_rectX1_DLY', label: 'Zone DLY X1' },
  { key: 'zones_rectY1_DLY', label: 'Zone DLY Y1' },
  { key: 'zones_rectY2_DLY', label: 'Zone DLY Y2' },
  { key: 'zones_rectX1_H4', label: 'Zone H4 X1' },
  { key: 'zones_rectY1_H4', label: 'Zone H4 Y1' },
  { key: 'zones_rectY2_H4', label: 'Zone H4 Y2' },
  { key: 'pattern_x1', label: 'Pattern X1' },
  { key: 'pattern_y1', label: 'Pattern Y1' },
  { key: 'pattern_y2', label: 'Pattern Y2' },
  { key: 'breakup_date', label: 'Breakup Date' },
  { key: 'fibonacci100', label: 'Fib 100' },
]

const isEmpty = (v) => v === null || v === undefined || v === ''
const fmtPrice = (v) => (isEmpty(v) ? '-' : Number(v).toFixed(5))
const fmtRR = (v) => (isEmpty(v) ? '-' : Number(v).toFixed(2))
const fmtDate = (v) => (isEmpty(v) ? '-' : v)

function Backtest() {
  const [databases, setDatabases] = useState([])
  const [selectedDb, setSelectedDb] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  // Filters
  const [directionTab, setDirectionTab] = useState('all')
  const [pairFilter, setPairFilter] = useState('all')
  const [resultFilter, setResultFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [page, setPage] = useState(0)

  // Data
  const [trades, setTrades] = useState([])
  const [total, setTotal] = useState(0)
  const [pairs, setPairs] = useState([])
  const [stats, setStats] = useState(null)

  const directionTabs = [
    { id: 'all', label: 'All Trades' },
    { id: 'LONG', label: 'Long Only' },
    { id: 'SHORT', label: 'Short Only' },
  ]

  const resultFilters = [
    { id: 'all', label: 'All Results' },
    { id: 'TARGET', label: 'Target' },
    { id: 'STOP LOSS', label: 'Stop Loss' },
  ]

  const typeFilters = [
    { id: 'all', label: 'Full + Partial' },
    { id: 'FULL', label: 'Full' },
    { id: 'PARTIAL', label: 'Partial' },
  ]

  const buildParams = useCallback((limit, offset) => {
    const params = new URLSearchParams()
    if (selectedDb) params.append('db', selectedDb)
    if (pairFilter !== 'all') params.append('pair', pairFilter)
    if (directionTab !== 'all') params.append('direction', directionTab)
    if (resultFilter !== 'all') params.append('result', resultFilter)
    if (typeFilter !== 'all') params.append('type', typeFilter)
    params.append('limit', limit)
    params.append('offset', offset)
    return params
  }, [selectedDb, pairFilter, directionTab, resultFilter, typeFilter])

  // Load list of available backtest databases (once)
  useEffect(() => {
    const fetchDatabases = async () => {
      try {
        const response = await fetch(`${API_URL}/api/backtest/databases`)
        const data = await response.json()
        const dbs = data.databases || []
        setDatabases(dbs)
        if (dbs.length > 0) {
          setSelectedDb(dbs[0].name)
        } else {
          setIsLoading(false)
        }
      } catch (err) {
        console.error('Error fetching backtest databases:', err)
        setError('Cannot reach the API server')
        setIsLoading(false)
      }
    }
    fetchDatabases()
  }, [])

  // Load trades whenever db / filters / page change
  const fetchTrades = useCallback(async () => {
    if (!selectedDb) return
    setIsLoading(true)
    setError(null)
    try {
      const params = buildParams(PAGE_SIZE, page * PAGE_SIZE)
      const response = await fetch(`${API_URL}/api/backtest/trades?${params}`)
      const data = await response.json()
      if (data.error) throw new Error(data.error)
      setTrades(data.trades || [])
      setTotal(data.total || 0)
      setPairs(data.pairs || [])
      setStats(data.stats || null)
    } catch (err) {
      console.error('Error fetching backtest trades:', err)
      setError(err.message)
      setTrades([])
    } finally {
      setIsLoading(false)
    }
  }, [selectedDb, buildParams, page])

  useEffect(() => {
    fetchTrades()
  }, [fetchTrades])

  // Reset pagination when any filter changes
  const selectDb = (name) => { setSelectedDb(name); setPairFilter('all'); setPage(0) }
  const selectDirection = (id) => { setDirectionTab(id); setPage(0) }
  const selectPair = (pair) => { setPairFilter(pair); setPage(0) }
  const selectResult = (id) => { setResultFilter(id); setPage(0) }
  const selectType = (id) => { setTypeFilter(id); setPage(0) }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // Export the whole filtered dataset to CSV
  const exportToCSV = async () => {
    try {
      const params = buildParams(20000, 0)
      const response = await fetch(`${API_URL}/api/backtest/trades?${params}`)
      const data = await response.json()
      const rows = data.trades || []

      const header = ['id', ...COLUMNS.map((c) => c.key)]
      let csvContent = header.join(',') + '\n'
      rows.forEach((t) => {
        csvContent += header.map((k) => (isEmpty(t[k]) ? '' : `"${String(t[k]).replace(/"/g, '""')}"`)).join(',') + '\n'
      })

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      link.setAttribute('href', URL.createObjectURL(blob))
      link.setAttribute('download', `backtest_${(selectedDb || 'db').replace('.db', '')}_${new Date().toISOString().split('T')[0]}.csv`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (err) {
      console.error('Error exporting CSV:', err)
    }
  }

  const renderCell = (trade, key) => {
    const value = trade[key]
    switch (key) {
      case 'pair':
        return <td key={key} className="px-4 py-3 font-bold whitespace-nowrap">{value}</td>
      case 'status':
        return (
          <td key={key} className="px-4 py-3 whitespace-nowrap">
            <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
              value === 'CLOSED'
                ? 'bg-slate-500/10 text-slate-500 dark:text-slate-400'
                : 'bg-amber-500/10 text-amber-500'
            }`}>
              {value || '-'}
            </span>
          </td>
        )
      case 'trade_type':
        return (
          <td key={key} className="px-4 py-3 whitespace-nowrap">
            <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
              value === 'FULL'
                ? 'bg-primary/10 text-primary'
                : 'bg-purple-500/10 text-purple-500'
            }`}>
              {value || '-'}
            </span>
          </td>
        )
      case 'direction':
        return (
          <td key={key} className={`px-4 py-3 font-bold whitespace-nowrap ${
            value === 'LONG' ? 'text-emerald-500' : 'text-rose-500'
          }`}>
            {value || '-'}
          </td>
        )
      case 'result':
        return (
          <td key={key} className="px-4 py-3 whitespace-nowrap">
            {isEmpty(value) ? (
              <span className="text-slate-400">-</span>
            ) : (
              <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
                value === 'TARGET'
                  ? 'bg-emerald-500/10 text-emerald-500'
                  : 'bg-rose-500/10 text-rose-500'
              }`}>
                {value}
              </span>
            )}
          </td>
        )
      case 'profit': {
        if (isEmpty(value)) return <td key={key} className="px-4 py-3 text-slate-400">-</td>
        const profit = Number(value)
        return (
          <td key={key} className={`px-4 py-3 font-bold whitespace-nowrap ${
            profit >= 0 ? 'text-emerald-500' : 'text-rose-500'
          }`}>
            {profit >= 0 ? '+' : ''}{profit.toFixed(2)}
          </td>
        )
      }
      case 'entry_date':
      case 'close_date':
      case 'breakup_date':
      case 'zones_rectX1_DLY':
      case 'zones_rectX1_H4':
      case 'pattern_x1':
        return (
          <td key={key} className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
            {fmtDate(value)}
          </td>
        )
      case 'initial_risk_reward':
      case 'final_risk_reward':
        return <td key={key} className="px-4 py-3 text-sm font-mono whitespace-nowrap">{fmtRR(value)}</td>
      case 'entry_price_index':
        return <td key={key} className="px-4 py-3 text-sm font-mono whitespace-nowrap">{isEmpty(value) ? '-' : value}</td>
      default:
        // Prices: entry_price, stop_loss, target, zone/pattern Y levels, fibonacci100
        return <td key={key} className="px-4 py-3 text-sm font-mono whitespace-nowrap">{fmtPrice(value)}</td>
    }
  }

  // No backtest DB available at all
  if (!isLoading && databases.length === 0) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex min-w-72 flex-col gap-1 mb-2">
          <h1 className="text-slate-900 dark:text-white text-2xl font-extrabold leading-tight">Backtest Results</h1>
          <p className="text-slate-500 dark:text-[#92adc9] text-sm font-normal leading-normal">
            Historical trades generated by the MP-DH415-BT backtesting engine.
          </p>
        </div>
        <div className="bg-white dark:bg-[#111a22] border border-slate-200 dark:border-[#324d67] rounded-xl p-10 flex flex-col items-center gap-3 text-center">
          <span className="material-symbols-outlined text-5xl text-slate-400">database_off</span>
          <h3 className="font-bold text-lg">No backtest database found</h3>
          <p className="text-sm text-slate-500 dark:text-[#92adc9] max-w-md">
            Copy the backtest .db files (e.g. my_database_2024.db) into the <span className="font-mono">backtest/</span> folder
            in the repository root, or set the <span className="font-mono">BACKTEST_DB_DIR</span> environment variable, then reload this page.
          </p>
          {error && <p className="text-sm text-rose-500">{error}</p>}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex flex-wrap justify-between items-end gap-3 mb-2">
        <div className="flex min-w-72 flex-col gap-1">
          <h1 className="text-slate-900 dark:text-white text-2xl font-extrabold leading-tight">
            Backtest Results
          </h1>
          <p className="text-slate-500 dark:text-[#92adc9] text-sm font-normal leading-normal">
            Historical trades generated by the MP-DH415-BT backtesting engine.
          </p>
        </div>
        <Button variant="primary" icon="download" onClick={exportToCSV} disabled={isLoading || trades.length === 0}>
          Export CSV
        </Button>
      </div>

      {/* Database selector */}
      <div className="flex gap-3 flex-wrap items-center">
        <p className="text-slate-400 dark:text-[#92adc9] text-xs font-bold uppercase tracking-wider">Database</p>
        {databases.map((db) => (
          <button
            key={db.name}
            onClick={() => selectDb(db.name)}
            className={`flex h-9 shrink-0 items-center justify-center gap-x-2 rounded-lg px-4 cursor-pointer transition-colors ${
              selectedDb === db.name
                ? 'bg-primary text-white shadow-lg shadow-primary/20'
                : 'bg-slate-200 dark:bg-[#233648] text-slate-900 dark:text-white hover:bg-primary/20'
            }`}
            title={db.name}
          >
            <p className="text-sm font-medium">{db.label}</p>
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
              selectedDb === db.name ? 'bg-white/20' : 'bg-slate-300 dark:bg-[#324d67]'
            }`}>
              {db.trades}
            </span>
          </button>
        ))}
      </div>

      {/* Direction Tabs */}
      <div className="pb-2">
        <div className="flex border-b border-slate-200 dark:border-[#324d67] gap-8">
          {directionTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => selectDirection(tab.id)}
              className={`flex flex-col items-center justify-center pb-[13px] pt-4 border-b-[3px] ${
                directionTab === tab.id
                  ? 'border-b-primary text-slate-900 dark:text-white'
                  : 'border-b-transparent text-slate-500 dark:text-[#92adc9]'
              }`}
            >
              <p className="text-sm font-bold leading-normal tracking-[0.015em]">{tab.label}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap items-center">
        <select
          value={pairFilter}
          onChange={(e) => selectPair(e.target.value)}
          className="h-9 rounded-lg px-3 text-sm font-medium bg-slate-200 dark:bg-[#233648] text-slate-900 dark:text-white border-transparent focus:border-primary focus:ring-primary cursor-pointer"
        >
          <option value="all">All Pairs ({pairs.length})</option>
          {pairs.map((pair) => (
            <option key={pair} value={pair}>{pair}</option>
          ))}
        </select>

        {resultFilters.map((filter) => (
          <button
            key={filter.id}
            onClick={() => selectResult(filter.id)}
            className={`flex h-9 shrink-0 items-center justify-center rounded-lg px-4 cursor-pointer transition-colors ${
              resultFilter === filter.id
                ? 'bg-primary text-white shadow-lg shadow-primary/20'
                : 'bg-slate-200 dark:bg-[#233648] text-slate-900 dark:text-white hover:bg-primary/20'
            }`}
          >
            <p className="text-sm font-medium">{filter.label}</p>
          </button>
        ))}

        <div className="w-px h-6 bg-slate-300 dark:bg-[#324d67]"></div>

        {typeFilters.map((filter) => (
          <button
            key={filter.id}
            onClick={() => selectType(filter.id)}
            className={`flex h-9 shrink-0 items-center justify-center rounded-lg px-4 cursor-pointer transition-colors ${
              typeFilter === filter.id
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
          value={isLoading || !stats ? '...' : stats.totalTrades.toLocaleString()}
          trend={stats ? `${stats.wins}W / ${stats.losses}L` : ''}
          trendUp={stats ? stats.wins >= stats.losses : true}
          tooltip="Total number of backtest trades matching the current filters. Each setup produces two rows: FULL (target on the H4 Kijun) and PARTIAL (target at 1:1 risk-reward)."
        />
        <StatsCard
          title="Win Rate"
          value={isLoading || !stats ? '...' : `${stats.winRate}%`}
          trend={stats && stats.winRate >= 50 ? 'Profitable' : 'Below 50%'}
          trendUp={stats ? stats.winRate >= 50 : true}
          tooltip="Percentage of trades that hit the target compared to all decided trades (target + stop loss)."
        />
        <StatsCard
          title="Avg R:R"
          value={isLoading || !stats ? '...' : `1:${stats.avgRR}`}
          trend={stats && stats.avgRR >= 2 ? 'Good ratio' : 'Below target'}
          trendUp={stats ? stats.avgRR >= 2 : true}
          tooltip="Average initial risk-to-reward ratio of the trades matching the current filters. The strategy only opens setups with R:R of at least 1:2."
        />
        <StatsCard
          title="Total Profit"
          value={isLoading || !stats ? '...' : `${stats.totalProfitR >= 0 ? '+' : ''}${stats.totalProfitR} R`}
          trend={stats && stats.totalProfitR >= 0 ? 'In profit' : 'In loss'}
          trendUp={stats ? stats.totalProfitR >= 0 : true}
          tooltip="Sum of the profit column in R units (risk units) across the trades matching the current filters."
        />
      </div>

      {/* Trades Table */}
      <div className="bg-white dark:bg-[#111a22] border border-slate-200 dark:border-[#324d67] rounded-xl overflow-hidden">
        <div className="p-6 border-b border-slate-200 dark:border-[#324d67] flex justify-between items-center flex-wrap gap-3">
          <h3 className="font-bold text-lg">
            Backtest Trades
            <span className="ml-2 text-sm font-medium text-slate-500 dark:text-[#92adc9]">
              {selectedDb}
            </span>
          </h3>
          <p className="text-sm text-slate-500 dark:text-[#92adc9]">
            {total > 0 && `Showing ${page * PAGE_SIZE + 1}–${Math.min((page + 1) * PAGE_SIZE, total)} of ${total.toLocaleString()}`}
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-slate-500 dark:text-[#92adc9] text-xs uppercase bg-slate-50 dark:bg-[#111a22]">
                {COLUMNS.map((col) => (
                  <th key={col.key} className="px-4 py-4 font-semibold whitespace-nowrap">{col.label}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-[#233648]">
              {isLoading ? (
                <tr>
                  <td colSpan={COLUMNS.length} className="px-4 py-8 text-center text-slate-500">
                    <span className="material-symbols-outlined animate-spin mr-2">progress_activity</span>
                    Loading backtest trades...
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={COLUMNS.length} className="px-4 py-8 text-center text-rose-500">{error}</td>
                </tr>
              ) : trades.length === 0 ? (
                <tr>
                  <td colSpan={COLUMNS.length} className="px-4 py-8 text-center text-slate-500">
                    No backtest trades found for the selected filters
                  </td>
                </tr>
              ) : (
                trades.map((trade) => (
                  <tr key={trade.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    {COLUMNS.map((col) => renderCell(trade, col.key))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {/* Pagination */}
        {!isLoading && total > PAGE_SIZE && (
          <div className="p-4 border-t border-slate-200 dark:border-[#324d67] flex justify-between items-center">
            <Button variant="secondary" icon="chevron_left" disabled={page === 0} onClick={() => setPage(page - 1)}>
              Previous
            </Button>
            <p className="text-sm text-slate-500 dark:text-[#92adc9]">
              Page {page + 1} of {totalPages}
            </p>
            <Button variant="secondary" disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>
              Next
              <span className="material-symbols-outlined text-[18px]">chevron_right</span>
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

export default Backtest
