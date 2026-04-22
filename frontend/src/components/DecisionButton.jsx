const allDecisions = [
  { value: 'promote', label: 'Promote', color: 'emerald' },
  { value: 'watch', label: 'Watch', color: 'yellow' },
  { value: 'discard', label: 'Discard', color: 'red' },
  { value: 'forge', label: 'Forge', color: 'blue' },
  { value: 'hold', label: 'Hold', color: 'gray' },
  { value: 'reject', label: 'Reject', color: 'red' },
  { value: 'execute', label: 'Execute', color: 'emerald' },
  { value: 'defer', label: 'Defer', color: 'yellow' },
]

const gateDecisions = {
  L1_triage: ['promote', 'watch', 'discard'],
  L2_validation: ['promote', 'watch', 'discard', 'forge'],
  L3_conviction: ['execute', 'defer', 'reject'],
}

const colorActive = {
  emerald: 'bg-emerald-900 text-emerald-300 border-emerald-600',
  yellow: 'bg-yellow-900 text-yellow-300 border-yellow-600',
  red: 'bg-red-900 text-red-300 border-red-600',
  blue: 'bg-blue-900 text-blue-300 border-blue-600',
  gray: 'bg-gray-700 text-gray-300 border-gray-500',
}

export function DecisionButton({ decision, onDecision, gate = null }) {
  const allowed = gate && gateDecisions[gate]
    ? allDecisions.filter(d => gateDecisions[gate].includes(d.value))
    : allDecisions

  return (
    <div className="flex gap-2 flex-wrap">
      {allowed.map(({ value, label, color }) => (
        <button
          key={value}
          onClick={() => onDecision(value)}
          className={`px-3 py-1 text-xs border rounded transition-colors ${
            decision === value ? colorActive[color] : 'bg-gray-800 text-gray-400 border-gray-700 hover:border-gray-500'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
