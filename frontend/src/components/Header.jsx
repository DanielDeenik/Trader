import { AlertBell } from './AlertBell'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

export function Header({ title, alerts = [], onClearAlerts = () => {} }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="border-b border-gray-700 px-6 py-3 flex items-center justify-between bg-gray-800">
      <h1 className="text-lg font-bold">{title}</h1>
      <div className="flex items-center gap-4">
        <AlertBell alerts={alerts} onClearAll={onClearAlerts} />
        {user && (
          <>
            <div className="text-xs text-gray-400">
              <p>{user.display_name || user.displayName || user.email}</p>
            </div>
            <button
              onClick={handleLogout}
              className="text-xs text-gray-400 hover:text-gray-200 transition-colors"
            >
              Logout
            </button>
          </>
        )}
        <div className="text-xs text-gray-500">Social Arb v2.0</div>
      </div>
    </div>
  )
}
