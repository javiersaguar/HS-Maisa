'use client'

import { useCallback } from 'react'
import { confianzaDisponible, fetchConfianzaFichero, fetchConfianzaMapa } from '@/lib/api/confianza'
import type { ConfianzaFicha, ConfianzaItem, ConfianzaResumen } from '@/lib/types'
import { useAsync } from './useAsync'

/** `data` es el resumen si K3 responde y null si no. Mientras sondea, `loading`. Nunca da error. */
export function useConfianzaDisponible() {
  return useAsync<ConfianzaResumen | null>(useCallback(() => confianzaDisponible(), []), [])
}

/**
 * file_id → fila de confianza, para la columna de la lista de ficheros. null si K3 no está o falla:
 * la columna no se pinta y nada más se entera.
 */
export function useConfianzaMapa() {
  return useAsync<Map<string, ConfianzaItem> | null>(
    useCallback(async () => ((await confianzaDisponible()) ? fetchConfianzaMapa().catch(() => null) : null), []),
    [],
  )
}

/** La ficha de una factura; null si K3 no está o la factura no tiene decisión vigente (404). */
export function useConfianzaFicha(fileId: string | null) {
  return useAsync<ConfianzaFicha | null>(
    useCallback(async () => {
      if (!fileId || !(await confianzaDisponible())) return null
      return fetchConfianzaFichero(fileId).catch(() => null)
    }, [fileId]),
    [fileId],
  )
}
