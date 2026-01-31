import { Link } from 'react-router-dom'
import Badge from '../common/Badge'

function PairsTable({ trades }) {
  const getStatusBadge = (status) => {
    switch (status) {
      case 'active':
        return <Badge variant="active" pulse>Active</Badge>
      case 'retest':
        return <Badge variant="retest" icon="hourglass_empty">Retest</Badge>
      case 'waiting':
        return <Badge variant="waiting" icon="visibility">Waiting</Badge>
      default:
        return <Badge>{status}</Badge>
    }
  }

  return (
    <div className="bg-white dark:bg-[#192633] rounded-xl border border-slate-200 dark:border-[#233648] overflow-hidden shadow-sm">
      <div className="px-6 py-5 border-b border-slate-200 dark:border-[#233648] flex items-center justify-between">
        <h2 className="text-slate-900 dark:text-white text-lg font-bold">Forex Pairs Monitoring</h2>
        <button className="text-primary text-sm font-bold flex items-center gap-1 hover:underline">
          <span className="material-symbols-outlined text-[18px]">filter_list</span>
          Filter
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="bg-slate-50 dark:bg-background-dark/50">
              <th className="px-6 py-4 text-slate-500 dark:text-[#92adc9] text-xs font-bold uppercase tracking-wider">Pair</th>
              <th className="px-6 py-4 text-slate-500 dark:text-[#92adc9] text-xs font-bold uppercase tracking-wider">Status</th>
              <th className="px-6 py-4 text-slate-500 dark:text-[#92adc9] text-xs font-bold uppercase tracking-wider">Direction</th>
              <th className="px-6 py-4 text-slate-500 dark:text-[#92adc9] text-xs font-bold uppercase tracking-wider">Entry Price</th>
              <th className="px-6 py-4 text-slate-500 dark:text-[#92adc9] text-xs font-bold uppercase tracking-wider">Risk/Reward</th>
              <th className="px-6 py-4 text-slate-500 dark:text-[#92adc9] text-xs font-bold uppercase tracking-wider text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-[#233648]">
            {trades.map((trade) => (
              <tr key={trade.id} className="hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                <td className="px-6 py-4 font-bold text-slate-900 dark:text-white">{trade.pair}</td>
                <td className="px-6 py-4">{getStatusBadge(trade.status)}</td>
                <td className="px-6 py-4">
                  <div className={`inline-flex items-center gap-1 font-bold text-sm ${trade.direction === 'LONG' ? 'text-accent-green' : 'text-accent-red'}`}>
                    <span className="material-symbols-outlined text-[18px]">
                      {trade.direction === 'LONG' ? 'north_east' : 'south_east'}
                    </span>
                    {trade.direction}
                  </div>
                </td>
                <td className="px-6 py-4 text-slate-600 dark:text-slate-400 font-mono text-sm">{trade.entryPrice}</td>
                <td className="px-6 py-4 text-slate-600 dark:text-slate-400 text-sm">{trade.riskReward}</td>
                <td className="px-6 py-4 text-right">
                  <Link
                    to={`/pair/${trade.pair.replace('/', '')}`}
                    className="bg-slate-100 dark:bg-[#233648] hover:bg-primary hover:text-white text-slate-600 dark:text-white px-4 py-1.5 rounded-lg text-xs font-bold transition-all"
                  >
                    Details
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default PairsTable
