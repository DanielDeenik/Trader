import { useState, useEffect, useCallback } from 'react'

const API = '/api/v1'

const STATE_COLORS = {
  watching: 'bg-emerald-400',
  acting: 'bg-amber-400',
  idle: 'bg-gray-500',
  error: 'bg-red-500',
  stopped: 'bg-gray-600',
  unknown: 'bg-gray-600',
}

const STATE_TEXT = {
  watching: 'text-emerald-400',
  acting: 'text-amber-400',
  idle: 'text-gray-400',
  error: 'text-red-400',
  stopped: 'text-gray-500',
  unknown: 'text-gray-500',
}

const LAYER_LABELS = {
  'L0': 'Peripheral Vision',
  'L1-L2': 'Pattern Recognition',
  'L2-L3': 'Divergence + Conviction',
  'L3-L4': 'Decision Gates',
  'L4-L5': 'Execution + Monitoring',
  'meta': 'Meta-cognition',
}

function AgentNode({ agent, onRestart }) {
  const state = agent.state || 'unknown'
  const metrics = agent.metrics || {}
  const dotColor = STATE_COLORS[state] || STATE_COLORS.unknown
  const textColor = STATE_TEXT[state] || STATE_TEXT.unknown

  return (
    <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4 min-w-[220px]">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${dotColor}`} />
          <span className="text-sm font-semibold text-white capitalize">{agent.name}</span>
        </div>
        <span className={`text-[10px] uppercase tracking-wider font-medium ${textColor}`}>{state}</span>
      </div>

      <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">
        {agent.layer} — {LAYER_LABELS[agent.layer] || agent.layer}
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
        <div className="text-gray-500">Actions</div>
        <div className="text-gray-300 text-right">{metrics.actions_taken || 0}</div>
        <div className="text-gray-500">Failed</div>
        <div className={`text-right ${metrics.actions_failed > 0 ? 'text-red-400' : 'text-gray-300'}`}>{metrics.actions_failed || 0}</div>
        <div className="text-gray-500">Events In</div>
        <div className="text-gray-300 text-right">{metrics.events_received || 0}</div>
        <div className="text-gray-500">Events Out</div>
        <div className="text-gray-300 text-right">{metrics.events_published || 0}</div>
      </div>

      {metrics.last_action_at && (
        <div className="mt-2 text-[10px] text-gray-500">
          Last: {new Date(metrics.last_action_at).toLocaleTimeString()}
        </div>
      )}

      {state === 'error' && (
        <button
          onClick={() => onRestart(agent.name)}
          className="mt-3 w-full text-[11px] px-3 py-1.5 rounded bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
        >
          Restart Agent
        </button>
      )}
    </div>
  )
}

function PipelineFlow({ nodes, edges }) {
  if (!nodes || nodes.length === 0) {
    return <div className="text-gray-500 text-sm">No pipeline data</div>
  }

  // Position nodes in a horizontal flow
  const nodePositions = {}
  const nodeWidth = 140
  const nodeHeight = 50
  const gapX = 60
  const startX = 40
  const startY = 80

  // Main pipeline: sentinel → assembler → strategist → gatekeeper → executor
  const mainFlow = ['sentinel', 'assembler', 'strategist', 'gatekeeper', 'executor']
  mainFlow.forEach((name, i) => {
    nodePositions[name] = { x: startX + i * (nodeWidth + gapX), y: startY }
  })
  // Supervisor below center
  nodePositions['supervisor'] = { x: startX + 2 * (nodeWidth + gapX), y: startY + 100 }

  const svgWidth = startX + mainFlow.length * (nodeWidth + gapX)
  const svgHeight = startY + 180

  const getNodeCenter = (name) => {
    const pos = nodePositions[name]
    if (!pos) return { x: 0, y: 0 }
    return { x: pos.x + nodeWidth / 2, y: pos.y + nodeHeight / 2 }
  }

  const nodeMap = {}
  nodes.forEach(n => { nodeMap[n.id] = n })

  return (
    <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4 overflow-x-auto">
      <svg width={svgWidth} height={svgHeight} className="w-full" viewBox={`0 0 ${svgWidth} ${svgHeight}`}>
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
            <path d="M0,0 L8,3 L0,6" fill="#4b5563" />
          </marker>
          <marker id="arrow-feedback" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
            <path d="M0,0 L8,3 L0,6" fill="#6366f1" />
          </marker>
        </defs>

        {/* Edges */}
        {(edges || []).map((edge, i) => {
          const from = getNodeCenter(edge.source)
          const to = getNodeCenter(edge.target)
          const isFeedback = edge.source === 'executor' && edge.target === 'sentinel'
          const isHITL = edge.label === 'HITL_REQUIRED'

          if (isFeedback) {
            // Curved feedback loop under the pipeline
            const midY = startY + nodeHeight + 40
            return (
              <g key={i}>
                <path
                  d={`M${from.x},${from.y + nodeHeight/2} Q${from.x},${midY} ${(from.x + to.x) / 2},${midY} Q${to.x},${midY} ${to.x},${to.y + nodeHeight/2}`}
                  fill="none" stroke="#6366f1" strokeWidth="1" strokeDasharray="4,4"
                  markerEnd="url(#arrow-feedback)"
                />
                <text x={(from.x + to.x) / 2} y={midY + 14} textAnchor="middle" className="fill-indigo-400 text-[9px]">
                  {edge.label}
                </text>
              </g>
            )
          }

          if (isHITL) {
            // Curved HITL path
            const midY = startY - 30
            return (
              <g key={i}>
                <path
                  d={`M${from.x},${from.y - nodeHeight/2} Q${from.x},${midY} ${(from.x + to.x) / 2},${midY} Q${to.x},${midY} ${to.x},${to.y - nodeHeight/2}`}
                  fill="none" stroke="#f59e0b" strokeWidth="1" strokeDasharray="3,3"
                  markerEnd="url(#arrow)"
                />
                <text x={(from.x + to.x) / 2} y={midY - 6} textAnchor="middle" className="fill-amber-400 text-[9px]">
                  HITL
                </text>
              </g>
            )
          }

          // Normal forward edge
          return (
            <g key={i}>
              <line
                x1={from.x + nodeWidth / 2 - 4} y1={from.y}
                x2={to.x - nodeWidth / 2 + 4} y2={to.y}
                stroke="#4b5563" strokeWidth="1.5" markerEnd="url(#arrow)"
              />
              <text
                x={(from.x + to.x) / 2} y={from.y - 10}
                textAnchor="middle" className="fill-gray-500 text-[8px]"
              >
                {edge.label}
              </text>
            </g>
          )
        })}

        {/* Nodes */}
        {nodes.map(node => {
          const pos = nodePositions[node.id]
          if (!pos) return null
          const state = node.state || 'unknown'
          const fillColor = state === 'watching' ? '#065f46' : state === 'acting' ? '#78350f' : state === 'error' ? '#7f1d1d' : '#1f2937'
          const borderColor = state === 'watching' ? '#10b981' : state === 'acting' ? '#f59e0b' : state === 'error' ? '#ef4444' : '#374151'

          return (
            <g key={node.id}>
              <rect
                x={pos.x} y={pos.y - nodeHeight / 2}
                width={nodeWidth} height={nodeHeight}
                rx="8" fill={fillColor} stroke={borderColor} strokeWidth="1"
              />
              <text x={pos.x + nodeWidth / 2} y={pos.y - 4} textAnchor="middle" className="fill-white text-[11px] font-semibold capitalize">
                {node.id}
              </text>
              <text x={pos.x + nodeWidth / 2} y={pos.y + 12} textAnchor="middle" className="fill-gray-400 text-[9px]">
                {node.layer}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function ThroughputPanel({ throughput }) {
  if (!throughput) return null
  const items = [
    { label: 'Signals (24h)', value: throughput.signals_24h || 0, color: 'text-blue-400' },
    { label: 'Mosaics (24h)', value: throughput.mosaics_24h || 0, color: 'text-purple-400' },
    { label: 'Theses (24h)', value: throughput.theses_24h || 0, color: 'text-emerald-400' },
    { label: 'Pending Reviews', value: throughput.pending_reviews || 0, color: throughput.pending_reviews > 10 ? 'text-amber-400' : 'text-gray-300' },
  ]

  return (
    <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Pipeline Throughput</h3>
      <div className="grid grid-cols-4 gap-4">
        {items.map(item => (
          <div key={item.label} className="text-center">
            <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
            <div className="text-[10px] text-gray-500 mt-1">{item.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function EventHistory({ events }) {
  if (!events || events.length === 0) {
    return (
      <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Recent Events</h3>
        <div className="text-gray-500 text-sm">No events yet</div>
      </div>
    )
  }

  return (
    <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Recent Events</h3>
      <div className="space-y-1 max-h-64 overflow-y-auto">
        {events.map(evt => (
          <div key={evt.id} className="flex items-center gap-3 text-[11px] py-1.5 border-b border-white/[0.03] last:border-0">
            <span className="text-gray-500 w-16 flex-shrink-0">
              {new Date(evt.timestamp).toLocaleTimeString()}
            </span>
            <span className="text-emerald-400 font-mono w-36 flex-shrink-0 truncate">{evt.type}</span>
            <span className="text-gray-400 flex-shrink-0">{evt.source_agent}</span>
            <span className="text-gray-500 truncate flex-1">
              {evt.payload ? JSON.stringify(evt.payload).slice(0, 80) : ''}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Pipeline() {
  const [health, setHealth] = useState(null)
  const [flow, setFlow] = useState(null)
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchAll = useCallback(async () => {
    try {
      const [healthRes, flowRes, eventsRes] = await Promise.all([
        fetch(`${API}/agents/health`),
        fetch(`${API}/agents/flow`),
        fetch(`${API}/agents/events/history?limit=30`),
      ])

      if (healthRes.ok) setHealth(await healthRes.json())
      if (flowRes.ok) setFlow(await flowRes.json())
      if (eventsRes.ok) setEvents(await eventsRes.json())
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 5000)
    return () => clearInterval(interval)
  }, [fetchAll])

  const handleRestart = async (agentName) => {
    try {
      await fetch(`${API}/agents/${agentName}/restart`, { method: 'POST' })
      await fetchAll()
    } catch (err) {
      console.error('Failed to restart agent:', err)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
        Loading pipeline status...
      </div>
    )
  }

  if (error && !health) {
    return (
      <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-6 text-center">
        <div className="text-red-400 text-sm mb-2">Pipeline not available</div>
        <div className="text-gray-500 text-xs">{error}</div>
        <div className="text-gray-500 text-xs mt-2">Agents may be disabled or not yet initialized.</div>
      </div>
    )
  }

  const pipelineStatus = health?.status || 'unknown'
  const statusColor = pipelineStatus === 'healthy' ? 'text-emerald-400' : pipelineStatus === 'degraded' ? 'text-amber-400' : 'text-red-400'
  const agents = health?.agents?.agents || []

  return (
    <div className="space-y-4">
      {/* Pipeline Status Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-2.5 h-2.5 rounded-full ${pipelineStatus === 'healthy' ? 'bg-emerald-400' : pipelineStatus === 'degraded' ? 'bg-amber-400' : 'bg-red-400'}`} />
          <span className={`text-sm font-semibold uppercase tracking-wider ${statusColor}`}>{pipelineStatus}</span>
          {health?.last_check && (
            <span className="text-[10px] text-gray-500">
              Last check: {new Date(health.last_check).toLocaleTimeString()}
            </span>
          )}
        </div>
        <button
          onClick={fetchAll}
          className="text-[11px] px-3 py-1.5 rounded bg-white/[0.05] text-gray-400 hover:bg-white/[0.08] transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Throughput */}
      <ThroughputPanel throughput={health?.throughput} />

      {/* Visual Flow Diagram */}
      <PipelineFlow nodes={flow?.nodes || []} edges={flow?.edges || []} />

      {/* Issues */}
      {health?.issues && health.issues.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
          <h3 className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">Issues ({health.issues.length})</h3>
          <div className="space-y-1">
            {health.issues.map((issue, i) => (
              <div key={i} className="text-[11px] text-red-300">
                <span className="text-red-400 font-mono">[{issue.type}]</span> {issue.agent && <span className="text-gray-400">{issue.agent}:</span>} {issue.message || issue.error}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Agent Cards Grid */}
      <div>
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Agent Status</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {agents.map(agent => (
            <AgentNode key={agent.name} agent={agent} onRestart={handleRestart} />
          ))}
        </div>
      </div>

      {/* Event History */}
      <EventHistory events={events} />
    </div>
  )
}
