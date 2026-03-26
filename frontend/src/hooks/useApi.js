import { useState, useEffect, useCallback } from 'react'
import { ApiError } from '../api'

export function useApi(asyncFn, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const doFetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await asyncFn()
      setData(result)
    } catch (err) {
      setError(err instanceof ApiError ? err : new Error(err.message))
      setData(null)
    } finally {
      setLoading(false)
    }
  }, deps)

  useEffect(() => {
    doFetch()
  }, [doFetch])

  return { data, loading, error, refetch: doFetch }
}
