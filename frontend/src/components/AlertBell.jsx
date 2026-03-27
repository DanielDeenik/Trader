/**
 * AlertBell: Bell icon with unread count badge for header.
 * Click opens dropdown with recent alerts, each alert links to symbol.
 */

import { useState, useRef, useEffect } from 'react'

export function AlertBell({ alerts, onClearAll }) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)
  const unreadCount = alerts.length

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'text-red-400'
      case 'warning':
        return 'text-yellow-400'
      default:
        return 'text-blue-400'
    }
  }

  const getSeverityBg = (severity) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-900/20'
      case 'warning':
        return 'bg-yellow-900/20'
      default:
        return 'bg-blue-900/20'
    }
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-300 hover:text-white transition-colors"
        aria-label="Alerts"
        title={`${unreadCount} unread alert${unreadCount !== 1 ? 's' : ''}`}
      >
        {/* Bell icon */}
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0018 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>

        {/* Badge */}
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-red-600 rounded-full">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-40">
          <div className="p-3 border-b border-gray-700 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-100">Alerts</h3>
            {alerts.length > 0 && (
              <button
                onClick={() => {
                  onClearAll()
                  setIsOpen(false)
                }}
                className="text-xs text-gray-400 hover:text-gray-200 transition-colors"
              >
                Clear all
              </button>
            )}
          </div>

          <div className="max-h-96 overflow-y-auto">
            {alerts.length === 0 ? (
              <div className="p-4 text-center text-gray-400 text-sm">
                No alerts yet
              </div>
            ) : (
              <div className="divide-y divide-gray-700">
                {alerts.slice(0, 20).map((alert) => (
                  <div
                    key={alert.id}
                    className={`p-3 hover:bg-gray-700/50 transition-colors cursor-pointer ${getSeverityBg(
                      alert.severity
                    )}`}
                  >
                    <div className="flex items-start gap-2">
                      <div className="flex-shrink-0 mt-0.5">
                        <div
                          className={`w-2 h-2 rounded-full ${getSeverityColor(
                            alert.severity
                          )}`}
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-baseline gap-2 mb-1">
                          <a
                            href={`/symbol/${alert.symbol}`}
                            className="font-semibold text-sm text-gray-100 hover:text-blue-400 transition-colors"
                          >
                            {alert.symbol}
                          </a>
                          <span className="text-xs text-gray-500">
                            {alert.type.replace(/_/g, ' ')}
                          </span>
                        </div>
                        <p className="text-xs text-gray-300 leading-snug">
                          {alert.message}
                        </p>
                        <div className="text-xs text-gray-500 mt-1">
                          {new Date(alert.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {alerts.length > 20 && (
            <div className="p-2 text-center border-t border-gray-700">
              <span className="text-xs text-gray-400">
                {alerts.length - 20} more alert{alerts.length - 20 !== 1 ? 's' : ''}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
