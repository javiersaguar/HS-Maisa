import { USE_MOCK } from '../config'
import type { PasoTraza, TrazaQuery } from '../types'
import * as mock from '../mock/store'
import { apiFetch, buildQuery } from './client'
import { toTraza } from './mappers'

/**
 * GET /traza?file_id&etapa&categoria → `PasoTraza[]`
 *
 * Alimenta la Chain of Work: `/audit`, la pestaña Traza del fichero y el detalle de etapa.
 * Equivale a `albertitos trace <file_id>` / `core.db.traza()`: eventos del fichero + motivos de su
 * decisión vigente. Sin `file_id`, los pasos más recientes de todo el pipeline.
 */
export async function fetchTraza(query: TrazaQuery = {}): Promise<PasoTraza[]> {
  if (USE_MOCK) return mock.listTraza(query)
  const search = buildQuery({
    file_id: query.file_id?.normalize('NFC'),
    etapa: query.etapa,
    categoria: query.categoria,
  })
  return toTraza(await apiFetch<unknown>(`/traza${search}`))
}
