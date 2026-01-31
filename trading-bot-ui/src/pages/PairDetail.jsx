import { useParams, Link } from 'react-router-dom'
import Button from '../components/common/Button'

function PairDetail() {
  const { symbol } = useParams()
  const formattedSymbol = symbol ? `${symbol.slice(0, 3)}/${symbol.slice(3)}` : 'EUR/USD'

  const trade = {
    pair: formattedSymbol,
    status: 'Live Trade',
    direction: 'SHORT',
    entry: 1.0920,
    stopLoss: 1.0955,
    target: 1.0820,
    positionSize: '0.5 Lot',
    riskReward: '1:2.8',
    pattern: 'Descending Wedge Breakdown',
    currentPL: '+$245.50',
    progress: 65,
  }

  const zones = {
    daily: { level: '1.0850', status: 'Validated' },
    h4: { level: '1.0910', status: 'Pending Mitigation' },
  }

  const timeline = [
    { id: 1, title: 'Zone Identified', desc: 'Daily demand level hit at 1.0850', time: 'Oct 24, 08:30 AM', status: 'complete' },
    { id: 2, title: 'Signal Confirmed', desc: 'Wedge breakdown on H1 timeframe', time: 'Oct 24, 10:15 AM', status: 'complete' },
    { id: 3, title: 'Trade Entered', desc: 'Short position at 1.0920', time: 'Oct 24, 11:00 AM', status: 'active' },
    { id: 4, title: 'Target Pending', desc: 'Awaiting price action at 1.0820', time: 'ETA: Approx 4 hours', status: 'pending' },
  ]

  return (
    <div className="flex flex-col gap-6">
      {/* Breadcrumbs */}
      <div className="flex flex-wrap gap-2 py-2">
        <Link to="/" className="text-slate-400 dark:text-[#92adc9] text-sm font-medium hover:text-primary">
          Market Analysis
        </Link>
        <span className="text-slate-400 dark:text-[#92adc9] text-sm font-medium">/</span>
        <span className="text-slate-900 dark:text-white text-sm font-medium">{trade.pair} Detailed View</span>
      </div>

      {/* Page Header */}
      <div className="flex flex-wrap justify-between items-center gap-3">
        <div className="flex min-w-72 flex-col gap-1">
          <div className="flex items-center gap-3">
            <h1 className="text-slate-900 dark:text-white text-2xl font-extrabold leading-tight">
              {trade.pair} Analysis
            </h1>
            <span className="bg-green-500/20 text-green-500 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
              {trade.status}
            </span>
          </div>
          <p className="text-slate-500 dark:text-[#92adc9] text-sm font-normal">
            Real-time trade setup and zone validation for {trade.pair.replace('/', ' / ')}
          </p>
        </div>
        <Link to="/">
          <Button variant="secondary" icon="arrow_back">Back to Dashboard</Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          {/* Zones Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-1 gap-4 rounded-xl border border-slate-200 dark:border-[#324d67] bg-white dark:bg-[#192633] p-5">
              <div className="flex items-center justify-center size-12 rounded-lg bg-primary/10 text-primary">
                <span className="material-symbols-outlined">calendar_today</span>
              </div>
              <div className="flex flex-col gap-1">
                <h2 className="text-slate-900 dark:text-white text-lg font-bold">Daily Zone</h2>
                <p className="text-slate-500 dark:text-[#92adc9] text-sm font-medium">
                  Level: <span className="text-white">{zones.daily.level}</span>
                </p>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className="size-2 rounded-full bg-green-500"></span>
                  <span className="text-green-500 text-xs font-bold uppercase">{zones.daily.status}</span>
                </div>
              </div>
            </div>
            <div className="flex flex-1 gap-4 rounded-xl border border-slate-200 dark:border-[#324d67] bg-white dark:bg-[#192633] p-5">
              <div className="flex items-center justify-center size-12 rounded-lg bg-orange-500/10 text-orange-500">
                <span className="material-symbols-outlined">schedule</span>
              </div>
              <div className="flex flex-col gap-1">
                <h2 className="text-slate-900 dark:text-white text-lg font-bold">H4 Zone</h2>
                <p className="text-slate-500 dark:text-[#92adc9] text-sm font-medium">
                  Level: <span className="text-white">{zones.h4.level}</span>
                </p>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className="size-2 rounded-full bg-orange-500"></span>
                  <span className="text-orange-500 text-xs font-bold uppercase">{zones.h4.status}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Trade Setup Card */}
          <div className="rounded-xl overflow-hidden shadow-lg bg-white dark:bg-[#192633] border border-slate-200 dark:border-[#324d67]">
            {/* Chart Mockup */}
            <div className="relative w-full h-64 bg-slate-100 dark:bg-slate-800 flex items-center justify-center overflow-hidden">
              <div className="absolute inset-0 opacity-40 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
              <div className="w-full h-full p-4 flex items-end">
                <div className="w-full h-3/4 flex items-end gap-1">
                  <div className="flex-1 bg-red-500/40 rounded-t h-[40%]"></div>
                  <div className="flex-1 bg-red-500/60 rounded-t h-[60%]"></div>
                  <div className="flex-1 bg-red-500/50 rounded-t h-[55%]"></div>
                  <div className="flex-1 bg-green-500/70 rounded-t h-[80%] border-t-2 border-green-500"></div>
                  <div className="flex-1 bg-green-500/50 rounded-t h-[65%]"></div>
                  <div className="flex-1 bg-green-500/80 rounded-t h-[90%] border-t-2 border-green-500"></div>
                  <div className="flex-1 bg-primary/40 rounded-t h-[70%] animate-pulse"></div>
                </div>
              </div>
              <div className="absolute top-4 left-4 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-sm">auto_graph</span>
                <span className="text-white text-xs font-bold">Pattern Analysis: Wedge</span>
              </div>
            </div>

            {/* Trade Details */}
            <div className="p-6 flex flex-col gap-4">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-slate-900 dark:text-white text-2xl font-bold leading-tight tracking-tight">Trade Setup</p>
                  <p className="text-primary text-sm font-semibold mt-1">Technical Pattern: {trade.pattern}</p>
                </div>
                <div className="flex flex-col items-end">
                  <span className="text-slate-400 dark:text-[#92adc9] text-xs font-medium uppercase">Risk Reward</span>
                  <span className="text-slate-900 dark:text-white text-xl font-black">{trade.riskReward}</span>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-slate-200 dark:border-[#324d67]">
                <div className="flex flex-col">
                  <span className="text-slate-500 dark:text-[#92adc9] text-xs font-medium uppercase">Entry</span>
                  <span className="text-slate-900 dark:text-white text-lg font-bold font-mono tracking-tighter">{trade.entry}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-red-500 text-xs font-medium uppercase">Stop Loss</span>
                  <span className="text-slate-900 dark:text-white text-lg font-bold font-mono tracking-tighter">{trade.stopLoss}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-green-500 text-xs font-medium uppercase">Target</span>
                  <span className="text-slate-900 dark:text-white text-lg font-bold font-mono tracking-tighter">{trade.target}</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-slate-500 dark:text-[#92adc9] text-xs font-medium uppercase">Position Size</span>
                  <span className="text-slate-900 dark:text-white text-lg font-bold font-mono tracking-tighter">{trade.positionSize}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap gap-4">
            <Button variant="danger" icon="cancel" className="flex-1 min-w-[150px] py-3">
              Close Trade
            </Button>
            <Button variant="secondary" icon="edit_square" className="flex-1 min-w-[150px] py-3">
              Modify SL
            </Button>
            <Button variant="secondary" icon="edit_square" className="flex-1 min-w-[150px] py-3">
              Modify TP
            </Button>
          </div>
        </div>

        {/* Sidebar: Timeline */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          <div className="rounded-xl bg-white dark:bg-[#192633] border border-slate-200 dark:border-[#324d67] p-6">
            <h3 className="text-slate-900 dark:text-white text-lg font-bold mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">history</span>
              Trade Timeline
            </h3>
            <div className="relative flex flex-col gap-8">
              {/* Timeline Line */}
              <div className="absolute left-[11px] top-2 bottom-2 w-0.5 bg-slate-200 dark:bg-[#324d67]"></div>
              
              {/* Timeline Items */}
              {timeline.map((item) => (
                <div key={item.id} className={`relative flex gap-4 ${item.status === 'pending' ? 'opacity-50' : ''}`}>
                  <div className={`size-6 rounded-full border-4 border-[#192633] z-10 ${
                    item.status === 'active' 
                      ? 'bg-primary shadow-[0_0_8px_rgba(19,127,236,0.6)]' 
                      : item.status === 'complete' 
                        ? 'bg-green-500' 
                        : 'bg-slate-400 dark:bg-slate-600'
                  }`}></div>
                  <div className="flex flex-col">
                    <p className={`text-sm font-bold ${item.status === 'active' ? 'text-primary' : 'text-slate-900 dark:text-white'}`}>
                      {item.title}
                    </p>
                    <p className="text-slate-500 dark:text-[#92adc9] text-xs">{item.desc}</p>
                    <p className="text-slate-400 dark:text-slate-500 text-[10px] mt-1 font-mono uppercase tracking-widest">{item.time}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* P/L Card */}
            <div className="mt-8 p-4 bg-primary/5 rounded-lg border border-primary/20">
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-bold text-primary uppercase">Current Profit/Loss</span>
                <span className="text-sm font-bold text-green-500">{trade.currentPL}</span>
              </div>
              <div className="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
                <div className="bg-primary h-full" style={{ width: `${trade.progress}%` }}></div>
              </div>
              <div className="flex justify-between text-[10px] text-slate-500 mt-2 font-bold">
                <span>STOP LOSS</span>
                <span>TAKE PROFIT</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PairDetail
