import { API_BASE_URL, USE_MOCK } from '../config'
import type { Salud } from '../types'
import * as mock from '../mock/store'
import { apiFetch } from './client'
import { toSalud } from './mappers'

/**
 * GET /salud
 *
 * Es la única lectura que responde aunque no exista `dist/albertitos.db`: dice si el puente vive,
 * si tiene BD y cuántos ficheros/decisiones hay. La barra lateral la usa para que nadie enseñe
 * datos de ejemplo creyendo que son la Caja.
 */
export async function fetchSalud(): Promise<Salud> {
  if (USE_MOCK) return mock.getSalud()
  return toSalud(await apiFetch<unknown>('/salud'))
}

/** Dónde pega la consola, para enseñarlo en la UI. */
export const ORIGEN_DATOS = USE_MOCK ? 'Datos de ejemplo' : API_BASE_URL.replace(/^https?:\/\//, '')
