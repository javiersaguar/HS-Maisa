'use client'

import { useCallback } from 'react'
import { fetchSalud } from '@/lib/api/salud'
import { LIVE_POLL_INTERVAL_MS } from '@/lib/config'
import type { Salud } from '@/lib/types'
import { useAsync } from './useAsync'

/**
 * Estado del puente y de la BD. Con `live`, se refresca en segundo plano y, al contrario que las
 * pantallas de datos, un fallo de sondeo sí se enseña: si el puente cae a mitad de la demo, se ve.
 */
export function useSalud({ live = false }: { live?: boolean } = {}) {
  return useAsync<Salud>(useCallback(() => fetchSalud(), []), [], {
    pollMs: live ? LIVE_POLL_INTERVAL_MS : null,
    pollErrors: true,
  })
}
