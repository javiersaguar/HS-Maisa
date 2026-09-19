import { CHAT_URL, USE_MOCK } from '../config'
import type { ChatRespuesta, ChatTurno } from '../types'
import { ApiError } from './client'

/**
 * Chat de sólo lectura (bonus K2). Contrato: docs/api/chat.md.
 *
 * Otro proceso y otro origen (`CHAT_URL`, :8001), así que no pasa por `apiFetch` del puente. No hay
 * POST en :8000. Si `/chat/salud` no responde, el panel no se enseña. Con datos de ejemplo, tampoco:
 * sus citas apuntarían a ficheros que el mock no tiene.
 */

/** Algo más que el presupuesto de 60 s por pregunta del servidor. */
const TIMEOUT_MS = 70_000

let sondeo: Promise<boolean> | null = null

export function chatDisponible(): Promise<boolean> {
  if (USE_MOCK) return Promise.resolve(false)
  sondeo ??= fetch(`${CHAT_URL}/chat/salud`, { headers: { Accept: 'application/json' } })
    .then(async (response) => response.ok && Boolean(((await response.json()) as { ok?: boolean }).ok))
    .catch(() => false)
  return sondeo
}

/** POST /chat. 200 también en degradación controlada: mirar `estado`. */
export async function preguntar(mensaje: string, historial: ChatTurno[] = []): Promise<ChatRespuesta> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  let response: Response
  try {
    response = await fetch(`${CHAT_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ mensaje, historial: historial.slice(-10) }),
      signal: controller.signal,
    })
  } catch (error) {
    const abortado = error instanceof DOMException && error.name === 'AbortError'
    throw new ApiError(abortado ? 'El chat no respondió en 70 s.' : 'No se puede contactar con el chat.', 0, error)
  } finally {
    clearTimeout(timer)
  }
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`
    try {
      message = ((await response.json()) as { error?: string }).error ?? message
    } catch {
      /* sin JSON */
    }
    throw new ApiError(message, response.status)
  }
  return (await response.json()) as ChatRespuesta
}
