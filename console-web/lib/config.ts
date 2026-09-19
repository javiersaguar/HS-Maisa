/**
 * Configuración de ejecución. Todo lo que el frontend sabe del backend vive aquí.
 *
 *   NEXT_PUBLIC_API_URL   URL base del puente de lectura (fase 3 de PLAN-ADAPTACION.md)
 *   NEXT_PUBLIC_USE_MOCK  'true' (por defecto) funciona sin red contra `lib/mock`
 *   NEXT_PUBLIC_CHAT_URL  chat de sólo lectura (K2), otro proceso: `python -m albertitos.chat --servidor`
 *
 * Con USE_MOCK a false y API_URL definida, `lib/api/*` pasa a HTTP. Ninguna página cambia.
 */

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? '').replace(/\/+$/, '')

const mockFlag = process.env.NEXT_PUBLIC_USE_MOCK

/** El mock es el defecto; HTTP exige el flag a false y una URL. */
export const USE_MOCK = mockFlag === 'false' && API_BASE_URL !== '' ? false : true

/**
 * Versión del contrato JSON que entiende esta consola (`lecturas.API_VERSION` en el backend).
 * El puente la manda en `X-Albertitos-Api` y en el campo `api` de cada colección.
 */
export const API_CONTRACT_VERSION = 1
export const API_VERSION_HEADER = 'X-Albertitos-Api'

/**
 * El chat vive en su propio proceso (:8001), no en el puente. Su CORS sólo admite `http://localhost:3000`:
 * abre la consola por `localhost`, no por `127.0.0.1`, o el POST se rechaza.
 */
export const CHAT_URL = (process.env.NEXT_PUBLIC_CHAT_URL ?? 'http://127.0.0.1:8001').replace(/\/+$/, '')

export const BRAND = 'Albertitos'

/** El ERP de Alberto: un bridge Oracle de 2009 que se descarga en snapshots (v1, v2). */
export const ERP_NOMBRE = 'ERP 2009'

/** Refresco en segundo plano de las superficies "en vivo": panel y etapas. */
export const LIVE_POLL_INTERVAL_MS = 10_000
