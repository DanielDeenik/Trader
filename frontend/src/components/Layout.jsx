import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { StatusBar } from './StatusBar'
import { AlertToast } from './AlertToast'
import { useAlerts } from '../hooks/useAlerts'

export function Layout({ title, children }) {
  const { alerts, connected, clearAlerts } = useAlerts()

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header title={title} alerts={alerts} onClearAlerts={clearAlerts} />
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
        <StatusBar />
      </div>
      <AlertToast alerts={alerts} />
    </div>
  )
}
