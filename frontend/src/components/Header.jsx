import { useAuth } from '../contexts/AuthContext'
import { AlertBell } from './AlertBell'

export function Header({ title, alerts = [], onClearAlerts = () => {} }) {
  const { user, logout } = useAuth()

  return (
    <div className="border-b border-gray-700/50 px-6 py-3 flex items-center justify-between bg-gray-800/50 backdrop-blur">
      <h1 className="text-base font-semibold text-gray-100">{title}</h1>
      <div className="flex items-center gap-3">
        <AlertBell alerts={alerts} onClearAll={onClearAlerts} />
        <div className="h-4 w-px bg-gray-700" />
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-[10px] text-emerald-400 font-medium">
            {(user?.display_name || user?.email || 'U')[0].toUpperCase()}
          </div>
          <span className="text-xs text-gray-400">{user?.display_name || user?.email || 'User'}</span>
        </div>
        <button
          onClick={logout}
          className="text-xs text-gray-500 hover:text-red-400 transition-colors px-2 py-1 rounded hover:bg-gray-700/50"
        >
          Sign out
        </button>
      </div>
    </div>
  )
}
