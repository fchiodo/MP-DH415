import { Outlet } from 'react-router-dom'
import Header from './Header'
import Sidebar from './Sidebar'

function Layout() {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto bg-slate-50 dark:bg-background-dark">
          <div className="max-w-[1400px] w-full mx-auto p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export default Layout
