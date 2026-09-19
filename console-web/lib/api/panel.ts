import { USE_MOCK } from '../config'
import type { PanelResumen } from '../types'
import * as mock from '../mock/store'
import { apiFetch } from './client'
import { toPanel } from './mappers'

/**
 * GET /panel (provisional, fase 3)
 *
 * Contadores de la vista Panel de Streamlit: ficheros por lote, decisiones vigentes por resultado,
 * pendientes, versiones cargadas y eventos por etapa.
 */
export async function fetchPanel(): Promise<PanelResumen> {
  if (USE_MOCK) return mock.getPanel()
  return toPanel(await apiFetch<unknown>('/panel'))
}
