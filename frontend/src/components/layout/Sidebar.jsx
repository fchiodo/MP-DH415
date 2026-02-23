import { Link, useLocation } from 'react-router-dom'
import { useApp } from '../../context/AppContext'

function Sidebar() {
  const location = useLocation()
  const { botStatus, isSimulationMode, isSidebarOpen } = useApp()

  const navItems = [
    { path: '/', label: 'Dashboard', icon: 'dashboard' },
    { path: '/performance', label: 'History', icon: 'history' },
    { path: '/simulation', label: 'Signals', icon: 'terminal' },
    { path: '/settings', label: 'Settings', icon: 'settings' },
  ]

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  return (
    <aside 
      className={`${
        isSidebarOpen ? 'w-64' : 'w-20'
      } border-r border-slate-200 dark:border-[#233648] bg-white dark:bg-background-dark flex flex-col shrink-0 h-screen sticky top-0 transition-all duration-300 ease-in-out overflow-hidden`}
    >
      {/* Logo */}
      <div className="p-4 border-b border-slate-200 dark:border-[#233648]">
        <Link to="/" className="flex items-center gap-3">
          <div className="size-10 bg-primary rounded-xl flex items-center justify-center text-white shadow-lg shadow-primary/20 shrink-0">
            <span className="material-symbols-outlined">query_stats</span>
          </div>
          <div className={`${isSidebarOpen ? 'opacity-100' : 'opacity-0 w-0'} transition-all duration-300 overflow-hidden`}>
            <h1 className="text-slate-900 dark:text-white text-lg font-bold leading-tight whitespace-nowrap">MP-DH415</h1>
            <p className="text-slate-500 dark:text-[#92adc9] text-xs font-medium whitespace-nowrap">Pro v2.0</p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3">
        <p className={`text-slate-400 dark:text-[#92adc9] text-xs font-bold uppercase tracking-wider px-3 mb-3 ${isSidebarOpen ? 'opacity-100' : 'opacity-0'} transition-opacity duration-200`}>
          Menu
        </p>
        <div className="flex flex-col gap-1">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
                isActive(item.path)
                  ? 'bg-primary/10 dark:bg-primary/20 text-primary font-bold'
                  : 'text-slate-600 dark:text-[#92adc9] hover:bg-slate-100 dark:hover:bg-[#233648] hover:text-slate-900 dark:hover:text-white'
              } ${!isSidebarOpen ? 'justify-center' : ''}`}
              title={!isSidebarOpen ? item.label : ''}
            >
              <span className={`material-symbols-outlined text-[20px] shrink-0 ${isActive(item.path) ? 'text-primary' : ''}`}>
                {item.icon}
              </span>
              <span className={`text-sm ${isSidebarOpen ? 'opacity-100' : 'opacity-0 w-0'} transition-all duration-300 overflow-hidden whitespace-nowrap`}>
                {item.label}
              </span>
              {item.path === '/simulation' && isSimulationMode && isSidebarOpen && (
                <span className="ml-auto bg-amber-500/20 text-amber-500 text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0">
                  SIM
                </span>
              )}
            </Link>
          ))}
        </div>
      </nav>

      {/* Status Card */}
      <div className={`p-3 ${isSidebarOpen ? '' : 'px-2'}`}>
        <div className={`p-3 bg-slate-50 dark:bg-[#192633] rounded-xl border border-slate-200 dark:border-[#233648] ${!isSidebarOpen ? 'flex flex-col items-center' : ''}`}>
          {isSidebarOpen ? (
            <>
              <div className="flex items-center justify-between mb-3">
                <p className="text-slate-500 dark:text-[#92adc9] text-xs font-bold uppercase tracking-wider">Status</p>
                <div className={`flex items-center gap-1.5 ${botStatus === 'running' ? 'text-accent-green' : 'text-slate-400'}`}>
                  <div className={`size-2 rounded-full ${botStatus === 'running' ? 'bg-accent-green animate-pulse' : 'bg-slate-400'}`}></div>
                  <span className="text-xs font-bold uppercase">{botStatus === 'running' ? 'On' : 'Off'}</span>
                </div>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-500 dark:text-[#92adc9]">Mode</span>
                <span className={`font-bold ${isSimulationMode ? 'text-amber-500' : 'text-accent-green'}`}>
                  {isSimulationMode ? 'Sim' : 'Live'}
                </span>
              </div>
            </>
          ) : (
            <div className={`size-3 rounded-full ${botStatus === 'running' ? 'bg-accent-green animate-pulse' : 'bg-slate-400'}`} title={botStatus === 'running' ? 'Bot Online' : 'Bot Offline'}></div>
          )}
        </div>
      </div>

      {/* User Section */}
      <div className={`p-3 border-t border-slate-200 dark:border-[#233648] ${!isSidebarOpen ? 'flex justify-center' : ''}`}>
        <div className={`flex items-center gap-3 ${!isSidebarOpen ? 'justify-center' : ''}`}>
          <div
            className="bg-center bg-no-repeat aspect-square bg-cover rounded-full size-10 border-2 border-primary/20 shrink-0"
            style={{ backgroundImage: 'url("https://lh3.googleusercontent.com/aida-public/AB6AXuC_fsD_Pe-I7FeTF6a8nJdcjMsbLRk3ZKMTF_ubZysp8xwDW2WLGgldp_CSKDYm6rFmCpRfoYCkTEdAgUMo2Kr1QcDc2lS0I-pyqdoVg3Ew4Br87Oi8IQIsT891D-_1qkv-NVhm6Vhect05gRpaRW4eIMhtM3xIIO9zu1M2mUBcKi5Ta5pc-XjhqgrhHvtKoXhcawp48LjKLLFJPvCIOv44pL1DXxyVM_FWdfaa4W_l8yhjq3As_dg5VzUYSBWtkWDsgHTETqYmD6M")' }}
          ></div>
          {isSidebarOpen && (
            <>
              <div className="flex-1 min-w-0">
                <p className="text-slate-900 dark:text-white text-sm font-bold truncate">MP-DH415</p>
                <p className="text-slate-500 dark:text-[#92adc9] text-xs truncate">admin@mpdh415.io</p>
              </div>
              <button className="text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors shrink-0">
                <span className="material-symbols-outlined text-[20px]">logout</span>
              </button>
            </>
          )}
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
