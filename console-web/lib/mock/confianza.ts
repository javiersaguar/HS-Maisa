/**
 * K3 sin puente: sirve las respuestas reales de docs/api/ejemplos/confianza-*.json (copiadas aquí).
 *
 * Los ejemplos hablan de ficheros de la Caja (`scan_021.pdf`…) que el mock no tiene, así que se superponen sobre
 * los `file_id` del mock: las filas de «revisar primero» caen en los primeros ESCALAR, el resto de ESCALAR sale en
 * media como el ejemplo de política, los NO_PAGAR como el de NO_PAGAR y los PAGAR en alta/100. El resumen es el real.
 * Nada de aquí se importa desde la UI.
 */

import type {
  ConfianzaFicha,
  ConfianzaItem,
  ConfianzaLista,
  ConfianzaQuery,
  ConfianzaResumen,
} from '../types'
import { FICHEROS } from './data'
import fichaLectura from './confianza-fichero-escalar-lectura.json'
import fichaPolitica from './confianza-fichero-escalar-politica.json'
import fichaNoPagar from './confianza-fichero-no-pagar.json'
import fichaPagar from './confianza-fichero-pagar-plantilla.json'
import revisarPrimero from './confianza-ficheros-revisar-primero.json'
import resumen from './confianza-resumen.json'

const delay = (ms = 120) => new Promise<void>((resolve) => setTimeout(resolve, ms))
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

function notFound(fileId: string): never {
  const error = new Error(`${fileId} no tiene decisión vigente`) as Error & { status?: number }
  error.status = 404
  throw error
}

/** La ficha de ejemplo que se usa como plantilla para cada fila superpuesta. */
const plantillas = new Map<string, ConfianzaFicha>()

function fila(fileId: string, lote: number, ficha: ConfianzaFicha, base?: ConfianzaItem): ConfianzaItem {
  const item: ConfianzaItem = base
    ? { ...base, file_id: fileId, lote }
    : {
        file_id: fileId,
        lote,
        resultado: ficha.resultado,
        regla: ficha.regla,
        puntuacion: ficha.puntuacion,
        banda: ficha.banda,
        razon_principal: ficha.razones[0] ?? '',
        razones: ficha.razones,
      }
  plantillas.set(fileId, ficha)
  return item
}

const ITEMS: ConfianzaItem[] = (() => {
  const baja = [...(revisarPrimero.items as ConfianzaItem[])]
  return FICHEROS.flatMap((fichero): ConfianzaItem[] => {
    switch (fichero.estado) {
      case 'ESCALAR': {
        const base = baja.shift()
        return [base ? fila(fichero.file_id, fichero.lote, fichaLectura as ConfianzaFicha, base) : fila(fichero.file_id, fichero.lote, fichaPolitica as ConfianzaFicha)]
      }
      case 'NO_PAGAR':
        return [fila(fichero.file_id, fichero.lote, fichaNoPagar as ConfianzaFicha)]
      case 'PAGAR':
        return [fila(fichero.file_id, fichero.lote, fichaPagar as ConfianzaFicha)]
      default:
        return [] // sin decisión vigente: la API no la puntúa
    }
  })
})()

export async function getResumen(lote?: number): Promise<ConfianzaResumen> {
  await delay()
  const body = clone(resumen) as ConfianzaResumen
  if (lote === undefined) return body
  const bandas = body.por_lote?.[String(lote)] ?? { alta: 0, media: 0, baja: 0 }
  return { ...body, bandas, total: bandas.alta + bandas.media + bandas.baja }
}

export async function listFicheros(query: ConfianzaQuery = {}): Promise<ConfianzaLista> {
  await delay()
  const filtrados = ITEMS.filter(
    (item) =>
      (!query.banda || item.banda === query.banda) &&
      (!query.resultado || item.resultado === query.resultado) &&
      (query.lote === undefined || item.lote === query.lote),
  ).sort((a, b) => (query.orden === 'desc' ? b.puntuacion - a.puntuacion : a.puntuacion - b.puntuacion))
  const limite = Math.min(Math.max(query.limite ?? 50, 1), 1000)
  return clone({ api: 1, items: filtrados.slice(0, limite), total: filtrados.length, limite })
}

export async function getFichero(fileId: string): Promise<ConfianzaFicha> {
  await delay()
  const item = ITEMS.find((candidato) => candidato.file_id === fileId)
  const plantilla = plantillas.get(fileId)
  if (!item || !plantilla) notFound(fileId)
  const { file_id, lote, resultado, regla, puntuacion, banda, razones } = item
  return clone({ ...plantilla, file_id, lote, resultado, regla, puntuacion, banda, razones })
}
