import { USE_MOCK } from '../config'
import type { ConfianzaFicha, ConfianzaItem, ConfianzaResumen } from '../types'
import { apiFetch, buildQuery } from './client'

/**
 * Confianza en la clasificación por factura (bonus K3). Contrato: docs/api/confianza.md.
 *
 * Es opcional: la consola la enseña sólo si `GET /confianza/resumen` responde 200. Se sondea UNA vez por
 * carga de la app (promesa de módulo). Con datos de ejemplo no se sondea: la demo sin puente no finge K3.
 */

let sondeo: Promise<ConfianzaResumen | null> | null = null

/** El resumen si el servicio está, o null (404, red, mock). Nunca lanza. */
export function confianzaDisponible(): Promise<ConfianzaResumen | null> {
  if (USE_MOCK) return Promise.resolve(null)
  sondeo ??= apiFetch<ConfianzaResumen>('/confianza/resumen').catch(() => null)
  return sondeo
}

/** GET /confianza/fichero?file_id= → la ficha completa. 404 si no tiene decisión vigente. */
export async function fetchConfianzaFichero(fileId: string): Promise<ConfianzaFicha> {
  return apiFetch<ConfianzaFicha>(`/confianza/fichero${buildQuery({ file_id: fileId.normalize('NFC') })}`)
}

/**
 * GET /confianza/ficheros?limite=1000: una fila por factura con decisión vigente (540 caben de sobra).
 * Para la columna de la lista, que así no pide una ficha por fila.
 */
export async function fetchConfianzaMapa(): Promise<Map<string, ConfianzaItem>> {
  const body = await apiFetch<{ items: ConfianzaItem[] }>('/confianza/ficheros?limite=1000')
  return new Map(body.items.map((item) => [item.file_id, item]))
}
