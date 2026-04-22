import { useState } from 'react'
import { usePolling } from '../hooks'
import { api } from '../api'

const SOURCES = ['yfinance', 'reddit', 'sec_edgar', 'google_trends', 'github', 'coingecko', 'defillama']

export default function TaskQueue() {
  const { data: taskData, refetch } = usePolling(() => api.getTasks(), 3000)
  const [busy, setBusy] = useState(false)

  const tasks = taskData?.tasks || (Array.isArray(taskData) ? taskData : [])

  const triggerCollect = async (sources) => {
    setBusy(true)
    try { await api.createTask({ task_type: 'collect', params: { sources, domain: 'public' } }); refetch() }
    catch (e) { console.error(e) }
    finally { setBusy(false) }
  }

  const triggerAnalyze = async () => {
    setBusy(true)
    try { await api.createTask({ task_type: 'analyze', params: {} }); refetch() }
    catch (e) { console.error(e) }
    finally { setBusy(false) }
  }

  const STATUS_COLOR = { pending: 'text-yellow-400', running: 'text-blue-400', completed: 'text-emerald-400', failed: 'text-red-400', cancelled: 'text-gray-500' }

  return (
    <div className="space-y-4">
      <div className="bg-gray-800 border border-gray-700 rounded p-3">
        <div className="text-xs font-bold mb-2">Quick Actions</div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => triggerCollect(SOURCES)} disabled={busy} className="px-3 py-1 bg-emerald-900 text-emerald-400 border border-emerald-700 text-xs rounded disabled:opacity-50">Collect All</button>
          <button onClick={triggerAnalyze} disabled={busy} className="px-3 py-1 bg-purple-900 text-purple-400 border border-purple-700 text-xs rounded disabled:opacity-50">Run Analysis</button>
        </div>
        <div className="text-xs text-gray-400 mt-2">Collect by source:</div>
        <div className="flex flex-wrap gap-1 mt-1">
          {SOURCES.map(s => (
            <button key={s} onClick={() => triggerCollect([s])} disabled={busy} className="px-2 py-0.5 bg-blue-900/50 text-blue-400 border border-blue-800 text-xs rounded disabled:opacity-50">{s}</button>
          ))}
        </div>
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded p-3">
        <div className="flex justify-between items-center mb-2">
          <div className="text-xs font-bold">Queue ({tasks.length} tasks)</div>
          <div className="text-xs text-gray-500">Auto-refresh 3s</div>
        </div>
        {tasks.length === 0 && <div className="text-xs text-gray-500">No tasks</div>}
        {tasks.map(t => (
          <div key={t.id} className="bg-gray-900 border border-gray-700 rounded p-2 mb-1 text-xs">
            <div className="flex justify-between">
              <span className="font-mono">{t.task_type}</span>
              <span className={STATUS_COLOR[t.status] || 'text-gray-400'}>{t.status}</span>
            </div>
            <div className="text-gray-500 mt-0.5">
              {t.created_at && new Date(t.created_at).toLocaleString()}
              {t.attempts > 0 && <span className="ml-2">attempt {t.attempts}/{t.max_attempts}</span>}
            </div>
            {t.error && <div className="text-red-400 mt-1">{t.error}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}
