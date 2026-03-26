import React from 'react'
import { createRoot } from 'react-dom/client'

function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-emerald-400 mb-2">Social Arb</h1>
        <p className="text-gray-400">Information Arbitrage Platform</p>
        <p className="text-gray-500 text-sm mt-4">Frontend scaffold ready. Building pages next.</p>
      </div>
    </div>
  )
}

createRoot(document.getElementById('root')).render(<App />)
