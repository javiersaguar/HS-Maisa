import { USE_MOCK } from '../config'
import type { AvisoBonus, BonusResumen, Calendario, Pago, ProveedorPago, Remesa, Tesoreria } from '../types'
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

interface MockBonus {
  resumen: BonusResumen
  proveedores: { proveedores: ProveedorPago[] }
  avisos: { total: number; avisos: AvisoBonus[] }
  calendario: Pago[]
  tesoreria: Tesoreria
  programas: Record<string, NonNullable<Tesoreria['programa']>>
}

let mockData: Promise<MockBonus> | null = null

/** `lib/mock/bonus.json`: las rutas del bonus sobre la BD real del lote 1 (mismas cifras que docs/api/ejemplos). */
function mock(): Promise<MockBonus> {
  mockData ??= import('../mock/bonus.json').then(
    (module) => new Promise<MockBonus>((resolve) => setTimeout(() => resolve(module.default as unknown as MockBonus), 120)),
  )
  return mockData
}

function mockError(message: string, status: number): never {
  const error = new Error(message) as Error & { status?: number }
  error.status = status
  throw error
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

/** GET /bonus/proveedores: de mayor a menor importe. */
export async function fetchProveedores(): Promise<ProveedorPago[]> {
  if (USE_MOCK) return clone((await mock()).proveedores.proveedores)
  return (await apiFetch<{ proveedores: ProveedorPago[] }>('/bonus/proveedores')).proveedores
}

/** GET /bonus/remesa: sólo los pagos que entran en el borrador de remesa. */
export async function fetchRemesa(limite?: number): Promise<Remesa> {
  if (USE_MOCK) {
    const data = await mock()
    const pagos = data.calendario.filter((pago) => pago.apto_remesa)
    const shown = pagos.slice(0, limite ?? 500)
    return clone({
      tipo: data.resumen.tipo,
      iban_sin_control: pagos.filter((pago) => !pago.iban_control_ok).length,
      total: pagos.length,
      mostrados: shown.length,
      pagos: shown,
    })
  }
  return apiFetch<Remesa>(`/bonus/remesa${buildQuery({ limite })}`)
}

/** GET /bonus/avisos */
export async function fetchAvisos(): Promise<{ total: number; avisos: AvisoBonus[] }> {
  if (USE_MOCK) return clone((await mock()).avisos)
  return apiFetch<{ total: number; avisos: AvisoBonus[] }>('/bonus/avisos')
}

/**
 * GET /bonus/tesoreria?tope=: semanas con importe, vencido y acumulado; con `tope`, el programa que
 * reparte lo pendiente en semanas de como mucho ese importe.
 *
 * El mock no calcula programas (sería repetir la lógica del backend en el navegador): trae los de
 * 100.000 a 300.000 € y para otro tope responde 400 diciéndolo.
 */
export async function fetchTesoreria(tope?: number): Promise<Tesoreria> {
  if (USE_MOCK) {
    const data = await mock()
    if (tope === undefined) return clone(data.tesoreria)
    const programa = data.programas[String(tope)]
    if (!programa) {
      const disponibles = Object.keys(data.programas)
        .map((valor) => Number(valor).toLocaleString('es-ES'))
        .join(', ')
      mockError(`Con datos de ejemplo sólo hay programa para ${disponibles} €. Conecta el puente para otro tope.`, 400)
    }
    return clone({ ...data.tesoreria, programa })
  }
  return apiFetch<Tesoreria>(`/bonus/tesoreria${buildQuery({ tope })}`)
}
