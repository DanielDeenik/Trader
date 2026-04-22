import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="flex items-center justify-center h-screen bg-gray-900">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-500">404</h1>
        <p className="text-gray-400 mt-2">Page not found</p>
        <Link to="/" className="text-emerald-400 hover:text-emerald-300 text-sm mt-4 inline-block">Back to Overview</Link>
      </div>
    </div>
  )
}
