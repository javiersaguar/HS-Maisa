/**
 * Thin fetch wrapper. Every network call in the app goes through here.
 *
 * - Base URL and mock switch come from `lib/config.ts`.
 * - Failures always surface as `ApiError`, so the UI can render one error state.
 * - No component ever calls `fetch` directly.
 */

import { API_BASE_URL } from '../config'

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

  if (!response.ok) {
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
