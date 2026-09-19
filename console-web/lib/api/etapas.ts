import { USE_MOCK } from '../config'
import type { Etapa, EtapasResumen, Event } from '../types'
import * as mock from '../mock/store'
import { apiFetch, buildQuery } from './client'
import { toEtapasResumen, toEvent } from './mappers'

/** GET /etapas → `EtapasResumen`: agregado de `eventos` por etapa y estado. */
export async function fetchEtapas(): Promise<EtapasResumen> {
  if (USE_MOCK) return mock.getEtapas()
  return toEtapasResumen(await apiFetch<unknown>('/etapas'))
}

/** GET /eventos?etapa&limit → `Event[]`: últimas filas de `eventos`. */
export async function fetchEventos(query: { etapa?: Etapa; limit?: number } = {}): Promise<Event[]> {
  if (USE_MOCK) return mock.listEventos(query)
  const payload = await apiFetch<unknown>(`/eventos${buildQuery({ etapa: query.etapa, limit: query.limit })}`)
  const items = Array.isArray(payload) ? payload : ((payload as { items?: unknown[] })?.items ?? [])
  return items.map(toEvent)
}
