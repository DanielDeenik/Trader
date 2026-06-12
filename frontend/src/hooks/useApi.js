import { useState, useEffect, useCallback, useRef } from 'react'
import { ApiError } from '../api'

export function useApi(asyncFn, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  // Monotonic request id: only the latest in-flight request may commit state,
  // so rapid dep changes (e.g. a filter toggle) can't let a slow earlier
  // response overwrite the current selection (last-response-wins race).
  const reqId = useRef(0)

  const doFetch = useCallback(async () => {
    const id = ++reqId.current
    setLoading(true)
    setError(null)
    try {
      const result = await asyncFn()
      if (id === reqId.current) setData(result)
    } catch (err) {
      if (id === reqId.current) {
        setError(err instanceof ApiError ? err : new Error(err.message))
        setData(null)
      }
    } finally {
      if (id === reqId.current) setLoading(false)
    }
  }, deps)

  useEffect(() => {
    doFetch()
  }, [doFetch])

  return { data, loading, error, refetch: doFetch }
}
