import { USE_MOCK } from '../config'
import type { PanelResumen } from '../types'
import * as mock from '../mock/store'
import { apiFetch } from './client'
import { toPanel } from './mappers'

/**
 * GET /panel → `PanelResumen`
 *
 * Ficheros por lote, decisiones vigentes por resultado, pendientes, versiones que deciden hoy,
 * ritmo y coste de la última pasada y eventos por etapa. Agregados SQL: no hidrata 500 ficheros.
 */
export async function fetchPanel(): Promise<PanelResumen> {
  if (USE_MOCK) return mock.getPanel()
  return toPanel(await apiFetch<unknown>('/panel'))
}
