import { useState } from 'react'
import { usePolling } from '../hooks'
import { api } from '../api'

const SOURCES = ['yfinance', 'reddit', 'sec_edgar', 'google_trends', 'github', 'coingecko', 'defillama']

const STATUS_BADGES = {
  pending: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20' },
  running: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/20' },
  completed: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20' },
  failed: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20' },
  cancelled: { bg: 'bg-gray-500/10', text: 'text-gray-400', border: 'border-gray-500/20' },
}

export default function TaskQueue() {
  const { data: taskData, refetch } = usePolling(() => api.getTasks({ limit: 100 }), 3000)
  const [busy, setBusy] = useState(false)

  const tasks = taskData?.tasks || (Array.isArray(taskData) ? taskData : [])

  const triggerCollect = async (sources) => {
    setBusy(true)
    try {
      await api.createTask({
        task_type: 'collect',
        params: { sources, domain: 'public' },
      })
      refetch()
    } catch (e) {
      console.error('Failed to create task:', e)
    } finally {
      setBusy(false)
    }
  }

  const triggerAnalyze = async () => {
    setBusy(true)
    try {
      await api.createTask({
        task_type: 'analyze',
        params: {},
      })
      refetch()
    } catch (e) {
      console.error('Failed to create task:', e)
    } finally {
      setBusy(false)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '—'
    try {
      return new Date(dateString).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    } catch {
      return '—'
    }
  }

  const getStatusBadge = (status) => STATUS_BADGES[status] || STATUS_BADGES.pending

  return (
    <div className="space-y-4">
      {/* Quick Actions */}
      <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
        <h2 className="text-sm font-bold text-white mb-3">Quick Actions</h2>

        <div className="space-y-3">
          {/* Primary actions */}
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => triggerCollect(SOURCES)}
              disabled={busy}
              className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium rounded-lg hover:bg-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              Collect All Sources
            </button>
            <button
              onClick={triggerAnalyze}
              disabled={busy}
              className="px-4 py-2 bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-medium rounded-lg hover:bg-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              Run Analysis
            </button>
          </div>

          {/* Per-source buttons */}
          <div>
            <p className="text-xs text-gray-400 mb-2">Collect by source:</p>
            <div className="flex gap-2 flex-wrap">
              {SOURCES.map(source => (
                <button
                  key={source}
                  onClick={() => triggerCollect([source])}
                  disabled={busy}
                  className="px-3 py-1.5 bg-white/[0.04] border border-white/[0.08] text-gray-300 text-xs rounded-lg hover:bg-white/[0.06] disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  {source}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Task Queue */}
      <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-bold text-white">Task Queue</h2>
            <p className="text-xs text-gray-400 mt-1">{tasks.length} task{tasks.length !== 1 ? 's' : ''}</p>
          </div>
          <div className="text-xs text-gray-500">
            Auto-refresh every 3s
          </div>
        </div>

        {tasks.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-gray-500 text-xs">No tasks in queue</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-white/[0.03] border-b border-white/[0.06]">
                  <th className="text-left py-3 px-3 font-mono text-gray-400">ID</th>
                  <th className="text-left py-3 px-3 text-gray-400">Type</th>
                  <th className="text-center py-3 px-3 text-gray-400">Status</th>
                  <th className="text-center py-3 px-3 font-mono text-gray-400">Attempts</th>
                  <th className="text-left py-3 px-3 text-gray-400">Created</th>
                  <th className="text-left py-3 px-3 text-gray-400">Started</th>
                  <th className="text-left py-3 px-3 text-gray-400">Completed</th>
                  <th className="text-left py-3 px-3 text-gray-400">Error</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map(task => {
                  const statusBadge = getStatusBadge(task.status)
                  return (
                    <tr key={task.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition">
                      <td className="py-2 px-3 font-mono text-gray-500 truncate max-w-xs">
                        {task.id.substring(0, 8)}...
                      </td>
                      <td className="py-2 px-3 font-mono text-white">
                        {task.task_type}
                      </td>
                      <td className="py-2 px-3 text-center">
                        <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${statusBadge.bg} ${statusBadge.text} border ${statusBadge.border}`}>
                          {task.status}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-center font-mono text-gray-400">
                        {task.attempts || 0}/{task.max_attempts || 3}
                      </td>
                      <td className="py-2 px-3 text-gray-500">
                        {formatDate(task.created_at)}
                      </td>
                      <td className="py-2 px-3 text-gray-500">
                        {formatDate(task.started_at)}
                      </td>
                      <td className="py-2 px-3 text-gray-500">
                        {formatDate(task.completed_at)}
                      </td>
                      <td className="py-2 px-3 text-red-400/80">
                        {task.error ? (
                          <span className="truncate max-w-xs inline-block" title={task.error}>
                            {task.error.substring(0, 40)}...
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
