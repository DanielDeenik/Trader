import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

const SidebarIcon = ({ name, className = '' }) => {
  const baseProps = {
    className: `w-4 h-4 ${className}`,
    viewBox: '0 0 16 16',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: '1.5',
    strokeLinecap: 'round',
    strokeLinejoin: 'round'
  }

  const icons = {
    logo: <svg {...baseProps} viewBox="0 0 16 16"><path d="M8 2L13 5v6L8 14L3 11V5L8 2Z" strokeWidth="1.3" /><path d="M8 7L10.5 8.75M8 7L5.5 8.75" /></svg>,
    dashboard: <svg {...baseProps}><rect x="2" y="2" width="12" height="12" rx="1" /><path d="M2 7h12M7 2v12" /></svg>,
    tickers: <svg {...baseProps}><path d="M2 13l3-4 2 2 5-6 4 5" /><circle cx="13" cy="3" r="1" /></svg>,
    signals: <svg {...baseProps}><path d="M2 10l3-3 3 2 4-4M2 2h12v12H2z" /></svg>,
    mosaic: <svg {...baseProps}><rect x="2" y="2" width="4" height="4" /><rect x="7" y="2" width="4" height="4" /><rect x="2" y="7" width="4" height="4" /><rect x="7" y="7" width="4" height="4" /><rect x="12" y="2" width="2" height="4" /><rect x="12" y="7" width="2" height="4" /></svg>,
    thesis: <svg {...baseProps}><path d="M2 3h12M2 6h12M2 9h12M2 12h12" strokeWidth="1.2" /></svg>,
    decision: <svg {...baseProps}><circle cx="8" cy="8" r="6" /><path d="M8 5v6M5 8h6" /></svg>,
    portfolio: <svg {...baseProps}><path d="M3 5h10v8H3zM6 5V3h4v2" /><path d="M5 9h2m2 0h2" /></svg>,
    gate: <svg {...baseProps}><path d="M2 5h12M2 11h12M4 2v12M12 2v12" /></svg>,
    tasks: <svg {...baseProps}><rect x="2" y="3" width="12" height="10" rx="1" /><path d="M5 6h6M5 9h6M5 12h3" /></svg>,
    radar: <svg {...baseProps}><circle cx="8" cy="8" r="6" strokeWidth="1" /><circle cx="8" cy="8" r="3" strokeWidth="1" /><path d="M8 2v12M2 8h12" strokeWidth="0.8" /><circle cx="10" cy="5" r="1" fill="currentColor" stroke="none" /></svg>,
    trends: <svg {...baseProps}><path d="M2 12l4-4 3 2 5-6" /><path d="M11 4h3v3" /></svg>,
    pipeline: <svg {...baseProps}><circle cx="3" cy="8" r="1.5" /><circle cx="8" cy="4" r="1.5" /><circle cx="8" cy="12" r="1.5" /><circle cx="13" cy="8" r="1.5" /><path d="M4.5 7.2L6.5 4.8M4.5 8.8L6.5 11.2M9.5 4.8L11.5 7.2M9.5 11.2L11.5 8.8" /></svg>,
    settings: <svg {...baseProps}><circle cx="8" cy="8" r="2" /><path d="M8 2v2.5M8 11.5v2M14 8h-2.5M3.5 8H2M12.5 3.5l-1.8 1.8M5.3 11.7l-1.8 1.8M12.5 12.5l-1.8-1.8M5.3 4.3l-1.8-1.8" /></svg>,
  }

  return icons[name] || null
}

export function Sidebar() {
  const location = useLocation()
  const [isCollapsed, setIsCollapsed] = useState(false)

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname === path || location.pathname.startsWith(path + '/')
  }

  const NavItem = ({ icon, label, path }) => {
    const active = isActive(path)
    return (
      <Link
        to={path}
        className={`flex items-center gap-3 px-3 py-2 text-[13px] transition-all duration-150 rounded relative group ${
          active
            ? 'text-emerald-400 bg-emerald-400/[0.08]'
            : 'text-gray-400 hover:bg-white/[0.04]'
        }`}
      >
        <div className={`flex-shrink-0 ${active ? 'text-emerald-400' : 'text-gray-500 group-hover:text-gray-400'}`}>
          <SidebarIcon name={icon} />
        </div>
        {!isCollapsed && <span className="flex-1 truncate">{label}</span>}
        {active && <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-emerald-400" />}
      </Link>
    )
  }

  const SectionLabel = ({ children }) => (
    !isCollapsed && <div className="px-3 py-2 mt-4 first:mt-0 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">{children}</div>
  )

  return (
    <aside className={`flex flex-col bg-[#0a0f1a] border-r border-white/[0.06] h-screen transition-all duration-150 ${isCollapsed ? 'w-16' : 'w-56'}`}>
      {/* Brand Header */}
      <div className="flex items-center gap-3 px-3 py-4 border-b border-white/[0.06]">
        <div className="flex-shrink-0">
          <SidebarIcon name="logo" className="w-5 h-5 text-emerald-400" />
        </div>
        {!isCollapsed && (
          <div className="flex-1 min-w-0">
            <div className="text-[13px] font-semibold text-white">Social Arb</div>
            <div className="text-[11px] text-gray-500">Information Arbitrage</div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto scrollbar-hide px-2 py-3">
        <SectionLabel>Discovery</SectionLabel>
        <div className="space-y-1">
          <NavItem icon="radar" label="Trend Radar" path="/" />
          <NavItem icon="trends" label="Similar Trends" path="/trends" />
          <NavItem icon="tickers" label="Tickers" path="/tickers" />
        </div>

        <SectionLabel>Cognitive Layers</SectionLabel>
        <div className="space-y-1">
          <NavItem icon="signals" label="L1 Signal Radar" path="/signals" />
          <NavItem icon="mosaic" label="L2 Mosaic Cards" path="/mosaics" />
          <NavItem icon="thesis" label="L3 Thesis Forge" path="/theses" />
          <NavItem icon="decision" label="L4 Decisions" path="/decisions" />
          <NavItem icon="portfolio" label="L5 Portfolio" path="/positions" />
        </div>

        <SectionLabel>Operations</SectionLabel>
        <div className="space-y-1">
          <NavItem icon="gate" label="HITL Gate" path="/gate/review" />
          <NavItem icon="tasks" label="Task Queue" path="/tasks" />
          <NavItem icon="pipeline" label="Agent Pipeline" path="/pipeline" />
          <NavItem icon="settings" label="Settings" path="/settings" />
        </div>
      </nav>

      {/* Footer */}
      <div className="border-t border-white/[0.06] px-3 py-3">
        <div className="flex items-center gap-2 text-[11px] text-gray-500">
          <div className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-emerald-400" />
          {!isCollapsed && (
            <>
              <span>Connected</span>
              <span className="flex-1 text-right">v0.1.0</span>
            </>
          )}
        </div>
      </div>

      {/* Collapse Toggle */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="m-2 p-2 text-gray-500 hover:text-gray-400 hover:bg-white/[0.04] rounded transition-all duration-150"
        title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          {isCollapsed ? (
            <path d="M6 3l4 5-4 5" />
          ) : (
            <path d="M10 3l-4 5 4 5" />
          )}
        </svg>
      </button>
    </aside>
  )
}
