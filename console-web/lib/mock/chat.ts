/**
 * Las 15 respuestas REALES de la evaluación del chat (19/09, 14:58-15:04, deepseek-v4-flash, copia de la BD real),
 * copiadas de docs/api/ejemplos/chat-*.json sin tocar el texto (sólo se quita la evidencia de las herramientas).
 *
 * Sirven para enseñar el chat cuando el modelo no está disponible, SIEMPRE con la etiqueta «respuesta grabada · no es
 * una consulta en vivo». `respuestaGrabada()` sólo encuentra la pregunta exacta: nunca inventa una respuesta.
 */

import type { RespuestaChat } from '@/lib/api/chat'
import c1 from './chat/chat-01-resumen.json'
import c2 from './chat/chat-02-pagar.json'
import c3 from './chat/chat-03-pagada.json'
import c4 from './chat/chat-04-instruccion.json'
import c5 from './chat/chat-05-duplicado.json'
import c6 from './chat/chat-06-semana.json'
import c7 from './chat/chat-07-pagos.json'
import c8 from './chat/chat-08-proveedor.json'
import c9 from './chat/chat-09-inexistente.json'
import c10 from './chat/chat-10-scan.json'
import c11 from './chat/chat-11-versiones.json'
import c12 from './chat/chat-12-escalados.json'
import c13 from './chat/chat-13-trampa_inyeccion.json'
import c14 from './chat/chat-14-trampa_pagar.json'
import c15 from './chat/chat-15-sin_datos.json'

export const GRABACION = 'evaluación 19/09 15:00'
export const ETIQUETA_GRABADA = 'respuesta grabada · no es una consulta en vivo'

export interface RespuestaGrabada {
  fuente: string
  pregunta: string
  respuesta: RespuestaChat
  evaluacion: { veredicto: string | null; observacion: string | null }
}

export const RESPUESTAS_GRABADAS: readonly RespuestaGrabada[] = [
  c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14, c15,
] as RespuestaGrabada[]

const normalizar = (s: string) => s.normalize('NFC').trim().replace(/\s+/g, ' ')

/** La respuesta grabada de ESA pregunta (texto exacto, salvo espacios), o null. Nunca se inventa una. */
export function respuestaGrabada(pregunta: string): RespuestaGrabada | null {
  const buscada = normalizar(pregunta)
  return RESPUESTAS_GRABADAS.find((r) => normalizar(r.pregunta) === buscada) ?? null
}

/**
 * Las sugerencias del panel: el texto EXACTO de su pregunta grabada, para que el modo grabado la encuentre y para que
 * en vivo se pregunte lo mismo que se evaluó.
 */
export const SUGERENCIAS: readonly string[] = [c1.pregunta, c4.pregunta, c5.pregunta, c6.pregunta]
