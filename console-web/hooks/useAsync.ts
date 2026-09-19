'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, toApiError } from '@/lib/api/client'

export interface AsyncState<T> {
  data: T | null
  error: ApiError | null
  /** True while a foreground request (first load, deps change, manual refresh) is in flight. */
  loading: boolean
  /** True only for the first load, so refreshes do not blank the screen. */
  initialLoading: boolean
  refresh: () => void
  setData: (updater: T | ((current: T | null) => T | null)) => void
}

export interface AsyncOptions {
  enabled?: boolean
  /**
   * Re-reads in the background every N ms. Background reads never toggle
   * `loading`, pause while the tab is hidden, and a failed poll keeps the
   * last good data on screen instead of replacing it with an error.
   */
  pollMs?: number | null
  /**
   * By default a failed poll is swallowed once there is data on screen. Health indicators want the
   * opposite: a bridge that dies after connecting must show up, so they set this to true.
   */
  pollErrors?: boolean
}

/**
 * Runs an async reader and keeps the component in sync with it.
 * Handles the three states every screen needs: loading, error and data.
 */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[] = [], options: AsyncOptions = {}): AsyncState<T> {
  const enabled = options.enabled ?? true
  const pollMs = options.pollMs ?? null
  const pollErrors = options.pollErrors ?? false
  const [data, setDataState] = useState<T | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(enabled)
  const [loadedOnce, setLoadedOnce] = useState(false)
  const [nonce, setNonce] = useState(0)

  const requestId = useRef(0)
  const loaderRef = useRef(loader)
  loaderRef.current = loader
  const hasData = useRef(false)

  useEffect(() => {
    if (!enabled) {
      setLoading(false)
      return
    }

    const id = requestId.current + 1
    requestId.current = id
    let active = true

    setLoading(true)
    loaderRef
      .current()
      .then((result) => {
        if (!active || requestId.current !== id) return
        hasData.current = true
        setDataState(result)
        setError(null)
      })
      .catch((caught) => {
        if (!active || requestId.current !== id) return
        setError(toApiError(caught))
      })
      .finally(() => {
        if (!active || requestId.current !== id) return
        setLoading(false)
        setLoadedOnce(true)
      })

    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, nonce, ...deps])

  useEffect(() => {
    if (!enabled || !pollMs) return
    let active = true

    const timer = window.setInterval(() => {
      if (document.visibilityState !== 'visible') return
      const id = requestId.current
      loaderRef
        .current()
        .then((result) => {
          if (!active || requestId.current !== id) return
          hasData.current = true
          setDataState(result)
          setError(null)
        })
        .catch((caught) => {
          if (!active || requestId.current !== id) return
          if (hasData.current && !pollErrors) return
          setError(toApiError(caught))
        })
    }, pollMs)

    return () => {
      active = false
      window.clearInterval(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, pollMs, pollErrors, ...deps])

  const refresh = useCallback(() => setNonce((value) => value + 1), [])

  const setData = useCallback((updater: T | ((current: T | null) => T | null)) => {
    setDataState((current) =>
      typeof updater === 'function' ? (updater as (value: T | null) => T | null)(current) : updater,
    )
  }, [])

  return {
    data,
    error,
    loading,
    initialLoading: loading && !loadedOnce,
    refresh,
    setData,
  }
}
