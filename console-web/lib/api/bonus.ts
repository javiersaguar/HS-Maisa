import { USE_MOCK } from '../config'
import type { BonusResumen, Calendario, Pago } from '../types'
import { apiFetch, buildQuery } from './client'

/**
 * Calendario de pagos y tesorería (bonus K1). Contrato: docs/api/bonus.md. Sólo lectura: el backend
 * recalcula en cada GET a partir de las decisiones PAGAR vigentes; aquí no se suma ni se decide nada.
 *
 * Los tipos llevan los nombres del contrato tal cual (snake_case), así que no hay mapper: lo que llega
 * es lo que se pinta. 400/409 traen `error` para una persona y `apiFetch` lo deja en `ApiError.message`.
 */

export interface CalendarioQuery {
  semana?: string
  /** `P001` o la razón social exacta. */
  proveedor?: string
  lote?: number
  vencido?: boolean
  limite?: number
  conConfianza?: boolean
  estricto?: boolean
}

/* ------------------------------------------------------------------ mock --- */

/** `bonus.json` trae también proveedores, avisos y tesorería; la consola ya sólo lee estas dos. */
interface MockBonus {
  resumen: BonusResumen
  calendario: Pago[]
}

let mockData: Promise<MockBonus> | null = null

/** `lib/mock/bonus.json`: las rutas del bonus sobre la BD real del lote 1 (mismas cifras que docs/api/ejemplos). */
function mock(): Promise<MockBonus> {
  mockData ??= import('../mock/bonus.json').then(
    (module) => new Promise<MockBonus>((resolve) => setTimeout(() => resolve(module.default as unknown as MockBonus), 120)),
  )
  return mockData
}


const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

/* ------------------------------------------------------------------ rutas --- */

/** GET /bonus/resumen: totales, vencido, avisos por código, lotes y semanas. */
export async function fetchBonusResumen(estricto = false): Promise<BonusResumen> {
  if (USE_MOCK) return clone((await mock()).resumen)
  return apiFetch<BonusResumen>(`/bonus/resumen${buildQuery({ estricto: estricto || undefined })}`)
}

/** GET /bonus/calendario: pagos filtrados, ordenados por vencimiento. */
export async function fetchCalendario(query: CalendarioQuery = {}): Promise<Calendario> {
  if (USE_MOCK) {
    const data = await mock()
    const proveedor = query.proveedor
    const pagos = data.calendario.filter(
      (pago) =>
        (!query.semana || pago.semana === query.semana) &&
        (!proveedor || pago.proveedor_id === proveedor || pago.beneficiario === proveedor) &&
        (query.lote === undefined || pago.lote === query.lote) &&
        (query.vencido === undefined || pago.vencido === query.vencido),
    )
    const limite = query.limite ?? 500
    return clone({
      filtros: {
        semana: query.semana ?? null,
        proveedor: proveedor ?? null,
        lote: query.lote ?? null,
        vencido: query.vencido ?? null,
      },
      total: pagos.length,
      mostrados: Math.min(limite, pagos.length),
      pagos: pagos.slice(0, limite),
    })
  }
  return apiFetch<Calendario>(
    `/bonus/calendario${buildQuery({
      semana: query.semana,
      proveedor: query.proveedor,
      lote: query.lote,
      vencido: query.vencido,
      limite: query.limite,
      con_confianza: query.conConfianza || undefined,
      estricto: query.estricto || undefined,
    })}`,
  )
}
