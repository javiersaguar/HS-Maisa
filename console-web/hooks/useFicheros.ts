'use client'

import { useCallback } from 'react'
import { fetchFichero, fetchFicheros } from '@/lib/api/ficheros'
import type { Fichero, FicheroQuery, Paginated } from '@/lib/types'
import { useAsync } from './useAsync'

export function useFicheros(query: FicheroQuery) {
  const deps = [query.q, query.estado, query.regla, query.lote, query.page, query.pageSize]
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const loader = useCallback(() => fetchFicheros(query), deps)
  return useAsync<Paginated<Fichero>>(loader, deps)
}

export function useFichero(fileId: string) {
  const loader = useCallback(() => fetchFichero(fileId), [fileId])
  return useAsync<Fichero>(loader, [fileId], { enabled: Boolean(fileId) })
}
