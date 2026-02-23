import { Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import PairDetail from './pages/PairDetail'
import Settings from './pages/Settings'
import Performance from './pages/Performance'
import Simulation from './pages/Simulation'

function App() {
  return (
    <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-white min-h-screen">
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="pair/:symbol" element={<PairDetail />} />
          <Route path="settings" element={<Settings />} />
          <Route path="performance" element={<Performance />} />
          <Route path="simulation" element={<Simulation />} />
        </Route>
      </Routes>
    </div>
  )
}

export default App
