export function EngineCard({ name, data, error = null }) {
  if (error) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded p-3">
        <div className="text-xs font-bold text-gray-300">{name}</div>
        <div className="text-xs text-red-400 mt-1">Error: {error}</div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded p-3">
        <div className="text-xs font-bold text-gray-300">{name}</div>
        <div className="text-xs text-gray-500 mt-1">No data</div>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-3">
      <div className="text-xs font-bold text-gray-300 mb-2">{name}</div>
      <pre className="text-xs overflow-x-auto bg-gray-900 p-2 rounded border border-gray-700 max-h-48 overflow-y-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}
