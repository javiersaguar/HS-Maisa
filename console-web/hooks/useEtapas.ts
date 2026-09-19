'use client'

import { useCallback } from 'react'
import { fetchEtapas, fetchEventos } from '@/lib/api/etapas'
import { LIVE_POLL_INTERVAL_MS } from '@/lib/config'
import type { Etapa, EtapasResumen, Event } from '@/lib/types'
import { useAsync } from './useAsync'

export function useEtapas({ live = false }: { live?: boolean } = {}) {
  return useAsync<EtapasResumen>(useCallback(() => fetchEtapas(), []), [], {
    pollMs: live ? LIVE_POLL_INTERVAL_MS : null,
  })
}

export function useEventos(etapa: Etapa | null, limit = 12) {
  return useAsync<Event[]>(
    useCallback(() => fetchEventos({ etapa: etapa ?? undefined, limit }), [etapa, limit]),
    [etapa, limit],
    { enabled: Boolean(etapa) },
  )
}
