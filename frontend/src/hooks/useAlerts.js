/**
 * useAlerts: WebSocket hook for real-time alert streaming.
 * Manages connection, reconnection, and alert state.
 */

import { useEffect, useRef, useState, useCallback } from 'react'

const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/alerts/ws`
const RECONNECT_DELAY = 3000 // ms
const PING_INTERVAL = 30000 // ms

export function useAlerts() {
  const [alerts, setAlerts] = useState([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const pingIntervalRef = useRef(null)

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = null
    }
    setConnected(false)
  }, [])

  const connect = useCallback(() => {
    if (wsRef.current) return

    try {
      const ws = new WebSocket(WS_URL)

      ws.onopen = () => {
        console.log('Alert WebSocket connected')
        setConnected(true)

        // Send initial ping
        ws.send(JSON.stringify({ type: 'ping' }))

        // Set up ping interval to keep connection alive
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current)
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, PING_INTERVAL)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'alert') {
            // New alert received
            setAlerts((prev) => {
              const updated = [data, ...prev]
              return updated.length > 100 ? updated.slice(0, 100) : updated
            })
          } else if (data.type === 'connection_established') {
            console.log('Alert connection established:', data.message)
          } else if (data.type === 'pong') {
            // Ping-pong keep-alive
            console.debug('Alert WS pong')
          }
        } catch (e) {
          console.error('Error parsing alert message:', e)
        }
      }

      ws.onerror = (error) => {
        console.error('Alert WebSocket error:', error)
        setConnected(false)
      }

      ws.onclose = () => {
        console.log('Alert WebSocket closed, reconnecting in', RECONNECT_DELAY, 'ms')
        setConnected(false)
        wsRef.current = null

        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
          pingIntervalRef.current = null
        }

        // Attempt to reconnect
        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, RECONNECT_DELAY)
      }

      wsRef.current = ws
    } catch (error) {
      console.error('Failed to create WebSocket:', error)
      setConnected(false)

      reconnectTimeoutRef.current = setTimeout(() => {
        connect()
      }, RECONNECT_DELAY)
    }
  }, [])

  useEffect(() => {
    // Connect on mount
    connect()

    return () => {
      // Cleanup on unmount
      disconnect()
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [connect, disconnect])

  const clearAlerts = useCallback(() => {
    setAlerts([])
  }, [])

  return {
    alerts,
    connected,
    clearAlerts,
    unreadCount: alerts.length,
  }
}
