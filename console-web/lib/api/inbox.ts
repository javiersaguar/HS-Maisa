import { USE_MOCK } from '../config'
import type { EstadoFichero } from '../types'
import { ApiError, apiFetch } from './client'

/** Lote de la bandeja: fuera de la entrega (`package` sólo emite los lotes 1 y 2). */
export const LOTE_BANDEJA = 99

export type EstadoBandeja = 'idle' | 'ingiriendo' | 'extrayendo' | 'decidiendo' | 'listo' | 'error'

export interface Bandeja {
  estado: EstadoBandeja
  fileIds: string[]
  /** Resultado de cada fichero en la BD: null si ni siquiera se ingirió (PDF ilegible). */
  ficheros: Array<{ fileId: string; nombre: string; estado: EstadoFichero | null }>
  log: string[]
  error: string | null
  /** false si el puente sirve la BD de la entrega: arráncalo con `--bandeja`. */
  disponible: boolean
  /** true en la demo pública: la bandeja es una copia en disco temporal que se rehace al reiniciar. */
  efimera: boolean
  /** Plazas que quedan en este arranque (cupo del servidor público); null si no hay cupo. */
  restantes: number | null
}

export const BANDEJA_EN_CURSO: EstadoBandeja[] = ['ingiriendo', 'extrayendo', 'decidiendo']

const SIN_MOCK =
  'Con datos de ejemplo no se suben facturas: arranca el puente con `--bandeja` y NEXT_PUBLIC_USE_MOCK=false.'

function toBandeja(raw: unknown): Bandeja {
  const r = (raw ?? {}) as Record<string, unknown>
  const ficheros = Array.isArray(r.ficheros) ? (r.ficheros as Array<Record<string, unknown>>) : []
  return {
    estado: (r.estado as EstadoBandeja) ?? 'idle',
    fileIds: Array.isArray(r.file_ids) ? (r.file_ids as string[]) : [],
    ficheros: ficheros.map((f) => ({
      fileId: String(f.file_id ?? ''),
      // el nombre subido: el file_id puede ser `./<nombre>` (nombre ya usado en la Caja) o el del original
      nombre: String(f.nombre ?? f.file_id ?? ''),
      estado: (f.estado as EstadoFichero | null) ?? null,
    })),
    log: Array.isArray(r.log) ? (r.log as string[]) : [],
    error: (r.error as string | null) ?? null,
    disponible: r.disponible !== false,
    efimera: r.efimera === true,
    restantes: typeof r.restantes_arranque === 'number' ? r.restantes_arranque : null,
  }
}

/**
 * POST /inbox (multipart): el puente guarda los PDF, los ingiere en el lote 99 y lanza extract +
 * decide por la CLI en segundo plano. Devuelve los file_id (NFC) en cuanto están ingeridos.
 */
export async function subirFacturas(files: File[]): Promise<{ fileIds: string[] }> {
  if (USE_MOCK) throw new ApiError(SIN_MOCK, 0)
  const form = new FormData()
  files.forEach((file) => form.append('ficheros', file, file.name.normalize('NFC')))
  const r = await apiFetch<{ file_ids?: string[] }>('/inbox', { method: 'POST', body: form })
  return { fileIds: r?.file_ids ?? [] }
}

/** GET /inbox: en qué paso va el trabajo y el resultado de cada fichero. */
export async function fetchBandeja(): Promise<Bandeja> {
  if (USE_MOCK) throw new ApiError(SIN_MOCK, 0)
  return toBandeja(await apiFetch<unknown>('/inbox'))
}
