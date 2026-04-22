export function ScoreSlider({ criterion, score, onScore, max = 5 }) {
  return (
    <div className="flex items-center gap-3 py-1">
      <label className="text-xs w-36 text-gray-300">{criterion}</label>
      <div className="flex gap-1">
        {Array.from({ length: max }, (_, i) => i + 1).map((val) => (
          <button
            key={val}
            onClick={() => onScore(val)}
            className={`w-7 h-7 text-xs border rounded transition-colors ${
              score >= val
                ? 'bg-emerald-900 border-emerald-600 text-emerald-300'
                : 'bg-gray-800 border-gray-700 text-gray-500 hover:border-gray-500'
            }`}
          >
            {val}
          </button>
        ))}
      </div>
      <span className="text-xs text-gray-400 w-8 text-right">{score || 0}/{max}</span>
    </div>
  )
}
