/**
 * Thin fetch wrapper. Every network call in the app goes through here.
 *
 * - Base URL and mock switch come from `lib/config.ts`.
 * - Failures always surface as `ApiError`, so the UI can render one error state.
 * - No component ever calls `fetch` directly.
 */

import { API_BASE_URL, API_CONTRACT_VERSION, API_VERSION_HEADER } from '../config'
import { cabeceraClave, claveRechazada } from '@/components/auth/clave'

export class ApiError extends Error {
  readonly status: number
  readonly details: unknown

  constructor(message: string, status: number, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }

  get isNotFound() {
    return this.status === 404
  }

  get isUnauthorized() {
    return this.status === 401 || this.status === 403
  }

  get isNetwork() {
    return this.status === 0
  }

  /** El puente vive pero no tiene BD (503): el mensaje trae el comando que la crea. */
  get isUnavailable() {
    return this.status === 503
  }

  /** 409: la BD no tiene decisiones o mezcla cortes (bonus), o la bandeja está ocupada. */
  get isConflict() {
    return this.status === 409
  }
}

let versionAvisada = false

/**
 * El puente declara la versión de su contrato en una cabecera. Si no coincide con la que este
 * frontend entiende, se avisa una vez en consola: los mappers siguen tolerando alias, pero un
 * cambio de Miguel no debe pasar en silencio.
 */
function comprobarVersion(response: Response) {
  const declarada = response.headers.get(API_VERSION_HEADER)
  if (!declarada || versionAvisada) return
  if (Number(declarada) !== API_CONTRACT_VERSION) {
    versionAvisada = true
    console.warn(
      `[albertitos] el puente habla el contrato v${declarada} y esta consola espera v${API_CONTRACT_VERSION}: revisa lib/api/mappers.ts`,
    )
  }
}

/** Turns anything thrown by the mock or by fetch into an ApiError. */
export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (error instanceof Error) {
    const status = (error as Error & { status?: number }).status ?? 0
    return new ApiError(error.message, status)
  }
  return new ApiError('Error inesperado', 0, error)
}

export type QueryValue = string | number | boolean | undefined | null

export function buildQuery(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '' || value === 'all') return
    search.set(key, String(value))
  })
  const query = search.toString()
  return query ? `?${query}` : ''
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  if (!API_BASE_URL) {
    throw new ApiError(
      'NEXT_PUBLIC_API_URL no está definida. Defínela o deja NEXT_PUBLIC_USE_MOCK=true.',
      0,
    )
  }

  const { body, headers, ...rest } = options
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      headers: {
        Accept: 'application/json',
        ...(isFormData || body === undefined ? {} : { 'Content-Type': 'application/json' }),
        // Sin clave guardada no se manda cabecera: la petición es idéntica a la de siempre (PLAN-15).
        ...cabeceraClave(),
        ...headers,
      },
      body: body === undefined ? undefined : isFormData ? (body as FormData) : JSON.stringify(body),
    })
  } catch (error) {
    throw new ApiError(
      error instanceof Error ? error.message : 'No se pudo contactar con el backend',
      0,
      error,
    )
  }

  comprobarVersion(response)

  if (!response.ok) {
    // 401: la clave de la demo ya no vale. Se olvida y la puerta vuelve a pedirla, sin recargar.
    if (response.status === 401) claveRechazada()
    let details: unknown
    let message = `${response.status} ${response.statusText}`
    try {
      details = await response.json()
      const payload = details as { message?: string; detail?: string; error?: string }
      message = payload?.message ?? payload?.detail ?? payload?.error ?? message
    } catch {
      /* the backend did not return JSON */
    }
    throw new ApiError(message, response.status, details)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
