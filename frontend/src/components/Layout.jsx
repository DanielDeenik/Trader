import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { StatusBar } from './StatusBar'

export function Layout({ title, children }) {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header title={title} />
        <div className="flex-1 overflow-y-auto p-4">{children}</div>
        <StatusBar />
      </div>
    </div>
  )
}
