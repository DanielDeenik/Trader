import { Link, useLocation } from 'react-router-dom'

const navItems = [
  { path: '/', label: 'Overview', icon: '◉' },
  { path: '/tickers', label: 'Tickers', icon: '⊞' },
  { path: '/signals', label: 'L1: Signal Radar', icon: '◈' },
  { path: '/gate/review', label: 'HITL Gate Review', icon: '⊘' },
  { path: '/mosaics', label: 'L2: Mosaic Cards', icon: '◆' },
  { path: '/theses', label: 'L3: Thesis Forge', icon: '◇' },
  { path: '/decisions', label: 'L4: Decisions', icon: '▷' },
  { path: '/positions', label: 'L5: Portfolio', icon: '▣' },
  { path: '/tasks', label: 'Task Queue', icon: '⟳' },
]

export function Sidebar() {
  const location = useLocation()

  return (
    <div className="w-56 bg-gray-800 border-r border-gray-700 flex flex-col h-screen shrink-0">
      <div className="px-4 py-4 border-b border-gray-700">
        <h2 className="font-bold text-emerald-400 text-sm">SOCIAL ARB</h2>
        <p className="text-xs text-gray-500 mt-1">Information Arbitrage</p>
      </div>
      <nav className="flex-1 overflow-y-auto py-2">
        {navItems.map(({ path, label, icon }) => (
          <Link
            key={path}
            to={path}
            className={`block px-4 py-2 text-xs no-underline transition-colors ${
              location.pathname === path || (path !== '/' && location.pathname.startsWith(path))
                ? 'bg-gray-700 text-white'
                : 'text-gray-400 hover:bg-gray-700/50 hover:text-gray-200'
            }`}
          >
            <span className="mr-2">{icon}</span>{label}
          </Link>
        ))}
      </nav>
      <div className="px-4 py-3 border-t border-gray-700 text-xs text-gray-500">v2.0.0</div>
    </div>
  )
}
