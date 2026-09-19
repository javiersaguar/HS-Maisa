'use client'

import type { CSSProperties } from 'react'
import { ChevronLeft, ChevronRight, Info } from 'lucide-react'
import type { Pago } from '@/lib/types'
import { formatImporte, formatNumber } from '@/lib/format'

/** Lo que cae en un día de ejecución. El importe va en céntimos enteros: nunca se suma con `Number` a flote. */
export interface DiaPagos {
  fecha: string
  pagos: Pago[]
  centimos: number
}

/** "8107.54" → 810754, sin pasar por coma flotante. */
export function aCentimos(importe: string): number {
  const [enteros, decimales = ''] = importe.trim().split('.')
  return Number(enteros) * 100 + Number(`${decimales}00`.slice(0, 2))
}

/** 810754 → "8107.54", para pintarlo con `formatImporte`. */
export function deCentimos(centimos: number): string {
  return `${Math.floor(centimos / 100)}.${String(centimos % 100).padStart(2, '0')}`
}

/** Agrupa por `fecha_ejecucion` (ISO). */
export function agruparPorDia(pagos: Pago[]): Map<string, DiaPagos> {
  const dias = new Map<string, DiaPagos>()
  for (const pago of pagos) {
    const dia = dias.get(pago.fecha_ejecucion) ?? { fecha: pago.fecha_ejecucion, pagos: [], centimos: 0 }
    dia.pagos.push(pago)
    dia.centimos += aCentimos(pago.importe_eur)
    dias.set(pago.fecha_ejecucion, dia)
  }
  return dias
}

/** Letra del sistema (Segoe UI, SF, Roboto): más limpia que el Arial global y sin descargar nada. */
export const LETRA: CSSProperties = {
  fontFamily: 'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  fontFeatureSettings: '"tnum" 1',
}

const DIAS_SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

/** "2026-09" → "Septiembre 2026" */
const nombreMes = (mes: string) => {
  const texto = new Date(`${mes}-01T00:00:00Z`).toLocaleDateString('es-ES', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })
  return texto.charAt(0).toLocaleUpperCase('es-ES') + texto.slice(1).replace(' de ', ' ')
}

interface Celda {
  fecha: string
  fuera: boolean
}

/** Seis semanas de lunes a domingo, con los días de los meses vecinos para que la rejilla no baile. */
function celdas(mes: string): Celda[] {
  const [anio, numero] = mes.split('-').map(Number)
  const hueco = (new Date(Date.UTC(anio, numero - 1, 1)).getUTCDay() + 6) % 7
  return Array.from({ length: 42 }, (_, index) => {
    const fecha = new Date(Date.UTC(anio, numero - 1, 1 - hueco + index)).toISOString().slice(0, 10)
    return { fecha, fuera: !fecha.startsWith(mes) }
  })
}

/** Tres tonos del verde de la marca según el importe del día, en escala logarítmica (431 facturas frente a 1). */
const TONOS = [
  { caja: 'bg-accent-soft text-accent-dark', sub: 'text-accent-dark' },
  { caja: 'bg-accent-line text-accent-dark', sub: 'text-accent-dark' },
  { caja: 'bg-accent-dark text-canvas', sub: 'text-canvas/75' },
]

function tono(centimos: number, maximo: number) {
  const nivel = maximo > 0 ? Math.log10(1 + centimos) / Math.log10(1 + maximo) : 0
  return TONOS[nivel > 0.9 ? 2 : nivel > 0.75 ? 1 : 0]
}

export function CalendarioMes({
  mes,
  meses,
  onMes,
  dias,
  fechaCorte,
  diaActivo,
  onDia,
}: {
  /** `YYYY-MM` que se enseña. */
  mes: string
  /** Meses con algún pago, ordenados: las flechas sólo saltan entre ellos. */
  meses: string[]
  onMes: (mes: string) => void
  dias: Map<string, DiaPagos>
  fechaCorte: string | null
  /** El día cuyo overlay está abierto; null si no hay ninguno. */
  diaActivo: string | null
  onDia: (fecha: string) => void
}) {
  const indice = meses.indexOf(mes)
  const anterior = indice > 0 ? meses[indice - 1] : null
  const siguiente = indice >= 0 && indice < meses.length - 1 ? meses[indice + 1] : null

  const delMes = [...dias.values()].filter((dia) => dia.fecha.startsWith(mes))
  const facturasMes = delMes.reduce((suma, dia) => suma + dia.pagos.length, 0)
  const centimosMes = delMes.reduce((suma, dia) => suma + dia.centimos, 0)
  const maximo = Math.max(0, ...delMes.map((dia) => dia.centimos))

  const flecha =
    'inline-flex size-10 items-center justify-center rounded-full border border-line bg-surface text-accent-dark shadow-[0_1px_2px_rgba(43,55,51,0.06)] transition hover:border-accent hover:bg-accent-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-dark/30 disabled:cursor-default disabled:border-line-soft disabled:bg-transparent disabled:text-muted/60 disabled:shadow-none'

  return (
    <section
      aria-label={`Pagos de ${nombreMes(mes)}`}
      style={LETRA}
      className="flex h-full min-h-[600px] flex-col rounded-2xl border border-line bg-surface px-4 pt-5 pb-4 shadow-[0_8px_28px_rgba(43,55,51,0.05)] sm:px-6"
    >
      <header className="flex flex-col items-center gap-1.5">
        <div className="flex items-center gap-5">
          <button onClick={() => anterior && onMes(anterior)} disabled={!anterior} aria-label="Mes anterior" className={flecha}>
            <ChevronLeft className="size-5" />
          </button>
          <h1 className="min-w-[220px] text-center text-[28px] font-semibold tracking-[-0.02em] text-ink">
            {nombreMes(mes)}
          </h1>
          <button
            onClick={() => siguiente && onMes(siguiente)}
            disabled={!siguiente}
            aria-label="Mes siguiente"
            className={flecha}
          >
            <ChevronRight className="size-5" />
          </button>
        </div>
        <p className="text-[13px] text-ink-soft">
          {facturasMes > 0 ? (
            <>
              <span className="font-semibold text-accent-dark">{formatNumber(facturasMes)} facturas</span> a pagar ·{' '}
              <span className="font-semibold text-accent-dark">{formatImporte(deCentimos(centimosMes))}</span>
            </>
          ) : (
            'Sin pagos este mes'
          )}
        </p>
      </header>

      <div className="mt-5 grid grid-cols-7 pb-2 text-[12px] font-medium text-muted">
        {DIAS_SEMANA.map((dia, index) => (
          <span key={dia} className={`px-3 ${index > 4 ? 'text-muted' : ''}`}>
            {dia}
          </span>
        ))}
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-7 grid-rows-[repeat(6,minmax(0,1fr))] gap-px overflow-hidden rounded-xl border border-line bg-raised">
        {celdas(mes).map(({ fecha, fuera }, index) => {
          const numero = Number(fecha.slice(8))
          const dia = fuera ? undefined : dias.get(fecha)
          const corte = fecha === fechaCorte && !fuera
          const activo = fecha === diaActivo
          const fondo = fuera ? 'bg-canvas' : index % 7 > 4 ? 'bg-canvas/60' : 'bg-surface'

          const cabecera = (
            <span className="flex shrink-0 items-center gap-1.5">
              <span
                className={`inline-flex size-6 shrink-0 items-center justify-center rounded-full text-[12px] ${
                  corte
                    ? 'bg-accent-dark font-semibold text-canvas'
                    : fuera
                      ? 'text-muted/60'
                      : dia
                        ? 'font-semibold text-ink'
                        : 'text-muted'
                }`}
              >
                {numero}
              </span>
              {corte && (
                <span className="truncate text-[10px] font-semibold uppercase tracking-[0.08em] text-accent-dark">
                  Corte
                </span>
              )}
            </span>
          )

          if (!dia) {
            return (
              <div key={fecha} className={`flex min-h-0 flex-col overflow-hidden p-1.5 ${fondo}`}>
                {cabecera}
              </div>
            )
          }

          const { caja, sub } = tono(dia.centimos, maximo)
          return (
            <button
              key={fecha}
              onClick={() => onDia(fecha)}
              aria-haspopup="dialog"
              aria-expanded={activo}
              aria-label={`${numero} de ${nombreMes(mes)}: ${dia.pagos.length} factura${dia.pagos.length === 1 ? '' : 's'}, ${formatImporte(deCentimos(dia.centimos))}${corte ? ', día de corte' : ''}`}
              className={`group relative flex min-h-0 min-w-0 flex-col gap-1 overflow-hidden p-1.5 text-left transition-colors hover:bg-accent-soft focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent-dark/40 ${fondo} ${activo ? 'z-10 ring-2 ring-inset ring-accent-dark' : ''}`}
            >
              {cabecera}
              <span className={`mt-auto min-w-0 overflow-hidden rounded-md px-2 py-1 ${caja}`}>
                <span className="block truncate text-[13px] leading-4 font-semibold">
                  {formatNumber(dia.pagos.length)}
                  <span className="hidden font-normal sm:inline">
                    {' '}
                    {dia.pagos.length === 1 ? 'factura' : 'facturas'}
                  </span>
                </span>
                <span className={`mt-0.5 hidden truncate text-[11px] leading-4 whitespace-nowrap md:block ${sub}`}>
                  {formatImporte(deCentimos(dia.centimos))}
                </span>
              </span>
            </button>
          )
        })}
      </div>

      <footer className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2 pb-16 text-[12px] text-muted sm:pb-2 sm:pr-44">
        <span className="flex flex-wrap items-center gap-x-5 gap-y-1.5">
          <span className="flex items-center gap-2">
            <span aria-hidden className="inline-flex size-3.5 rounded-full bg-accent-dark" />
            Día de corte: las vencidas se ejecutarían ese día
          </span>
          <span className="flex items-center gap-1">
            {TONOS.map(({ caja }) => (
              <span key={caja} aria-hidden className={`size-3 rounded-sm ${caja}`} />
            ))}
            <span className="ml-1.5">más importe, más intenso</span>
          </span>
        </span>
        {/* Obligatorio: sin él, la demo promete transferencias reales. */}
        <span role="note" className="flex items-center gap-1.5">
          <Info aria-hidden className="size-3.5 shrink-0" />
          Borrador: los IBAN son sintéticos y no se ha hecho ninguna transferencia.
        </span>
      </footer>
    </section>
  )
}
