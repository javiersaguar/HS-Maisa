'use client'

import { useCallback } from 'react'
import { fetchTraza } from '@/lib/api/traza'
import type { PasoTraza, TrazaQuery } from '@/lib/types'
import { useAsync } from './useAsync'

/** Lector de la Chain of Work. Lo usan /audit, el detalle de fichero y el de etapa. */
export function useTraza(query: TrazaQuery = {}, { enabled = true }: { enabled?: boolean } = {}) {
  const loader = useCallback(
    () => fetchTraza(query),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [query.file_id, query.etapa, query.categoria],
  )
  return useAsync<PasoTraza[]>(loader, [query.file_id, query.etapa, query.categoria], { enabled })
}
