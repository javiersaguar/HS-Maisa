import { USE_MOCK } from '../config'
import type { Fichero, FicheroQuery, Paginated } from '../types'
import * as mock from '../mock/store'
import { apiFetch, buildQuery } from './client'
import { toFichero, toPaginatedFicheros } from './mappers'

export const DEFAULT_PAGE_SIZE = 15

/** GET /ficheros?q&estado&regla&lote&page&pageSize → `{ api, items, total, page, page_size }` */
export async function fetchFicheros(query: FicheroQuery = {}): Promise<Paginated<Fichero>> {
  const pageSize = query.pageSize ?? DEFAULT_PAGE_SIZE
  if (USE_MOCK) return mock.listFicheros({ ...query, pageSize })

  const search = buildQuery({
    q: query.q,
    estado: query.estado,
    regla: query.regla,
    lote: query.lote,
    page: query.page ?? 1,
    pageSize,
  })
  return toPaginatedFicheros(await apiFetch<unknown>(`/ficheros${search}`), pageSize)
}

/**
 * GET /ficheros/:file_id → `Fichero` con `fuentes` (maestro + asientos del ERP).
 *
 * `file_id` es el nombre exacto del PDF en NFC (con tildes): se normaliza y se codifica aquí.
 * Si el backend tiene `identidades` (un PDF con dos nombres), el segundo nombre también resuelve.
 */
export async function fetchFichero(fileId: string): Promise<Fichero> {
  const id = fileId.normalize('NFC')
  if (USE_MOCK) return mock.getFichero(id)
  return toFichero(await apiFetch<unknown>(`/ficheros/${encodeURIComponent(id)}`))
}
