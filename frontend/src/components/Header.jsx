import { AlertBell } from './AlertBell'

export function Header({ title, alerts = [], onClearAlerts = () => {} }) {
  return (
    <div className="border-b border-gray-700 px-6 py-3 flex items-center justify-between bg-gray-800">
      <h1 className="text-lg font-bold">{title}</h1>
      <div className="flex items-center gap-4">
        <AlertBell alerts={alerts} onClearAll={onClearAlerts} />
        <div className="text-xs text-gray-400">Social Arb v2.0</div>
      </div>
    </div>
  )
}
