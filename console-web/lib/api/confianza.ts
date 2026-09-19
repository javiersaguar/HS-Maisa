import { API_CONTRACT_VERSION, USE_MOCK } from '../config'
import type { ConfianzaFicha, ConfianzaItem, ConfianzaLista, ConfianzaQuery, ConfianzaResumen } from '../types'
import * as mock from '../mock/confianza'
import { apiFetch, buildQuery } from './client'

/**
 * Confianza en la clasificación por factura (bonus K3). Contrato: docs/api/confianza.md.
 *
 * Es opcional: nada de aquí lanza. Un 404 (rutas sin registrar, factura sin decisión vigente), la red caída o
 * cualquier otro fallo dan `null` o lista vacía, y la consola sigue igual sin la métrica.
 */

let apiAvisada = false

/** Como `noteApi` de mappers.ts: si el JSON declara otra versión se avisa una vez y se sigue. */
function notarApi<T extends { api?: number }>(body: T): T {
  if (!apiAvisada && body?.api !== undefined && body.api !== API_CONTRACT_VERSION) {
    apiAvisada = true
    console.warn(
      `[albertitos] /confianza declara contrato v${body.api} y esta consola espera v${API_CONTRACT_VERSION}: revisa lib/types-confianza.ts`,
    )
  }
  return body
}

let sondeo: Promise<ConfianzaResumen | null> | null = null

/** GET /confianza/resumen?lote= → el resumen, o null si K3 no está. */
export async function fetchConfianzaResumen(lote?: number): Promise<ConfianzaResumen | null> {
  try {
    if (USE_MOCK) return await mock.getResumen(lote)
    return notarApi(await apiFetch<ConfianzaResumen>(`/confianza/resumen${buildQuery({ lote })}`))
  } catch {
    return null
  }
}

/** El resumen global, sondeado UNA vez por carga de la app (promesa de módulo). null si K3 no responde. */
export function confianzaDisponible(): Promise<ConfianzaResumen | null> {
  sondeo ??= fetchConfianzaResumen()
  return sondeo
}

/** GET /confianza/ficheros?banda&resultado&lote&limite&orden → ya ordenadas (menor confianza primero por defecto). */
export async function fetchConfianzaFicheros(query: ConfianzaQuery = {}): Promise<ConfianzaLista> {
  try {
    if (USE_MOCK) return await mock.listFicheros(query)
    const search = buildQuery({ ...query })
    return notarApi(await apiFetch<ConfianzaLista>(`/confianza/ficheros${search}`))
  } catch {
    return { items: [], total: 0 }
  }
}

/** GET /confianza/fichero?file_id= → la ficha, o null (404 = sin decisión vigente). */
export async function fetchConfianzaFichero(fileId: string): Promise<ConfianzaFicha | null> {
  const id = fileId.normalize('NFC')
  try {
    if (USE_MOCK) return await mock.getFichero(id)
    return notarApi(await apiFetch<ConfianzaFicha>(`/confianza/fichero${buildQuery({ file_id: id })}`))
  } catch {
    return null
  }
}

/**
 * Una sola GET `/confianza/ficheros?limite=1000` (540 caben de sobra) → file_id → fila, para la columna de la lista
 * sin pedir una ficha por fila. null si K3 no respondió.
 */
export async function fetchConfianzaMap(): Promise<Map<string, ConfianzaItem> | null> {
  if (!(await confianzaDisponible())) return null
  const { items } = await fetchConfianzaFicheros({ limite: 1000 })
  return new Map(items.map((item) => [item.file_id.normalize('NFC'), item]))
}
