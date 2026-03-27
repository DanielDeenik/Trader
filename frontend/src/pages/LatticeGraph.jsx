import { useParams, Link } from 'react-router-dom'
import { useState, useCallback, useMemo, useEffect } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Handle,
  Position,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { api } from '../api'

/* ──────────────────────────────────────────────
   Node colours and styling per type
   ────────────────────────────────────────────── */
const NODE_STYLES = {
  instrument: { bg: '#065f46', border: '#34d399', icon: '⊞', color: '#34d399' },
  signal:     { bg: '#1e3a5f', border: '#4da6ff', icon: '◈', color: '#4da6ff' },
  mosaic:     { bg: '#4a1d6e', border: '#a78bfa', icon: '◆', color: '#a78bfa' },
  thesis:     { bg: '#713f12', border: '#fbbf24', icon: '◇', color: '#fbbf24' },
  decision:   { bg: '#1c1917', border: '#f97316', icon: '▷', color: '#f97316' },
  position:   { bg: '#14532d', border: '#22c55e', icon: '▣', color: '#22c55e' },
  custom:     { bg: '#374151', border: '#9ca3af', icon: '✦', color: '#9ca3af' },
}

const EDGE_COLORS = {
  contains: '#4da6ff',
  builds: '#a78bfa',
  fragment: '#6b7280',
  forged: '#fbbf24',
  decides: '#f97316',
  executes: '#22c55e',
  custom_link: '#9ca3af',
}

/* ──────────────────────────────────────────────
   Custom Node Component
   ────────────────────────────────────────────── */
function LatticeNode({ data, selected }) {
  const style = NODE_STYLES[data.nodeType] || NODE_STYLES.custom
  return (
    <div
      className="rounded-lg px-3 py-2 text-xs shadow-lg min-w-[140px] max-w-[220px] transition-all"
      style={{
        background: style.bg,
        border: `2px solid ${selected ? '#fff' : style.border}`,
        boxShadow: selected ? `0 0 16px ${style.border}` : 'none',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: style.border, width: 8, height: 8 }} />
      <div className="flex items-center gap-1.5 mb-1">
        <span style={{ color: style.color }}>{style.icon}</span>
        <span className="font-bold uppercase text-gray-400" style={{ fontSize: 9 }}>{data.nodeType}</span>
      </div>
      <div className="text-white font-medium truncate">{data.label}</div>
      {data.subtitle && (
        <div className="text-gray-400 mt-0.5 truncate" style={{ fontSize: 10 }}>{data.subtitle}</div>
      )}
      <Handle type="source" position={Position.Bottom} style={{ background: style.border, width: 8, height: 8 }} />
    </div>
  )
}

const nodeTypes = { latticeNode: LatticeNode }

/* ──────────────────────────────────────────────
   Layout algorithm — hierarchical top-to-bottom
   ────────────────────────────────────────────── */
const LAYER_ORDER = ['instrument', 'signal', 'mosaic', 'thesis', 'decision', 'position', 'custom']
const LAYER_Y = { instrument: 0, signal: 150, mosaic: 340, thesis: 530, decision: 720, position: 910, custom: 1050 }

function layoutNodes(apiNodes) {
  const byType = {}
  for (const n of apiNodes) {
    const t = n.type || 'custom'
    if (!byType[t]) byType[t] = []
    byType[t].push(n)
  }

  const flowNodes = []
  for (const type of LAYER_ORDER) {
    const group = byType[type] || []
    const count = group.length
    const spacing = Math.min(220, Math.max(160, 1200 / (count + 1)))
    const startX = -(count - 1) * spacing / 2

    group.forEach((n, i) => {
      const subtitle = _getSubtitle(n)
      flowNodes.push({
        id: n.id,
        type: 'latticeNode',
        position: { x: startX + i * spacing, y: LAYER_Y[type] ?? 1050 },
        data: { label: n.label, nodeType: n.type, subtitle, raw: n.data },
      })
    })
  }
  return flowNodes
}

function _getSubtitle(n) {
  const d = n.data || {}
  switch (n.type) {
    case 'signal': return d.strength ? `str: ${Number(d.strength).toFixed(2)} | conf: ${Number(d.confidence).toFixed(2)}` : null
    case 'mosaic': return d.coherence_score ? `coherence: ${Number(d.coherence_score).toFixed(2)}` : null
    case 'thesis': return d.lifecycle_stage || d.status
    case 'decision': return d.trust_level || d.gate
    case 'position': return d.status
    default: return null
  }
}

function layoutEdges(apiEdges) {
  return apiEdges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label,
    animated: e.label === 'custom_link',
    style: { stroke: EDGE_COLORS[e.label] || '#6b7280', strokeWidth: 1.5 },
    labelStyle: { fill: '#9ca3af', fontSize: 10 },
    markerEnd: { type: MarkerType.ArrowClosed, color: EDGE_COLORS[e.label] || '#6b7280' },
  }))
}

/* ──────────────────────────────────────────────
   HITL Panels: Add Node / Add Edge
   ────────────────────────────────────────────── */
function AddNodePanel({ symbol, existingNodes, onNodeAdded }) {
  const [label, setLabel] = useState('')
  const [content, setContent] = useState('')
  const [connectTo, setConnectTo] = useState([])
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!label.trim()) return
    setSaving(true)
    try {
      await api.addLatticeNode(symbol, {
        type: 'custom',
        label: label.trim(),
        data: { content: content.trim() },
        connect_to: connectTo,
      })
      setLabel('')
      setContent('')
      setConnectTo([])
      onNodeAdded()
    } catch (err) {
      console.error('Failed to add node:', err)
    } finally {
      setSaving(false)
    }
  }

  const toggleConnect = (nodeId) => {
    setConnectTo((prev) =>
      prev.includes(nodeId) ? prev.filter((id) => id !== nodeId) : [...prev, nodeId]
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <div className="text-xs font-bold text-emerald-400 mb-1">Add Research Node</div>
      <input
        type="text"
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        placeholder="Node label (e.g. 'Competitor filing')"
        className="w-full bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-xs text-white placeholder-gray-500 focus:border-emerald-400 focus:outline-none"
      />
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Research content / notes..."
        rows={3}
        className="w-full bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-xs text-white placeholder-gray-500 focus:border-emerald-400 focus:outline-none resize-none"
      />
      {existingNodes.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 mb-1">Connect to:</div>
          <div className="max-h-32 overflow-y-auto space-y-0.5">
            {existingNodes.slice(0, 20).map((n) => (
              <label key={n.id} className="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer hover:text-gray-200">
                <input
                  type="checkbox"
                  checked={connectTo.includes(n.id)}
                  onChange={() => toggleConnect(n.id)}
                  className="rounded"
                />
                <span style={{ color: NODE_STYLES[n.data?.nodeType]?.color }}>{NODE_STYLES[n.data?.nodeType]?.icon}</span>
                <span className="truncate">{n.data?.label}</span>
              </label>
            ))}
          </div>
        </div>
      )}
      <button
        type="submit"
        disabled={!label.trim() || saving}
        className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-xs py-1.5 rounded transition-colors"
      >
        {saving ? 'Adding...' : 'Add Node'}
      </button>
    </form>
  )
}

function AddEdgePanel({ symbol, existingNodes, onEdgeAdded }) {
  const [source, setSource] = useState('')
  const [target, setTarget] = useState('')
  const [label, setLabel] = useState('supports')
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!source || !target) return
    setSaving(true)
    try {
      await api.addLatticeEdge(symbol, { source, target, label })
      setSource('')
      setTarget('')
      onEdgeAdded()
    } catch (err) {
      console.error('Failed to add edge:', err)
    } finally {
      setSaving(false)
    }
  }

  const nodeOptions = existingNodes.map((n) => ({
    id: n.id,
    label: `${NODE_STYLES[n.data?.nodeType]?.icon || '?'} ${n.data?.label || n.id}`,
  }))

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <div className="text-xs font-bold text-fbbf24 mb-1" style={{ color: '#fbbf24' }}>Add Connection</div>
      <select
        value={source}
        onChange={(e) => setSource(e.target.value)}
        className="w-full bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-xs text-white focus:border-emerald-400 focus:outline-none"
      >
        <option value="">From node...</option>
        {nodeOptions.map((n) => <option key={n.id} value={n.id}>{n.label}</option>)}
      </select>
      <select
        value={target}
        onChange={(e) => setTarget(e.target.value)}
        className="w-full bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-xs text-white focus:border-emerald-400 focus:outline-none"
      >
        <option value="">To node...</option>
        {nodeOptions.map((n) => <option key={n.id} value={n.id}>{n.label}</option>)}
      </select>
      <input
        type="text"
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        placeholder="Edge label (e.g. 'supports', 'contradicts')"
        className="w-full bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-xs text-white placeholder-gray-500 focus:border-emerald-400 focus:outline-none"
      />
      <button
        type="submit"
        disabled={!source || !target || saving}
        className="w-full bg-yellow-600 hover:bg-yellow-500 disabled:bg-gray-700 disabled:text-gray-500 text-white text-xs py-1.5 rounded transition-colors"
      >
        {saving ? 'Connecting...' : 'Connect Nodes'}
      </button>
    </form>
  )
}

/* ──────────────────────────────────────────────
   Node Detail Panel (click a node)
   ────────────────────────────────────────────── */
function NodeDetailPanel({ node }) {
  if (!node) return null
  const d = node.data?.raw || {}
  const style = NODE_STYLES[node.data?.nodeType] || NODE_STYLES.custom

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span style={{ color: style.color, fontSize: 16 }}>{style.icon}</span>
        <div>
          <div className="text-sm font-bold text-white">{node.data?.label}</div>
          <div className="text-xs text-gray-500 uppercase">{node.data?.nodeType}</div>
        </div>
      </div>
      <div className="bg-gray-900 rounded border border-gray-700 p-2">
        <pre className="text-xs text-gray-300 overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">
          {JSON.stringify(d, null, 2)}
        </pre>
      </div>
    </div>
  )
}

/* ──────────────────────────────────────────────
   Stats Bar
   ────────────────────────────────────────────── */
function StatsBar({ stats }) {
  if (!stats) return null
  return (
    <div className="flex gap-3 flex-wrap">
      {Object.entries(stats).map(([type, count]) => {
        const style = NODE_STYLES[type] || NODE_STYLES.custom
        return (
          <div key={type} className="flex items-center gap-1 text-xs">
            <span style={{ color: style.color }}>{style.icon}</span>
            <span className="text-gray-400">{type}:</span>
            <span className="text-white font-mono">{count}</span>
          </div>
        )
      })}
    </div>
  )
}

/* ──────────────────────────────────────────────
   Main Lattice Graph Page
   ────────────────────────────────────────────── */
export default function LatticeGraph() {
  const { symbol } = useParams()
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [sidePanel, setSidePanel] = useState('detail') // 'detail' | 'addNode' | 'addEdge'

  const fetchGraph = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getLattice(symbol)
      const flowNodes = layoutNodes(data.nodes || [])
      const flowEdges = layoutEdges(data.edges || [])
      setNodes(flowNodes)
      setEdges(flowEdges)
      setStats(data.stats || {})
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [symbol])

  useEffect(() => { fetchGraph() }, [fetchGraph])

  const onConnect = useCallback((params) => {
    setEdges((eds) => addEdge({
      ...params,
      animated: true,
      style: { stroke: '#9ca3af', strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#9ca3af' },
    }, eds))
  }, [setEdges])

  const onNodeClick = useCallback((_, node) => {
    setSelectedNode(node)
    setSidePanel('detail')
  }, [])

  const onPaneClick = useCallback(() => {
    setSelectedNode(null)
  }, [])

  if (loading) {
    return <div className="text-gray-400 text-sm py-8 text-center">Building lattice for {symbol}...</div>
  }

  if (error) {
    return <div className="text-red-400 text-sm py-8 text-center">Error: {error}</div>
  }

  return (
    <div className="flex flex-col h-full -m-4">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700 bg-gray-800/80 shrink-0">
        <div className="flex items-center gap-3">
          <Link to={`/deepdive/${symbol}`} className="text-xs text-gray-500 hover:text-gray-300 no-underline">
            &larr; Deep Dive
          </Link>
          <span className="text-lg font-bold text-emerald-400 font-mono">{symbol}</span>
          <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">Lattice Network</span>
        </div>
        <StatsBar stats={stats} />
      </div>

      {/* Main content: graph + side panel */}
      <div className="flex flex-1 min-h-0">
        {/* Graph canvas */}
        <div className="flex-1 relative" style={{ background: '#0f172a' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.1}
            maxZoom={2}
            defaultEdgeOptions={{
              style: { strokeWidth: 1.5 },
              markerEnd: { type: MarkerType.ArrowClosed },
            }}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#1e293b" gap={24} size={1} />
            <Controls
              style={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 6 }}
              showInteractive={true}
            />
            <MiniMap
              nodeColor={(n) => NODE_STYLES[n.data?.nodeType]?.border || '#6b7280'}
              style={{ background: '#111827', border: '1px solid #374151', borderRadius: 6 }}
              maskColor="rgba(0,0,0,0.7)"
            />
          </ReactFlow>

          {/* Legend overlay */}
          <div className="absolute bottom-3 left-3 bg-gray-800/90 border border-gray-700 rounded-lg px-3 py-2 backdrop-blur-sm">
            <div className="text-xs text-gray-500 mb-1">Node Types</div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
              {LAYER_ORDER.map((type) => (
                <div key={type} className="flex items-center gap-1.5 text-xs">
                  <span style={{ color: NODE_STYLES[type].color }}>{NODE_STYLES[type].icon}</span>
                  <span className="text-gray-400 capitalize">{type}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right panel — HITL controls */}
        <div className="w-72 bg-gray-800 border-l border-gray-700 flex flex-col shrink-0 overflow-hidden">
          {/* Panel tabs */}
          <div className="flex border-b border-gray-700 shrink-0">
            {[
              { id: 'detail', label: 'Detail' },
              { id: 'addNode', label: '+ Node' },
              { id: 'addEdge', label: '+ Edge' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSidePanel(tab.id)}
                className={`flex-1 px-2 py-2 text-xs transition-colors ${
                  sidePanel === tab.id
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-500 hover:text-gray-300 hover:bg-gray-700/50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Panel content */}
          <div className="flex-1 overflow-y-auto p-3">
            {sidePanel === 'detail' && (
              selectedNode
                ? <NodeDetailPanel node={selectedNode} />
                : <p className="text-xs text-gray-500 text-center py-4">Click a node to view details</p>
            )}
            {sidePanel === 'addNode' && (
              <AddNodePanel
                symbol={symbol}
                existingNodes={nodes}
                onNodeAdded={fetchGraph}
              />
            )}
            {sidePanel === 'addEdge' && (
              <AddEdgePanel
                symbol={symbol}
                existingNodes={nodes}
                onEdgeAdded={fetchGraph}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
