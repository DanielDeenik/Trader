import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#0a0f1a] flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="mb-6">
          <h1 className="text-7xl font-bold text-emerald-400/20 mb-2">404</h1>
          <h2 className="text-2xl font-bold text-white">Page not found</h2>
        </div>

        <p className="text-gray-400 text-sm mb-8">
          The page you are looking for doesn't exist or has been moved.
        </p>

        <Link
          to="/"
          className="inline-block px-6 py-2.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-medium rounded-lg hover:bg-emerald-500/20 transition"
        >
          Back to Overview
        </Link>
      </div>
    </div>
  )
}
