/**
 * Cliente del chat de sólo lectura (proceso aparte en :8001, `make chat`). No pasa por el puente de :8000:
 * el chat necesita POST y el puente es sólo GET.
 *
 *   NEXT_PUBLIC_CHAT_URL        URL del chat (por defecto http://127.0.0.1:8001)
 *   NEXT_PUBLIC_CHAT_GRABADAS   'true': el panel aparece aunque no haya servidor, en modo «respuestas grabadas»
 *
 * Contratos: `GET /chat/salud` v2 (docs/agentes/PLAN-13.md) y `POST /chat` (docs/api/chat.md).
 */

import { ApiError } from './client'

export const CHAT_URL = (process.env.NEXT_PUBLIC_CHAT_URL ?? 'http://127.0.0.1:8001').replace(/\/+$/, '')

/** Con el servidor apagado, el panel sólo aparece si se pide el modo grabado (o con USE_MOCK). */
export const CHAT_GRABADAS = process.env.NEXT_PUBLIC_CHAT_GRABADAS === 'true'

export const MAX_MENSAJE = 4000
export const MAX_HISTORIAL = 10
const TIMEOUT_SALUD_MS = 2_000
/** El servidor se da 60 s por pregunta; la interfaz espera un poco más para ver su respuesta degradada. */
const TIMEOUT_PREGUNTA_MS = 70_000

export type EstadoChat = 'ok' | 'solo_lectura' | 'sin_datos' | 'sin_evidencia' | 'limite' | 'degradado'
const ESTADOS: readonly EstadoChat[] = ['ok', 'solo_lectura', 'sin_datos', 'sin_evidencia', 'limite', 'degradado']

export interface RespuestaChat {
  respuesta: string
  citas: string[]
  herramientas_usadas: string[]
  modelo: string | null
  latencia_ms: number
  estado: EstadoChat
  /** Saldo después de contestar; los servidores antiguos pueden omitirlo. */
  llamadas_restantes?: number | null
  /** true si contestó el modelo de respaldo (PLAN-13, B4). */
  respaldo?: boolean
}

export type MotivoSinModelo = 'sin_clave' | 'fuera_de_ventana' | 'presupuesto_agotado' | 'breaker'

export interface VentanaChat {
  desde: string | null
  hasta: string | null
}

export interface SaludChat {
  /** false: el servidor no contesta (apagado, otro puerto, CORS) o tarda más de 2 s. */
  ok: boolean
  api?: number
  solo_lectura?: boolean
  bd_disponible?: boolean
  /** true / false según el servidor; null si el servidor es anterior al contrato v2 y no lo dice. */
  modelo_disponible?: boolean | null
  motivo?: MotivoSinModelo | string | null
  modelo?: string | null
  respaldo?: string | null
  llamadas_restantes?: number | null
  max_llamadas?: number | null
  ventana?: VentanaChat | null
}

export interface MensajeHistorial {
  role: 'user' | 'assistant'
  content: string
}

function conTiempo(ms: number, externa?: AbortSignal): { signal: AbortSignal; limpiar: () => void } {
  const control = new AbortController()
  const temporizador = setTimeout(() => control.abort(new DOMException('timeout', 'TimeoutError')), ms)
  const alAbortar = () => control.abort(externa?.reason)
  externa?.addEventListener('abort', alAbortar, { once: true })
  return {
    signal: control.signal,
    limpiar: () => {
      clearTimeout(temporizador)
      externa?.removeEventListener('abort', alAbortar)
    },
  }
}

/** GET /chat/salud: nunca lanza. Sin respuesta en 2 s, `{ok: false}`. No gasta llamadas al modelo. */
export async function chatSalud(signal?: AbortSignal): Promise<SaludChat> {
  const { signal: s, limpiar } = conTiempo(TIMEOUT_SALUD_MS, signal)
  try {
    const r = await fetch(`${CHAT_URL}/chat/salud`, { headers: { Accept: 'application/json' }, signal: s })
    if (!r.ok) return { ok: false }
    const cuerpo = (await r.json()) as Partial<SaludChat> & Record<string, unknown>
    if (cuerpo?.ok !== true) return { ok: false }
    if (cuerpo.api !== 2 || typeof cuerpo.modelo_disponible !== 'boolean') {
      // Backend anterior al PLAN-13 (api 1): vive, pero no dice si hay modelo. No se inventa.
      return {
        ok: true,
        api: typeof cuerpo.api === 'number' ? cuerpo.api : 1,
        solo_lectura: cuerpo.solo_lectura,
        bd_disponible: cuerpo.bd_disponible,
        modelo_disponible: null,
      }
    }
    return {
      ok: true,
      api: 2,
      solo_lectura: cuerpo.solo_lectura,
      bd_disponible: cuerpo.bd_disponible,
      modelo_disponible: cuerpo.modelo_disponible,
      motivo: cuerpo.motivo ?? null,
      modelo: cuerpo.modelo ?? null,
      respaldo: cuerpo.respaldo ?? null,
      llamadas_restantes: typeof cuerpo.llamadas_restantes === 'number' ? cuerpo.llamadas_restantes : null,
      max_llamadas: typeof cuerpo.max_llamadas === 'number' ? cuerpo.max_llamadas : null,
      ventana: cuerpo.ventana ?? null,
    }
  } catch {
    return { ok: false }
  } finally {
    limpiar()
  }
}

/** null si el mensaje vale; si no, por qué (antes de enviarlo). */
export function validarMensaje(mensaje: string): string | null {
  const texto = mensaje.trim()
  if (!texto) return 'Escribe una pregunta.'
  if (texto.length > MAX_MENSAJE) return `La pregunta tiene ${texto.length} caracteres; el máximo es ${MAX_MENSAJE}.`
  return null
}

const ERRORES_POR_ESTADO: Record<number, string> = {
  400: 'Petición no válida.',
  403: 'Este origen no está autorizado por el chat (ALBERTITOS_CHAT_ORIGENES).',
  413: 'La pregunta es demasiado larga.',
  415: 'El chat sólo acepta JSON.',
  429: 'Ya hay una consulta en curso: espera a que termine.',
}

function esRespuesta(x: unknown): x is RespuestaChat {
  const r = x as RespuestaChat
  return (
    !!r &&
    typeof r.respuesta === 'string' &&
    Array.isArray(r.citas) &&
    ESTADOS.includes(r.estado) &&
    typeof r.latencia_ms === 'number'
  )
}

/**
 * POST /chat. Lanza `ApiError` con el texto del servidor tal cual (400/403/413/415/429), o con el motivo de red o de
 * tiempo. El historial se recorta a las últimas 10 entradas.
 */
export async function preguntar(
  mensaje: string,
  historial: MensajeHistorial[] = [],
  signal?: AbortSignal,
): Promise<RespuestaChat> {
  const invalido = validarMensaje(mensaje)
  if (invalido) throw new ApiError(invalido, 400)
  const { signal: s, limpiar } = conTiempo(TIMEOUT_PREGUNTA_MS, signal)
  let r: Response
  try {
    r = await fetch(`${CHAT_URL}/chat`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ mensaje: mensaje.trim(), historial: historial.slice(-MAX_HISTORIAL) }),
      signal: s,
    })
  } catch (error) {
    limpiar()
    const tiempo = s.aborted && !signal?.aborted
    throw new ApiError(
      tiempo
        ? 'El chat no ha contestado en 70 s. La decisión y su traza siguen en la consola.'
        : `No se pudo contactar con el chat en ${CHAT_URL}. ¿Está arrancado (make chat)?`,
      0,
      error,
    )
  }
  try {
    let cuerpo: unknown = null
    try {
      cuerpo = await r.json()
    } catch {
      /* sin JSON */
    }
    if (!r.ok) {
      const texto = (cuerpo as { error?: string } | null)?.error
      throw new ApiError((r.status === 429 ? ERRORES_POR_ESTADO[429] : texto) || ERRORES_POR_ESTADO[r.status] || `${r.status} ${r.statusText}`, r.status, cuerpo)
    }
    if (!esRespuesta(cuerpo)) throw new ApiError('El chat devolvió una respuesta con forma inesperada.', r.status, cuerpo)
    return cuerpo
  } finally {
    limpiar()
  }
}

/** El motivo de `/chat/salud` en castellano, para la línea de estado. */
export function describirMotivo(salud: SaludChat): string {
  switch (salud.motivo) {
    case 'sin_clave':
      return 'sin clave del LLM'
    case 'fuera_de_ventana': {
      const desde = salud.ventana?.desde ? formatearHora(salud.ventana.desde) : null
      return desde ? `fuera de horario (abre ${desde})` : 'fuera de horario'
    }
    case 'presupuesto_agotado':
      return 'sin llamadas disponibles'
    case 'breaker':
      return 'el proveedor está fallando; reintenta en un minuto'
    default:
      return salud.motivo ? String(salud.motivo) : 'no disponible'
  }
}

/** '2026-09-20T09:00:00+02:00' → 'dom 20/09 09:00', en hora de Madrid. */
export function formatearHora(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const partes = Object.fromEntries(
    new Intl.DateTimeFormat('es-ES', {
      timeZone: 'Europe/Madrid',
      weekday: 'short',
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
    })
      .formatToParts(d)
      .map((p) => [p.type, p.value]),
  )
  return `${partes.weekday} ${partes.day}/${partes.month} ${partes.hour}:${partes.minute}`
}
