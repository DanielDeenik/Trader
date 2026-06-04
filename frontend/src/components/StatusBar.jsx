import { usePolling } from '../hooks'
import { api } from '../api'

export function StatusBar() {
  const { data, error } = usePolling(() => api.getSourceHealth(), 15000)

  if (error) {
    return (
      <div className="bg-[#0a0f1a] border-t border-white/[0.06] px-4 py-1.5 text-[12px] text-red-400">
        Source health check failed
      </div>
    )
  }

  const sources = data?.sources || []

  return (
    <div className="bg-[#0a0f1a] border-t border-white/[0.06] px-4 py-1.5 h-7 flex items-center">
      <div className="flex gap-4 text-[12px]">
        {sources.map((s) => (
          <div key={s.source} className="flex items-center gap-2">
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${
              s.status === 'fresh' ? 'bg-emerald-400' :
              s.status === 'stale' ? 'bg-amber-400' : 'bg-red-400'
            }`} />
            <span className="text-gray-400">{s.source}</span>
          </div>
        ))}
        {sources.length === 0 && <span className="text-gray-500 text-[12px]">Loading sources...</span>}
      </div>
    </div>
  )
}
