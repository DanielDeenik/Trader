/**
 * AlertToast: Toast notification component for alerts.
 * Slides in from top-right, color-coded by severity, auto-dismisses.
 */

import { useEffect, useState } from 'react'

const SEVERITY_COLORS = {
  info: 'bg-blue-900 border-blue-700 text-blue-100',
  warning: 'bg-yellow-900 border-yellow-700 text-yellow-100',
  critical: 'bg-red-900 border-red-700 text-red-100',
}

const SEVERITY_ICONS = {
  info: '📢',
  warning: '⚠️',
  critical: '🚨',
}

function SingleToast({ alert, onDismiss }) {
  const [isVisible, setIsVisible] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false)
      setTimeout(onDismiss, 300) // Allow fade-out animation
    }, 8000)

    return () => clearTimeout(timer)
  }, [onDismiss])

  const colorClass = SEVERITY_COLORS[alert.severity] || SEVERITY_COLORS.info
  const icon = SEVERITY_ICONS[alert.severity] || '📌'

  const handleClose = () => {
    setIsVisible(false)
    setTimeout(onDismiss, 300)
  }

  const timestamp = new Date(alert.timestamp).toLocaleTimeString()

  return (
    <div
      className={`
        transform transition-all duration-300 ease-out
        ${isVisible ? 'translate-x-0 opacity-100' : 'translate-x-96 opacity-0'}
        mb-2
      `}
    >
      <div
        className={`
          ${colorClass}
          border rounded-lg p-4 shadow-lg max-w-md
          flex items-start gap-3
        `}
      >
        <span className="text-xl flex-shrink-0">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="font-semibold flex items-baseline gap-2">
            <span>{alert.symbol}</span>
            <span className="text-xs opacity-75">{timestamp}</span>
          </div>
          <p className="text-sm mt-1 break-words">{alert.message}</p>
        </div>
        <button
          onClick={handleClose}
          className="text-xl flex-shrink-0 opacity-50 hover:opacity-100 transition-opacity"
          aria-label="Dismiss alert"
        >
          ✕
        </button>
      </div>
    </div>
  )
}

export function AlertToast({ alerts }) {
  const [visibleAlerts, setVisibleAlerts] = useState([])

  useEffect(() => {
    // Keep only the 5 most recent alerts visible at once
    setVisibleAlerts(alerts.slice(0, 5))
  }, [alerts])

  const handleDismiss = (alertId) => {
    setVisibleAlerts((prev) => prev.filter((a) => a.id !== alertId))
  }

  return (
    <div
      className="fixed top-4 right-4 z-50 pointer-events-none"
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="flex flex-col gap-2 pointer-events-auto">
        {visibleAlerts.map((alert) => (
          <SingleToast
            key={alert.id}
            alert={alert}
            onDismiss={() => handleDismiss(alert.id)}
          />
        ))}
      </div>
    </div>
  )
}
