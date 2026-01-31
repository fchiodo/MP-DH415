import { useState } from 'react'
import StatsCard from '../components/common/StatsCard'
import Button from '../components/common/Button'

function Performance() {
  const [activeTab, setActiveTab] = useState('all')
  const [timeFilter, setTimeFilter] = useState('month')

  const tabs = [
    { id: 'all', label: 'All Trades' },
    { id: 'long', label: 'Long Only' },
    { id: 'short', label: 'Short Only' },
    { id: 'strategy', label: 'By Strategy' },
  ]

  const timeFilters = [
    { id: '24h', label: 'Last 24h' },
    { id: '7d', label: 'Last 7d' },
    { id: 'month', label: 'Last Month' },
    { id: 'quarter', label: 'Last Quarter' },
    { id: 'ytd', label: 'Year to Date' },
  ]

  const recentTrades = [
    { asset: 'BTC/USDT', type: 'Long', strategy: 'Mean Reversion', entry: '$64,241', result: 'win', profit: '+3.2 R' },
    { asset: 'ETH/USDT', type: 'Short', strategy: 'Trend Break', entry: '$3,421', result: 'loss', profit: '-1.0 R' },
    { asset: 'SOL/USDT', type: 'Long', strategy: 'EMA Ribbon', entry: '$145.20', result: 'win', profit: '+2.1 R' },
    { asset: 'DOT/USDT', type: 'Long', strategy: 'Mean Reversion', entry: '$7.21', result: 'win', profit: '+1.5 R' },
    { asset: 'AVAX/USDT', type: 'Short', strategy: 'Trend Break', entry: '$38.45', result: 'loss', profit: '-1.0 R' },
  ]

  const pairPerformance = [
    { pair: 'BTC/USDT', winRate: 78, color: 'primary' },
    { pair: 'ETH/USDT', winRate: 62, color: 'primary' },
    { pair: 'SOL/USDT', winRate: 55, color: 'primary' },
    { pair: 'ADA/USDT', winRate: 42, color: 'rose' },
    { pair: 'DOT/USDT', winRate: 59, color: 'primary' },
  ]

  const equityCurve = [20, 25, 22, 35, 42, 40, 45, 55, 50, 62, 75, 70, 68, 82, 90, 85, 88, 95, 100, 92]

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
        <Button variant="primary" icon="download">Export CSV</Button>
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
          value="1,284"
          trend="+12%"
          trendUp={true}
        />
        <StatsCard
          title="Win Rate"
          value="64.2%"
          trend="+2.1%"
          trendUp={true}
        />
        <StatsCard
          title="Avg R:R"
          value="1:2.4"
          trend="-0.2%"
          trendUp={false}
        />
        <StatsCard
          title="Total Profit"
          value="+142.5 R"
          trend="+15.4%"
          trendUp={true}
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
                  <th className="px-6 py-4 font-semibold">Asset</th>
                  <th className="px-6 py-4 font-semibold">Type</th>
                  <th className="px-6 py-4 font-semibold">Strategy</th>
                  <th className="px-6 py-4 font-semibold">Entry</th>
                  <th className="px-6 py-4 font-semibold">Result</th>
                  <th className="px-6 py-4 font-semibold">Profit (R)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-[#233648]">
                {recentTrades.map((trade, index) => (
                  <tr key={index} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    <td className="px-6 py-4 font-bold">{trade.asset}</td>
                    <td className={`px-6 py-4 font-bold ${trade.type === 'Long' ? 'text-emerald-500' : 'text-rose-500'}`}>
                      {trade.type}
                    </td>
                    <td className="px-6 py-4 text-sm">{trade.strategy}</td>
                    <td className="px-6 py-4 text-sm">{trade.entry}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
                        trade.result === 'win'
                          ? 'bg-emerald-500/10 text-emerald-500'
                          : 'bg-rose-500/10 text-rose-500'
                      }`}>
                        {trade.result}
                      </span>
                    </td>
                    <td className={`px-6 py-4 font-bold ${
                      trade.profit.startsWith('+') ? 'text-emerald-500' : 'text-rose-500'
                    }`}>
                      {trade.profit}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Performance per Pair */}
        <div className="bg-white dark:bg-[#111a22] border border-slate-200 dark:border-[#324d67] rounded-xl p-6">
          <h3 className="font-bold text-lg mb-6">Performance per Pair</h3>
          <div className="space-y-6">
            {pairPerformance.map((item) => (
              <div key={item.pair} className="space-y-2">
                <div className="flex justify-between items-center text-sm">
                  <span className="font-bold">{item.pair}</span>
                  <span className={`font-bold ${item.winRate >= 50 ? 'text-emerald-500' : 'text-rose-500'}`}>
                    {item.winRate}% Win Rate
                  </span>
                </div>
                <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${item.color === 'primary' ? 'bg-primary' : 'bg-rose-500'}`}
                    style={{ width: `${item.winRate}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-10 p-4 rounded-lg bg-primary/5 border border-primary/20">
            <div className="flex gap-3">
              <span className="material-symbols-outlined text-primary">info</span>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                BTC/USDT continues to be your most profitable pair with a profit factor of 2.8.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Equity Curve */}
      <div className="bg-white dark:bg-[#111a22] border border-slate-200 dark:border-[#324d67] rounded-xl p-6">
        <div className="flex justify-between items-center mb-6">
          <h3 className="font-bold text-lg">Equity Curve (Last Month)</h3>
          <div className="flex gap-4">
            <div className="flex items-center gap-2">
              <div className="size-3 bg-primary rounded-full"></div>
              <span className="text-xs text-slate-500 dark:text-slate-400">Profit (R)</span>
            </div>
          </div>
        </div>
        <div className="h-64 flex items-end justify-between gap-1 group/chart">
          {equityCurve.map((height, index) => (
            <div
              key={index}
              className="bg-primary/20 w-full hover:bg-primary transition-colors rounded-t-sm"
              style={{ height: `${height}%` }}
              title={`Day ${index + 1}`}
            ></div>
          ))}
        </div>
        <div className="flex justify-between mt-4 text-xs text-slate-500 dark:text-[#92adc9] px-2">
          <span>May 01</span>
          <span>May 08</span>
          <span>May 15</span>
          <span>May 22</span>
          <span>May 30</span>
        </div>
      </div>
    </div>
  )
}

export default Performance
