'use client'

import { useState } from 'react'
import Link from 'next/link'
import type { Calendario } from '@/lib/types'
import type { ApiError } from '@/lib/api/client'
import { formatDate, formatImporte, formatNumber, formatSemana, loteNombre } from '@/lib/format'
import { ficheroHref } from '@/lib/routes'
import { Card } from '@/components/ui/Card'
import { Select } from '@/components/ui/Select'
import { Spinner } from '@/components/ui/Spinner'
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states'
import { ConfianzaBadge } from '@/components/confianza/ConfianzaBadge'

const PAGE_SIZE = 15

export interface FiltrosPagos {
  semana: string | null
  proveedor: string | null
  lote: number | null
  vencido: boolean | null
}

export const SIN_FILTROS: FiltrosPagos = { semana: null, proveedor: null, lote: null, vencido: null }

/** Mod-97 fallido: los IBAN de la Caja son sintéticos. Un banco los rechazaría. */
export function IbanSinControl() {
  return (
    <span
      title="No pasa el dígito de control (mod-97). Un banco lo rechazaría."
      className="inline-flex items-center rounded-full border border-[#f1dada] bg-[#fff0f0] px-2 py-0.5 text-[11px] font-semibold text-[#bd3434]"
    >
      sin control
    </span>
  )
}

/**
 * Los pagos del calendario con los filtros de la página (la API filtra; aquí sólo se pagina). Cada
 * `file_id` abre el detalle con su traza.
 */
export function ListaPagos({
  calendario,
  error,
  loading,
  onRetry,
  filtros,
  onFiltros,
  semanas,
  lotes,
  proveedorNombre,
  conConfianza,
}: {
  calendario: Calendario | null
  error: ApiError | null
  loading: boolean
  onRetry: () => void
  filtros: FiltrosPagos
  onFiltros: (next: FiltrosPagos) => void
  semanas: string[]
  lotes: number[]
  proveedorNombre: string | null
  /** Sólo si K3 responde: el calendario llega con `con_confianza=true` y cada pago trae su ficha o null. */
  conConfianza: boolean
}) {
  const [page, setPage] = useState(1)
  const [clave, setClave] = useState(calendario)
  if (calendario !== clave) {
    // Nuevos filtros → primera página.
    setClave(calendario)
    setPage(1)
  }

  const pagos = calendario?.pagos ?? []
  const pageCount = Math.max(1, Math.ceil(pagos.length / PAGE_SIZE))
  const visibles = pagos.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  const hayFiltros = Object.values(filtros).some((value) => value !== null)

  const pagerButton =
    'inline-flex items-center gap-1.5 rounded-lg border border-[#d5e2da] bg-white px-3 py-1.5 font-semibold text-[#315d53] transition hover:bg-[#edf8f3] disabled:border-[#e5eae6] disabled:bg-transparent disabled:font-normal disabled:text-[#b2bbb5]'

  return (
    <Card className="mt-6 overflow-hidden rounded-2xl border-[#e1e7e2] shadow-[0_8px_28px_rgba(20,55,45,0.045)]">
      <div className="flex flex-col gap-4 px-5 pt-5 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-[22px] font-semibold tracking-[-0.025em]">Pagos</h2>
          <p className="mt-1 text-[13px] text-[#8a958e]">
            {calendario ? `${formatNumber(calendario.total)} facturas` : 'Cargando…'}
            {proveedorNombre && ` de ${proveedorNombre}`}
            {filtros.semana && ` · ${formatSemana(filtros.semana)}`}
            {calendario && calendario.mostrados < calendario.total && ` · se muestran ${formatNumber(calendario.mostrados)}`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Select
            aria-label="Semana"
            className="w-40"
            value={filtros.semana ?? 'all'}
            onChange={(value) => onFiltros({ ...filtros, semana: value === 'all' ? null : value })}
            options={[{ value: 'all', label: 'Todas las semanas' }, ...semanas.map((s) => ({ value: s, label: `${formatSemana(s)} (${s.slice(0, 4)})` }))]}
          />
          <Select
            aria-label="Lote"
            className="w-44"
            value={filtros.lote === null ? 'all' : String(filtros.lote)}
            onChange={(value) => onFiltros({ ...filtros, lote: value === 'all' ? null : Number(value) })}
            options={[{ value: 'all', label: 'Todos los lotes' }, ...lotes.map((l) => ({ value: String(l), label: `Lote ${l} · ${loteNombre(l)}` }))]}
          />
          <Select
            aria-label="Vencimiento"
            className="w-36"
            value={filtros.vencido === null ? 'all' : filtros.vencido ? 'si' : 'no'}
            onChange={(value) => onFiltros({ ...filtros, vencido: value === 'all' ? null : value === 'si' })}
            options={[
              { value: 'all', label: 'Todas' },
              { value: 'si', label: 'Vencidas' },
              { value: 'no', label: 'En plazo' },
            ]}
          />
          {hayFiltros && (
            <button onClick={() => onFiltros(SIN_FILTROS)} className="px-2 text-[13px] font-semibold text-[#315d53] underline">
              Quitar filtros
            </button>
          )}
        </div>
      </div>

      {error && !calendario ? (
        <ErrorState error={error} onRetry={onRetry} retrying={loading} />
      ) : !calendario ? (
        <LoadingState label="Cargando pagos" rows={6} />
      ) : pagos.length === 0 ? (
        <EmptyState
          title="Ningún pago con estos filtros"
          description="Prueba otra semana, otro lote o quita el proveedor."
          action={
            <button
              onClick={() => onFiltros(SIN_FILTROS)}
              className="rounded-lg border border-[#d5e0d9] bg-white px-4 py-2 text-[14px] font-semibold text-[#315d53] transition hover:bg-[#eff8f3]"
            >
              Quitar filtros
            </button>
          }
        />
      ) : (
        <div aria-busy={loading} className={`mt-4 overflow-x-auto transition-opacity ${loading ? 'opacity-60' : ''}`}>
          <table className="w-full min-w-[1080px] text-left text-[14px]">
            <thead>
              <tr className="border-y border-[#e8ece9] bg-[#fbfcfb] text-[11px] font-bold uppercase tracking-[0.1em] text-[#78867e]">
                <th className="px-5 py-3">file_id</th>
                <th className="px-3 py-3">Beneficiario</th>
                <th className="px-3 py-3 text-right">Importe</th>
                <th className="px-3 py-3">Vence</th>
                <th className="px-3 py-3">Se ejecuta</th>
                <th className="px-3 py-3">IBAN</th>
                {conConfianza && <th className="px-3 py-3">Confianza</th>}
                <th className="px-5 py-3">Lote</th>
              </tr>
            </thead>
            <tbody>
              {visibles.map((pago) => {
                return (
                  <tr key={pago.file_id} className="border-b border-[#edf0ec] last:border-b-0 hover:bg-[#f5fbf8]">
                    <td className="max-w-[240px] px-5 py-3">
                      <Link
                        href={ficheroHref(pago.file_id)}
                        className="block truncate font-mono text-[13px] font-bold text-[#17211e] hover:text-[#176d59] hover:underline"
                        title={`Abrir la traza de ${pago.file_id}`}
                      >
                        {pago.file_id}
                      </Link>
                      <span className="text-[12px] text-[#94a099]">{pago.referencia}</span>
                    </td>
                    <td className="px-3 py-3">
                      <p className="font-semibold text-[#203b31]">{pago.beneficiario}</p>
                      <p className="font-mono text-[12px] text-[#94a099]">{pago.proveedor_id}</p>
                    </td>
                    <td className="px-3 py-3 text-right font-semibold tabular-nums whitespace-nowrap text-[#203b31]">
                      {formatImporte(pago.importe_eur)}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <span className={pago.vencido ? 'font-semibold text-[#bd3434]' : 'text-[#52605a]'}>
                        {formatDate(pago.vencimiento)}
                      </span>
                      {pago.vencido && <span className="ml-1.5 text-[11px] font-semibold uppercase text-[#bd3434]">vencida</span>}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap text-[#52605a]">
                      {formatDate(pago.fecha_ejecucion)}
                      <span className="ml-1.5 text-[12px] text-[#94a099]">{formatSemana(pago.semana)}</span>
                    </td>
                    <td className="px-3 py-3">
                      <span className="block font-mono text-[12px] text-[#52605a]">{pago.iban}</span>
                      {pago.iban_control_ok === false && <IbanSinControl />}
                    </td>
                    {conConfianza && (
                      <td className="px-3 py-3">
                        {pago.confianza ? (
                          <ConfianzaBadge
                            puntuacion={pago.confianza.puntuacion}
                            banda={pago.confianza.banda}
                            title={pago.confianza.razones[0]}
                          />
                        ) : (
                          <span className="text-[#9aa39e]">—</span>
                        )}
                      </td>
                    )}
                    <td className="px-5 py-3 text-[#687970]">{pago.lote}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      {calendario && pagos.length > PAGE_SIZE && (
        <div className="flex items-center justify-between border-t border-[#edf0ec] px-5 py-3 text-[13px] text-[#819088]">
          <span className="flex items-center gap-2">
            {loading && <Spinner className="size-3 text-[#315d53]" />}
            Mostrando {(page - 1) * PAGE_SIZE + 1}–{(page - 1) * PAGE_SIZE + visibles.length} de {formatNumber(pagos.length)}
          </span>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page <= 1} className={pagerButton}>
              Anterior
            </button>
            <span className="rounded-lg border border-[#d5e2da] bg-white px-3 py-1.5 font-semibold text-[#315d53] tabular-nums">
              {page} / {pageCount}
            </span>
            <button onClick={() => setPage(Math.min(pageCount, page + 1))} disabled={page >= pageCount} className={pagerButton}>
              Siguiente
            </button>
          </div>
        </div>
      )}
    </Card>
  )
}
