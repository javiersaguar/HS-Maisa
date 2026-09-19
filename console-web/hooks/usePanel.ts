'use client'

import { useCallback } from 'react'
import { fetchPanel } from '@/lib/api/panel'
import { LIVE_POLL_INTERVAL_MS } from '@/lib/config'
import type { PanelResumen } from '@/lib/types'
import { useAsync } from './useAsync'

/** Pasa `live` en las pantallas que presentan los contadores como estado en vivo. */
export function usePanel({ live = false }: { live?: boolean } = {}) {
  return useAsync<PanelResumen>(useCallback(() => fetchPanel(), []), [], {
    pollMs: live ? LIVE_POLL_INTERVAL_MS : null,
  })
}
