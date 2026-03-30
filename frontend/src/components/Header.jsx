import { useAuth } from '../contexts/AuthContext'
import { AlertBell } from './AlertBell'

export function Header({ title, alerts = [], onClearAlerts = () => {} }) {
  const { user, logout } = useAuth()

  return (
    <div className="border-b border-gray-700 px-6 py-3 flex items-center justify-between bg-gray-800">
      <h1 className="text-lg font-bold">{title}</h1>
      <div className="flex items-center gap-4">
        <AlertBell alerts={alerts} onClearAll={onClearAlerts} />
        <div className="text-xs text-gray-400">{user?.display_name || user?.email || 'User'}</div>
        <button
          onClick={logout}
          className="text-xs text-gray-500 hover:text-gray-300 transition"
        >
          Sign out
        </button>
        <div className="text-xs text-gray-500">Social Arb v2.0</div>
      </div>
    </div>
  )
}
