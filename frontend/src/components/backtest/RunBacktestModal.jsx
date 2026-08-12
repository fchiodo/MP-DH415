import { useState } from 'react'
import Button from '../common/Button'
import { API_URL } from '../../config'

// Same 28-pair universe used by the MP-DH415-BT batch scripts
export const ALL_PAIRS = [
  'EUR/USD', 'AUD/USD', 'GBP/USD', 'USD/JPY', 'GBP/JPY', 'USD/CAD', 'EUR/JPY',
  'USD/CHF', 'NZD/USD', 'AUD/JPY', 'EUR/GBP', 'CAD/JPY', 'GBP/AUD', 'AUD/CAD',
  'EUR/AUD', 'EUR/CAD', 'GBP/CAD', 'EUR/NZD', 'AUD/NZD', 'GBP/CHF', 'GBP/NZD',
  'CHF/JPY', 'EUR/CHF', 'AUD/CHF', 'CAD/CHF', 'NZD/CAD', 'NZD/CHF', 'NZD/JPY',
]

const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: CURRENT_YEAR - 2021 + 1 }, (_, i) => CURRENT_YEAR - i)

function RunBacktestModal({ isOpen, onClose, onStarted }) {
  const [year, setYear] = useState(CURRENT_YEAR)
  const [selectedPairs, setSelectedPairs] = useState(new Set(['EUR/USD']))
  const [clean, setClean] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  if (!isOpen) return null

  const togglePair = (pair) => {
    setSelectedPairs((prev) => {
      const next = new Set(prev)
      if (next.has(pair)) next.delete(pair)
      else next.add(pair)
      return next
    })
  }

  const startBacktest = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const response = await fetch(`${API_URL}/api/backtest/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          year,
          pairs: [...selectedPairs],
          clean,
        }),
      })
      const data = await response.json()
      if (!response.ok || !data.success) {
        throw new Error(data.error || `HTTP ${response.status}`)
      }
      onStarted?.(year)
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose}></div>

      {/* Dialog */}
      <div className="relative bg-white dark:bg-[#192633] border border-slate-200 dark:border-[#324d67] rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-slate-200 dark:border-[#324d67] flex justify-between items-center shrink-0">
          <div className="flex items-center gap-3">
            <div className="size-10 bg-primary/10 rounded-xl flex items-center justify-center text-primary shrink-0">
              <span className="material-symbols-outlined">science</span>
            </div>
            <div>
              <h3 className="font-bold text-lg text-slate-900 dark:text-white">Run Backtest</h3>
              <p className="text-xs text-slate-500 dark:text-[#92adc9]">
                MP-DH415-BT engine — candle-by-candle simulation on FXCM history
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 flex flex-col gap-6 overflow-y-auto">
          {/* Year */}
          <div className="flex flex-col gap-2">
            <label className="text-slate-500 dark:text-[#92adc9] text-xs font-bold uppercase tracking-wider">
              Year
            </label>
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="h-10 rounded-lg px-3 text-sm font-medium bg-slate-100 dark:bg-[#233648] text-slate-900 dark:text-white border-transparent focus:border-primary focus:ring-primary cursor-pointer w-40"
            >
              {YEARS.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <p className="text-xs text-slate-400">
              Full year: 01.01.{year} → 12.31.{year}
              {year === CURRENT_YEAR ? ' (up to the latest available candle)' : ''}
            </p>
          </div>

          {/* Pairs */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <label className="text-slate-500 dark:text-[#92adc9] text-xs font-bold uppercase tracking-wider">
                Pairs <span className="font-normal normal-case">({selectedPairs.size} selected)</span>
              </label>
              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedPairs(new Set(ALL_PAIRS))}
                  className="text-xs font-bold text-primary hover:text-primary/80"
                >
                  Select all
                </button>
                <span className="text-slate-300 dark:text-[#324d67]">|</span>
                <button
                  onClick={() => setSelectedPairs(new Set())}
                  className="text-xs font-bold text-primary hover:text-primary/80"
                >
                  Clear
                </button>
              </div>
            </div>
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
              {ALL_PAIRS.map((pair) => {
                const isSelected = selectedPairs.has(pair)
                return (
                  <label
                    key={pair}
                    className={`flex items-center justify-center px-2 py-2 rounded-lg border cursor-pointer text-sm font-medium transition-colors select-none ${
                      isSelected
                        ? 'border-primary bg-primary/10 text-primary font-bold'
                        : 'border-slate-200 dark:border-[#324d67] text-slate-600 dark:text-[#92adc9] hover:border-primary/50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => togglePair(pair)}
                      className="hidden"
                    />
                    {pair}
                  </label>
                )
              })}
            </div>
          </div>

          {/* Clean option */}
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={clean}
              onChange={(e) => setClean(e.target.checked)}
              className="mt-0.5 w-4 h-4 rounded text-primary bg-slate-100 dark:bg-[#233648] border-slate-300 dark:border-[#324d67] focus:ring-primary"
            />
            <div>
              <p className="text-sm font-bold text-slate-900 dark:text-white">
                Clear existing trades for the selected pairs first
              </p>
              <p className="text-xs text-slate-500 dark:text-[#92adc9]">
                Recommended: re-running a pair without clearing duplicates its trades in the Latest database.
              </p>
            </div>
          </label>

          {/* Info box */}
          <div className="p-4 rounded-lg bg-primary/5 border border-primary/20 flex gap-3">
            <span className="material-symbols-outlined text-primary shrink-0">info</span>
            <div className="text-sm text-slate-600 dark:text-slate-400 space-y-1">
              <p>The engine logs in to FXCM (credentials from Settings), downloads D1/H4/m15 history and simulates the strategy candle by candle.</p>
              <p>Expect <strong>5–15 minutes per pair</strong> for a full year. Pairs run sequentially; results appear in the <strong>Latest</strong> database and progress is shown in the Backtest Log below.</p>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 flex gap-3">
              <span className="material-symbols-outlined text-rose-500 shrink-0">error</span>
              <p className="text-sm text-rose-500 break-words">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-200 dark:border-[#324d67] flex justify-end gap-3 shrink-0">
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            icon={submitting ? 'progress_activity' : 'rocket_launch'}
            onClick={startBacktest}
            disabled={submitting || selectedPairs.size === 0}
          >
            {submitting ? 'Starting...' : `Start Backtest (${selectedPairs.size})`}
          </Button>
        </div>
      </div>
    </div>
  )
}

export default RunBacktestModal
