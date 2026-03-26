import { usePolling } from '../hooks'
import { api } from '../api'

export function StatusBar() {
  const { data, error } = usePolling(() => api.getSourceHealth(), 15000)

  if (error) {
    return (
      <div className="border-t border-gray-700 px-4 py-1.5 bg-gray-800 text-xs text-red-400">
        Source health check failed
      </div>
    )
  }

  const sources = data?.sources || []

  return (
    <div className="border-t border-gray-700 px-4 py-1.5 bg-gray-800">
      <div className="flex gap-4 text-xs">
        {sources.map((s) => (
          <div key={s.source} className="flex items-center gap-1">
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${
              s.status === 'fresh' ? 'bg-green-400' :
              s.status === 'stale' ? 'bg-yellow-400' : 'bg-red-400'
            }`} />
            <span className="text-gray-400">{s.source}</span>
          </div>
        ))}
        {sources.length === 0 && <span className="text-gray-500">Loading sources...</span>}
      </div>
    </div>
  )
}
