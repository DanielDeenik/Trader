import { Link } from 'react-router-dom'

export function SymbolLink({ symbol }) {
  return (
    <Link to={`/tickers/${symbol}`} className="text-emerald-400 hover:text-emerald-300 font-mono no-underline">
      {symbol}
    </Link>
  )
}
