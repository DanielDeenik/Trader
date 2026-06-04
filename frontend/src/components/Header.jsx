import { useAuth } from '../contexts/AuthContext'
import { AlertBell } from './AlertBell'

export function Header({ title, alerts = [], onClearAlerts = () => {} }) {
  const { user, logout } = useAuth()

  return (
    <div className="bg-[#111827]/60 backdrop-blur-xl border-b border-white/[0.06] px-6 py-4 flex items-center justify-between">
      <h1 className="text-base font-semibold text-white">{title}</h1>
      <div className="flex items-center gap-4">
        <AlertBell alerts={alerts} onClearAll={onClearAlerts} />
        <div className="h-5 w-px bg-white/[0.06]" />
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-full bg-emerald-400/10 border border-emerald-400/30 flex items-center justify-center text-[11px] text-emerald-400 font-semibold">
            {(user?.display_name || user?.email || 'U')[0].toUpperCase()}
          </div>
          <span className="text-[13px] text-gray-300">{user?.display_name || user?.email || 'User'}</span>
        </div>
        <button
          onClick={logout}
          className="text-[13px] text-gray-500 hover:text-red-400 transition-colors duration-150 px-2 py-1 rounded hover:bg-white/[0.04]"
        >
          Sign out
        </button>
      </div>
    </div>
  )
}
