import { Link, useLocation } from 'react-router-dom'

const navSections = [
  {
    title: 'Dashboard',
    items: [
      { path: '/', label: 'Overview', icon: '◉' },
      { path: '/tickers', label: 'Tickers', icon: '⊞' },
    ]
  },
  {
    title: 'Cognitive Layers',
    items: [
      { path: '/signals', label: 'L1 Signal Radar', icon: '◈' },
      { path: '/mosaics', label: 'L2 Mosaic Cards', icon: '◆' },
      { path: '/theses', label: 'L3 Thesis Forge', icon: '◇' },
      { path: '/decisions', label: 'L4 Decisions', icon: '▷' },
      { path: '/positions', label: 'L5 Portfolio', icon: '▣' },
    ]
  },
  {
    title: 'Operations',
    items: [
      { path: '/gate/review', label: 'HITL Gate', icon: '⊘' },
      { path: '/tasks', label: 'Task Queue', icon: '⟳' },
      { path: '/settings', label: 'Settings', icon: '⚙' },
    ]
  }
]

export function Sidebar() {
  const location = useLocation()

  function isActive(path) {
    if (path === '/') return location.pathname === '/'
    return location.pathname === path || location.pathname.startsWith(path + '/')
  }

  return (
    <div className="w-56 bg-gray-800 border-r border-gray-700/50 flex flex-col h-screen shrink-0">
      {/* Brand */}
      <div className="px-4 py-4 border-b border-gray-700/50">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
            <svg width="14" height="14" viewBox="0 0 32 32" fill="none">
              <path d="M16 3L28 9V23L16 29L4 23V9L16 3Z" stroke="#10b981" strokeWidth="2.5" fill="none"/>
              <circle cx="16" cy="16" r="4" fill="#10b981" opacity="0.6"/>
            </svg>
          </div>
          <div>
            <h2 className="font-bold text-emerald-400 text-sm leading-none">Social Arb</h2>
            <p className="text-[10px] text-gray-500 mt-0.5">Information Arbitrage</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-2 px-2">
        {navSections.map((section, idx) => (
          <div key={section.title} className={idx > 0 ? 'mt-4' : ''}>
            <div className="px-2 mb-1">
              <span className="text-[10px] font-medium text-gray-500 uppercase tracking-widest">{section.title}</span>
            </div>
            {section.items.map(({ path, label, icon }) => (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-2 px-2 py-1.5 rounded-md text-xs no-underline transition-all duration-100 mb-0.5 ${
                  isActive(path)
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'text-gray-400 hover:bg-gray-700/40 hover:text-gray-200 border border-transparent'
                }`}
              >
                <span className="text-[11px] w-4 text-center opacity-70">{icon}</span>
                <span>{label}</span>
              </Link>
            ))}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-gray-700/50">
        <div className="flex items-center justify-between text-[10px] text-gray-500">
          <span>Social Arb v2.0</span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            Live
          </span>
        </div>
      </div>
    </div>
  )
}
