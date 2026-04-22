import { useEffect, useRef } from 'react'
import { useApi } from './useApi'

export function usePolling(asyncFn, intervalMs = 5000, deps = []) {
  const { data, loading, error, refetch } = useApi(asyncFn, deps)
  const intervalRef = useRef(null)

  useEffect(() => {
    intervalRef.current = setInterval(() => refetch(), intervalMs)
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [intervalMs, refetch])

  return { data, loading, error, refetch }
}
