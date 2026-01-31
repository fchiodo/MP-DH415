import { useState } from 'react'
import StatsCard from '../components/common/StatsCard'
import Button from '../components/common/Button'

function Simulation() {
  const [pendingOrders] = useState([
    { id: 1, timestamp: '2023-11-24 14:30:05', symbol: 'EURUSD', type: 'BUY_LIMIT', price: '1.09245', sl: '1.09100', tp: '1.09650' },
    { id: 2, timestamp: '2023-11-24 14:31:12', symbol: 'GBPUSD', type: 'SELL_STOP', price: '1.25430', sl: '1.25800', tp: '1.24800' },
    { id: 3, timestamp: '2023-11-24 14:35:55', symbol: 'XAUUSD', type: 'BUY_LIMIT', price: '1992.50', sl: '1985.00', tp: '2010.00' },
  ])

  const [modifications] = useState([
    { id: 1, time: '14:40:01', ticket: '#8839210', symbol: 'USDJPY', type: 'SL (Trailing)', from: '149.200', to: '149.350', change: '+150' },
    { id: 2, time: '14:42:15', ticket: '#8839215', symbol: 'NAS100', type: 'TP (Update)', from: '16050.0', to: '16120.0', change: '+700' },
    { id: 3, time: '14:45:00', ticket: '#8839222', symbol: 'EURUSD', type: 'SL (Breakeven)', from: '1.08900', to: '1.09120', change: '+220' },
  ])

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
        <Button variant="secondary" icon="delete_sweep">Clear All Logs</Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatsCard
          title="Pending Orders"
          value="12"
          icon="schedule"
          iconColor="text-primary"
          subtitle="+2 since last hour"
        />
        <StatsCard
          title="Active Modifications"
          value="48"
          icon="edit_note"
          iconColor="text-primary"
          subtitle="Trailing 32 / BE 16"
        />
        <StatsCard
          title="Simulated Exposure"
          value="$142,500.00"
          icon="analytics"
          iconColor="text-primary"
          subtitle="Total Margin: $1,425.00"
        />
      </div>

      {/* Pending Orders Table */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-slate-900 dark:text-white text-xl font-bold tracking-tight flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">list_alt</span>
            Pending Orders
          </h2>
          <span className="text-xs font-mono text-slate-500 dark:text-[#92adc9] uppercase">Updated 2s ago</span>
        </div>
        <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-[#324d67] bg-white dark:bg-[#192633]">
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-50 dark:bg-[#1a2733] border-b border-slate-200 dark:border-[#324d67]">
              <tr>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Timestamp</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Symbol</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Type</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Price</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">SL</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">TP</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-[#233648]">
              {pendingOrders.map((order) => (
                <tr key={order.id} className="hover:bg-slate-50 dark:hover:bg-[#16232e] transition-colors">
                  <td className="px-4 py-4 text-sm font-mono text-slate-500 dark:text-slate-400">{order.timestamp}</td>
                  <td className="px-4 py-4 text-sm font-bold text-slate-900 dark:text-white">{order.symbol}</td>
                  <td className="px-4 py-4 text-sm">{getOrderTypeBadge(order.type)}</td>
                  <td className="px-4 py-4 text-sm font-mono text-slate-900 dark:text-white">{order.price}</td>
                  <td className="px-4 py-4 text-sm font-mono text-red-500">{order.sl}</td>
                  <td className="px-4 py-4 text-sm font-mono text-green-500">{order.tp}</td>
                  <td className="px-4 py-4 text-sm">
                    <button className="text-primary hover:underline font-bold">Details</button>
                  </td>
                </tr>
              ))}
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
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Time</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Ticket #</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Symbol</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Type</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">From</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">To</th>
                <th className="px-4 py-3 text-xs font-bold text-slate-500 dark:text-[#92adc9] uppercase tracking-wider">Change (Pts)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-[#233648]">
              {modifications.map((mod) => (
                <tr key={mod.id} className="hover:bg-slate-50 dark:hover:bg-[#16232e] transition-colors">
                  <td className="px-4 py-4 text-sm font-mono text-slate-500 dark:text-slate-400">{mod.time}</td>
                  <td className="px-4 py-4 text-sm font-mono text-slate-900 dark:text-white">{mod.ticket}</td>
                  <td className="px-4 py-4 text-sm font-bold text-slate-900 dark:text-white">{mod.symbol}</td>
                  <td className="px-4 py-4 text-sm font-bold text-slate-500 dark:text-[#92adc9]">{mod.type}</td>
                  <td className="px-4 py-4 text-sm font-mono text-slate-400">{mod.from}</td>
                  <td className="px-4 py-4 text-sm">
                    <span className={`font-mono px-1 rounded ${getChangeBadgeColor(mod.type)}`}>{mod.to}</span>
                  </td>
                  <td className={`px-4 py-4 text-sm font-bold ${
                    mod.type.includes('Trailing') ? 'text-green-500' :
                    mod.type.includes('Breakeven') ? 'text-blue-500' : 'text-primary'
                  }`}>
                    {mod.change}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer Status */}
      <div className="border-t border-slate-200 dark:border-[#233648] pt-6 flex flex-col md:flex-row justify-between items-center gap-4 text-slate-500 dark:text-[#92adc9]">
        <div className="flex items-center gap-4">
          <p className="text-xs">MT5 API Status: <span className="text-green-500 font-bold uppercase">Online</span></p>
          <p className="text-xs">Latency: <span className="text-slate-900 dark:text-white font-medium">12ms</span></p>
        </div>
        <div className="flex gap-6">
          <a className="text-xs hover:text-primary transition-colors" href="#">Documentation</a>
          <a className="text-xs hover:text-primary transition-colors" href="#">API Keys</a>
          <a className="text-xs hover:text-primary transition-colors" href="#">System Health</a>
        </div>
      </div>
    </div>
  )
}

export default Simulation
