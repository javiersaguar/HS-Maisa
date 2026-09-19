'use client'

import { useCallback } from 'react'
import { confianzaDisponible, fetchConfianzaFichero, fetchConfianzaFicheros, fetchConfianzaMap } from '@/lib/api/confianza'
import type { ConfianzaFicha, ConfianzaItem, ConfianzaQuery, ConfianzaResumen } from '@/lib/types'
import { useAsync } from './useAsync'

/**
 * `data` es el resumen si K3 responde y null si no (404, red). Mientras sondea, `loading`. Nunca da error.
 * `disponible` es `false` sólo cuando ya se sabe que no está: mientras carga es `null`.
 */
export function useConfianzaDisponible() {
  const state = useAsync<ConfianzaResumen | null>(useCallback(() => confianzaDisponible(), []), [])
  const disponible = state.loading ? null : Boolean(state.data)
  return { ...state, disponible }
}

/** file_id → fila de confianza, para la columna de la lista. null si K3 no está: la columna sale con «—». */
export function useConfianzaMap() {
  return useAsync<Map<string, ConfianzaItem> | null>(useCallback(() => fetchConfianzaMap(), []), [])
}

/** Las filas de `/confianza/ficheros` con un filtro (p. ej. `banda=baja` para «revisar primero»). */
export function useConfianzaFicheros(query: ConfianzaQuery, enabled = true) {
  const key = JSON.stringify(query)
  return useAsync(
    // eslint-disable-next-line react-hooks/exhaustive-deps
    useCallback(() => fetchConfianzaFicheros(query), [key]),
    [key],
    { enabled },
  )
}

/** La ficha de una factura; null si K3 no está o la factura no tiene decisión vigente (404). */
export function useConfianzaFichero(fileId: string | null) {
  return useAsync<ConfianzaFicha | null>(
    useCallback(async () => (fileId && (await confianzaDisponible()) ? fetchConfianzaFichero(fileId) : null), [fileId]),
    [fileId],
  )
}
