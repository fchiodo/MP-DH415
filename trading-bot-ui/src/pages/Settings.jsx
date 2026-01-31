import { useState, useEffect } from 'react'
import Button from '../components/common/Button'

const API_URL = 'http://localhost:5001'

// All available currency pairs
const ALL_PAIRS = [
  'EUR/USD', 'GBP/USD', 'USD/JPY', 'AUD/USD', 'USD/CAD', 'USD/CHF', 'NZD/USD',
  'EUR/JPY', 'GBP/JPY', 'AUD/JPY', 'CAD/JPY', 'CHF/JPY', 'NZD/JPY',
  'EUR/GBP', 'EUR/AUD', 'EUR/CAD', 'EUR/CHF', 'EUR/NZD',
  'GBP/AUD', 'GBP/CAD', 'GBP/CHF', 'GBP/NZD',
  'AUD/CAD', 'AUD/CHF', 'AUD/NZD',
  'CAD/CHF', 'NZD/CAD', 'NZD/CHF',
]

function Settings() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)
  const [showFxcmPassword, setShowFxcmPassword] = useState(false)
  const [showSlackToken, setShowSlackToken] = useState(false)
  
  const [config, setConfig] = useState({
    loginId: '',
    password: '',
    url: 'http://www.fxcorporate.com/Hosts.jsp',
    connection: 'Demo',
    riskPerTrade: 1.0,
    minRewardRisk: 2.0,
    referenceBalance: 10000,
    slackToken: '',
    slackChannel: '',
    executionAlerts: true,
    errorLogs: true,
    dailySummary: false,
  })

  const [activePairs, setActivePairs] = useState({})

  // Load config on mount
  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const response = await fetch(`${API_URL}/api/config`)
      const data = await response.json()
      
      setConfig({
        loginId: data.fxcm?.loginId || '',
        password: data.fxcm?.password || '',
        url: data.fxcm?.url || 'http://www.fxcorporate.com/Hosts.jsp',
        connection: data.fxcm?.connection || 'Demo',
        riskPerTrade: data.risk?.riskPerTrade || 1.0,
        minRewardRisk: data.risk?.minRewardRisk || 2.0,
        referenceBalance: data.risk?.referenceBalance || 10000,
        slackToken: data.slack?.botToken || '',
        slackChannel: data.slack?.channel || '',
        executionAlerts: true,
        errorLogs: true,
        dailySummary: false,
      })
      
      // Set active pairs
      const pairsObj = {}
      ALL_PAIRS.forEach(pair => {
        pairsObj[pair] = data.activePairs?.includes(pair) || false
      })
      setActivePairs(pairsObj)
      
      setLoading(false)
    } catch (error) {
      console.error('Failed to load config:', error)
      setMessage({ type: 'error', text: 'Failed to load configuration. Is the API server running?' })
      setLoading(false)
    }
  }

  const saveConfig = async () => {
    setSaving(true)
    setMessage(null)
    
    try {
      const activePairsList = Object.entries(activePairs)
        .filter(([, isActive]) => isActive)
        .map(([pair]) => pair)
      
      const response = await fetch(`${API_URL}/api/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fxcm: {
            loginId: config.loginId,
            password: config.password,
            url: config.url,
            connection: config.connection,
          },
          risk: {
            riskPerTrade: config.riskPerTrade,
            minRewardRisk: config.minRewardRisk,
            referenceBalance: config.referenceBalance,
          },
          slack: {
            botToken: config.slackToken,
            channel: config.slackChannel,
          },
          activePairs: activePairsList,
        }),
      })
      
      const data = await response.json()
      
      if (data.success) {
        setMessage({ type: 'success', text: 'Configuration saved successfully!' })
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to save configuration' })
      }
    } catch (error) {
      console.error('Failed to save config:', error)
      setMessage({ type: 'error', text: 'Failed to save configuration. Is the API server running?' })
    } finally {
      setSaving(false)
    }
  }

  const handlePairToggle = (pair) => {
    setActivePairs(prev => ({ ...prev, [pair]: !prev[pair] }))
  }

  const handleToggle = (field) => {
    setConfig(prev => ({ ...prev, [field]: !prev[field] }))
  }

  const [testingFxcm, setTestingFxcm] = useState(false)
  const [testingSlack, setTestingSlack] = useState(false)

  const testFxcmConnection = async () => {
    setTestingFxcm(true)
    setMessage({ type: 'info', text: 'Testing FXCM connection...' })
    
    try {
      const response = await fetch(`${API_URL}/api/test/fxcm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          loginId: config.loginId,
          password: config.password,
          url: config.url,
          connection: config.connection,
        }),
      })
      
      const data = await response.json()
      
      if (data.success) {
        let successMsg = `FXCM connection successful! Server: ${data.server}`
        if (data.account) {
          successMsg += ` | Balance: $${data.account.balance?.toFixed(2) || 'N/A'}`
        }
        setMessage({ type: 'success', text: successMsg })
      } else {
        setMessage({ type: 'error', text: data.error || 'Connection failed' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to test connection. Is the API server running?' })
    } finally {
      setTestingFxcm(false)
    }
  }

  const testSlackConnection = async () => {
    setTestingSlack(true)
    setMessage({ type: 'info', text: 'Testing Slack connection...' })
    
    try {
      const response = await fetch(`${API_URL}/api/test/slack`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          botToken: config.slackToken,
          channel: config.slackChannel,
        }),
      })
      
      const data = await response.json()
      
      if (data.success) {
        let successMsg = `Slack connected as @${data.bot?.name || 'bot'}`
        if (data.channel) {
          successMsg += data.channel.accessible 
            ? ` | Channel ${data.channel.name} accessible` 
            : ` | Warning: ${data.warning || 'Channel not accessible'}`
        }
        setMessage({ 
          type: data.warning ? 'warning' : 'success', 
          text: successMsg 
        })
      } else {
        setMessage({ type: 'error', text: data.error || 'Connection failed' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to test Slack. Is the API server running?' })
    } finally {
      setTestingSlack(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500 dark:text-[#92adc9]">Loading configuration...</div>
      </div>
    )
  }

  return (
    <div className="flex flex-col max-w-[960px] mx-auto">
      {/* Page Header */}
      <div className="flex flex-wrap justify-between items-end gap-3 mb-8">
        <div className="flex flex-col gap-2">
          <h1 className="text-slate-900 dark:text-white text-2xl font-extrabold leading-tight">Bot Configuration</h1>
          <p className="text-slate-500 dark:text-[#92adc9] text-sm font-normal leading-normal">
            Manage your FXCM connection, risk parameters, and notifications.
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="primary" onClick={saveConfig} disabled={saving}>
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      {/* Message Alert */}
      {message && (
        <div className={`mb-6 p-4 rounded-lg flex items-center gap-3 ${
          message.type === 'success' ? 'bg-green-500/10 border border-green-500/20 text-green-500' :
          message.type === 'error' ? 'bg-red-500/10 border border-red-500/20 text-red-500' :
          message.type === 'warning' ? 'bg-amber-500/10 border border-amber-500/20 text-amber-500' :
          'bg-primary/10 border border-primary/20 text-primary'
        }`}>
          <span className="material-symbols-outlined">
            {message.type === 'success' ? 'check_circle' : 
             message.type === 'error' ? 'error' : 
             message.type === 'warning' ? 'warning' : 'info'}
          </span>
          <p className="text-sm font-medium">{message.text}</p>
        </div>
      )}

      {/* FXCM Connection Section */}
      <div className="mb-10">
        <div className="flex items-center justify-between px-4 pb-3 pt-5">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">api</span>
            <h2 className="text-slate-900 dark:text-white text-[22px] font-bold leading-tight tracking-[-0.015em]">FXCM Connection</h2>
          </div>
          <Button 
            variant="outline" 
            onClick={testFxcmConnection} 
            disabled={testingFxcm || !config.loginId || !config.password}
          >
            {testingFxcm ? 'Testing...' : 'Test Connection'}
          </Button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-slate-50 dark:bg-[#192633]/50 rounded-xl border border-slate-200 dark:border-[#233648]">
          <div className="flex flex-col gap-4">
            <label className="flex flex-col flex-1">
              <p className="text-slate-700 dark:text-white text-sm font-medium pb-2">Login ID</p>
              <input
                className="w-full rounded-lg text-slate-900 dark:text-white border border-slate-300 dark:border-[#324d67] bg-white dark:bg-[#101922] focus:border-primary focus:ring-1 focus:ring-primary h-12 p-4 text-sm font-normal"
                placeholder="FXCM Account Number"
                type="text"
                value={config.loginId}
                onChange={(e) => setConfig(prev => ({ ...prev, loginId: e.target.value }))}
              />
            </label>
            <label className="flex flex-col flex-1">
              <p className="text-slate-700 dark:text-white text-sm font-medium pb-2">Password</p>
              <div className="relative">
                <input
                  className="w-full rounded-lg text-slate-900 dark:text-white border border-slate-300 dark:border-[#324d67] bg-white dark:bg-[#101922] focus:border-primary focus:ring-1 focus:ring-primary h-12 p-4 pr-12 text-sm font-normal"
                  placeholder="••••••••"
                  type={showFxcmPassword ? 'text' : 'password'}
                  value={config.password}
                  onChange={(e) => setConfig(prev => ({ ...prev, password: e.target.value }))}
                />
                <button
                  type="button"
                  onClick={() => setShowFxcmPassword(!showFxcmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors"
                >
                  <span className="material-symbols-outlined text-[20px]">
                    {showFxcmPassword ? 'visibility_off' : 'visibility'}
                  </span>
                </button>
              </div>
            </label>
          </div>
          <div className="flex flex-col gap-4">
            <label className="flex flex-col flex-1">
              <p className="text-slate-700 dark:text-white text-sm font-medium pb-2">Server</p>
              <select
                className="w-full rounded-lg text-slate-900 dark:text-white border border-slate-300 dark:border-[#324d67] bg-white dark:bg-[#101922] focus:border-primary focus:ring-1 focus:ring-primary h-12 px-4 text-sm font-normal"
                value={config.connection}
                onChange={(e) => setConfig(prev => ({ ...prev, connection: e.target.value }))}
              >
                <option value="Demo">Demo (Real-time)</option>
                <option value="Real">Real (Production)</option>
              </select>
            </label>
            <div className="flex flex-col justify-end h-full pb-1">
              <div className="bg-primary/10 border border-primary/20 p-3 rounded-lg flex items-center gap-3">
                <span className="material-symbols-outlined text-primary">info</span>
                <p className="text-slate-500 dark:text-[#92adc9] text-xs leading-tight">
                  API access must be enabled in your FXCM dashboard before connecting.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Risk Management Section */}
      <div className="mb-10">
        <div className="flex items-center gap-2 px-4 pb-3 pt-5">
          <span className="material-symbols-outlined text-primary">security</span>
          <h2 className="text-slate-900 dark:text-white text-[22px] font-bold leading-tight tracking-[-0.015em]">Risk Management</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-slate-50 dark:bg-[#192633]/50 rounded-xl border border-slate-200 dark:border-[#233648]">
          <label className="flex flex-col">
            <p className="text-slate-700 dark:text-white text-sm font-medium pb-2">Risk per Trade (%)</p>
            <input
              className="w-full rounded-lg text-slate-900 dark:text-white border border-slate-300 dark:border-[#324d67] bg-white dark:bg-[#101922] focus:border-primary h-12 p-4 text-sm font-normal"
              type="number"
              step="0.1"
              value={config.riskPerTrade}
              onChange={(e) => setConfig(prev => ({ ...prev, riskPerTrade: parseFloat(e.target.value) }))}
            />
          </label>
          <label className="flex flex-col">
            <p className="text-slate-700 dark:text-white text-sm font-medium pb-2">Min Reward:Risk Ratio</p>
            <input
              className="w-full rounded-lg text-slate-900 dark:text-white border border-slate-300 dark:border-[#324d67] bg-white dark:bg-[#101922] focus:border-primary h-12 p-4 text-sm font-normal"
              type="number"
              step="0.5"
              value={config.minRewardRisk}
              onChange={(e) => setConfig(prev => ({ ...prev, minRewardRisk: parseFloat(e.target.value) }))}
            />
          </label>
          <label className="flex flex-col">
            <p className="text-slate-700 dark:text-white text-sm font-medium pb-2">Reference Balance ($)</p>
            <input
              className="w-full rounded-lg text-slate-900 dark:text-white border border-slate-300 dark:border-[#324d67] bg-white dark:bg-[#101922] focus:border-primary h-12 p-4 text-sm font-normal"
              type="number"
              value={config.referenceBalance}
              onChange={(e) => setConfig(prev => ({ ...prev, referenceBalance: parseFloat(e.target.value) }))}
            />
          </label>
        </div>
      </div>

      {/* Active Pairs Section */}
      <div className="mb-10">
        <div className="flex items-center gap-2 px-4 pb-3 pt-5">
          <span className="material-symbols-outlined text-primary">currency_exchange</span>
          <h2 className="text-slate-900 dark:text-white text-[22px] font-bold leading-tight tracking-[-0.015em]">Active Currency Pairs</h2>
          <span className="ml-2 text-xs text-slate-500 dark:text-[#92adc9]">
            ({Object.values(activePairs).filter(Boolean).length} selected)
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 p-4 bg-slate-50 dark:bg-[#192633]/50 rounded-xl border border-slate-200 dark:border-[#233648]">
          {Object.entries(activePairs).map(([pair, isActive]) => (
            <label
              key={pair}
              className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                isActive 
                  ? 'bg-primary/10 dark:bg-primary/20 border border-primary/30' 
                  : 'hover:bg-slate-100 dark:hover:bg-[#233648] border border-transparent'
              }`}
            >
              <input
                type="checkbox"
                checked={isActive}
                onChange={() => handlePairToggle(pair)}
                className="w-4 h-4 rounded text-primary bg-white dark:bg-[#101922] border-slate-300 dark:border-[#324d67] focus:ring-primary focus:ring-offset-0"
              />
              <span className={`text-sm font-medium ${isActive ? 'text-primary' : 'text-slate-900 dark:text-white'}`}>
                {pair}
              </span>
            </label>
          ))}
        </div>
      </div>

      {/* Slack Notifications Section */}
      <div className="mb-10">
        <div className="flex items-center justify-between px-4 pb-3 pt-5">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">chat</span>
            <h2 className="text-slate-900 dark:text-white text-[22px] font-bold leading-tight tracking-[-0.015em]">Slack Notifications</h2>
          </div>
          <Button 
            variant="outline" 
            onClick={testSlackConnection} 
            disabled={testingSlack || !config.slackToken}
          >
            {testingSlack ? 'Testing...' : 'Test Slack'}
          </Button>
        </div>
        <div className="p-4 bg-slate-50 dark:bg-[#192633]/50 rounded-xl border border-slate-200 dark:border-[#233648]">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <label className="flex flex-col">
              <p className="text-slate-700 dark:text-white text-sm font-medium pb-2">Bot Token</p>
              <div className="relative">
                <input
                  className="w-full rounded-lg text-slate-900 dark:text-white border border-slate-300 dark:border-[#324d67] bg-white dark:bg-[#101922] focus:border-primary h-12 p-4 pr-12 text-sm font-normal font-mono"
                  placeholder="xoxb-your-token"
                  type={showSlackToken ? 'text' : 'password'}
                  value={config.slackToken}
                  onChange={(e) => setConfig(prev => ({ ...prev, slackToken: e.target.value }))}
                />
                <button
                  type="button"
                  onClick={() => setShowSlackToken(!showSlackToken)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors"
                >
                  <span className="material-symbols-outlined text-[20px]">
                    {showSlackToken ? 'visibility_off' : 'visibility'}
                  </span>
                </button>
              </div>
            </label>
            <label className="flex flex-col">
              <p className="text-slate-700 dark:text-white text-sm font-medium pb-2">Channel Name</p>
              <input
                className="w-full rounded-lg text-slate-900 dark:text-white border border-slate-300 dark:border-[#324d67] bg-white dark:bg-[#101922] focus:border-primary h-12 p-4 text-sm font-normal"
                placeholder="#trading-alerts"
                type="text"
                value={config.slackChannel}
                onChange={(e) => setConfig(prev => ({ ...prev, slackChannel: e.target.value }))}
              />
            </label>
          </div>
          <div className="space-y-4 pt-4 border-t border-slate-200 dark:border-[#233648]">
            {/* Toggle Switches */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-900 dark:text-white font-medium text-sm">Execution Alerts</p>
                <p className="text-slate-500 dark:text-[#92adc9] text-xs">Notify when a trade is opened or closed</p>
              </div>
              <button
                onClick={() => handleToggle('executionAlerts')}
                className={`w-12 h-6 rounded-full relative transition-colors ${config.executionAlerts ? 'bg-primary' : 'bg-slate-300 dark:bg-[#324d67]'}`}
              >
                <span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${config.executionAlerts ? 'right-1' : 'left-1'}`}></span>
              </button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-900 dark:text-white font-medium text-sm">Error Logs</p>
                <p className="text-slate-500 dark:text-[#92adc9] text-xs">Notify on connection drops or critical errors</p>
              </div>
              <button
                onClick={() => handleToggle('errorLogs')}
                className={`w-12 h-6 rounded-full relative transition-colors ${config.errorLogs ? 'bg-primary' : 'bg-slate-300 dark:bg-[#324d67]'}`}
              >
                <span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${config.errorLogs ? 'right-1' : 'left-1'}`}></span>
              </button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-900 dark:text-white font-medium text-sm">Daily Summary</p>
                <p className="text-slate-500 dark:text-[#92adc9] text-xs">Send PnL summary at market close</p>
              </div>
              <button
                onClick={() => handleToggle('dailySummary')}
                className={`w-12 h-6 rounded-full relative transition-colors ${config.dailySummary ? 'bg-primary' : 'bg-slate-300 dark:bg-[#324d67]'}`}
              >
                <span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-all ${config.dailySummary ? 'right-1' : 'left-1'}`}></span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Help Card */}
      <div className="p-4">
        <div className="flex flex-col items-stretch justify-start rounded-xl md:flex-row md:items-start shadow-[0_0_4px_rgba(0,0,0,0.1)] bg-white dark:bg-[#192633] border border-slate-200 dark:border-transparent overflow-hidden">
          <div
            className="w-full md:w-1/3 bg-center bg-no-repeat aspect-video bg-cover"
            style={{ backgroundImage: 'linear-gradient(rgba(19, 127, 236, 0.2), rgba(16, 25, 34, 0.8)), url("https://lh3.googleusercontent.com/aida-public/AB6AXuD3PKNULcTTJfkdCzriLe8meV6AR67NCeyhQwgz_wMSCgszYmXcWvelnHMyXitPNcEfkERQ3ytNupV79u47K_t1y8h_iSMI3I6EOGWCA_uwvUmv0vbfNbrmOhLK4PvsjhX2Owg600Y16f0VxT2AJZ8taqpqfZPngo9-bKGKmkqExPAoxuN-lexkhZ_eKhQlZr0raDX-i9MFiXjwMeepRqcirx6adhvL90TEfZeJ6E-NElvY93JjsrKM5JI_9nfe8TNvzSPC5dtnmOk")' }}
          ></div>
          <div className="flex w-full min-w-72 grow flex-col items-stretch justify-center gap-2 py-6 px-6">
            <p className="text-slate-900 dark:text-white text-lg font-bold leading-tight tracking-[-0.015em]">Need assistance?</p>
            <p className="text-slate-500 dark:text-[#92adc9] text-sm font-normal leading-normal">
              Our technical documentation covers API setup, risk modeling, and notification integration in detail.
            </p>
            <div className="pt-2">
              <a className="text-primary hover:underline text-sm font-bold flex items-center gap-1" href="#">
                View Documentation <span className="material-symbols-outlined text-sm">open_in_new</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Settings
