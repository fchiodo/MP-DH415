import { useApp } from '../context/AppContext'
import StatsCard from '../components/common/StatsCard'
import PairsTable from '../components/dashboard/PairsTable'
import ActivityLog from '../components/dashboard/ActivityLog'

function Dashboard() {
  const { 
    botStatus, 
    activeTrades, 
    activityLogs, 
    stats 
  } = useApp()

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white">Dashboard Overview</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
          System status: <span className={`font-bold ${botStatus === 'running' ? 'text-accent-green' : 'text-amber-500'}`}>
            {botStatus === 'running' ? 'Operational' : 'Stopped'}
          </span>
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatsCard
          title="Active Trades"
          value={stats.activeTrades}
          icon="analytics"
          iconColor="text-primary"
          trend={stats.activeTrendup}
          trendUp={true}
        />
        <StatsCard
          title="Waiting Retest"
          value={stats.waitingRetest}
          icon="hourglass_empty"
          iconColor="text-amber-500"
          trend={stats.retestTrend}
          trendUp={false}
        />
        <StatsCard
          title="Today's Profit"
          value={`+$${stats.todayProfit.toLocaleString()}`}
          icon="payments"
          iconColor="text-accent-green"
          trend={`${stats.winRateBoost} Win Rate Boost`}
          trendUp={true}
        />
      </div>

      {/* Pairs Table */}
      <PairsTable trades={activeTrades} />

      {/* Activity Log */}
      <ActivityLog logs={activityLogs} onClear={() => {}} />
    </div>
  )
}

export default Dashboard
