'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronRight, Search, X } from 'lucide-react'
import { formatDate, formatImporte, formatNumber, initials } from '@/lib/format'
import { ficheroHref } from '@/lib/routes'
import { useRowLink } from '@/hooks/useRowLink'
import { LETRA, aCentimos, deCentimos, type DiaPagos } from './CalendarioMes'

/** "2026-09-18" → "Viernes, 18 de septiembre de 2026" */
function fechaLarga(iso: string): string {
  const texto = new Date(`${iso}T00:00:00Z`).toLocaleDateString('es-ES', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })
  return texto.charAt(0).toLocaleUpperCase('es-ES') + texto.slice(1)
}

const COLUMNAS = 'grid grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)_132px] items-center gap-4 sm:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)_128px_140px_20px]'

function Dato({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted">{etiqueta}</span>
      <span className="text-[17px] font-semibold text-ink">{valor}</span>
    </div>
  )
}

/**
 * Las facturas que se ejecutan un día, en una ventana por delante del calendario (z-50: el chat flota a z-40).
 * Lista entera con scroll y buscador, sin paginar: el día de corte trae unas 430 y se recorren de un tirón.
 * Cierran el fondo, Escape y la X; cada fila abre el detalle del fichero.
 */
export function ListaDia({
  dia,
  fechaCorte,
  onCerrar,
}: {
  dia: DiaPagos
  fechaCorte: string | null
  onCerrar: () => void
}) {
  const rowLink = useRowLink()
  const buscarRef = useRef<HTMLInputElement>(null)
  const [texto, setTexto] = useState('')

  useEffect(() => {
    const anterior = document.activeElement as HTMLElement | null
    buscarRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCerrar()
    }
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('keydown', onKey)
      anterior?.focus?.()
    }
  }, [onCerrar])

  const pagos = useMemo(() => {
    const q = texto.trim().toLowerCase()
    if (!q) return dia.pagos
    return dia.pagos.filter((pago) =>
      `${pago.beneficiario} ${pago.proveedor_id} ${pago.referencia} ${pago.file_id}`.toLowerCase().includes(q),
    )
  }, [dia.pagos, texto])

  const vencidas = dia.pagos.filter((pago) => pago.vencido).length
  const centimosFiltrados = pagos.reduce((suma, pago) => suma + aCentimos(pago.importe_eur), 0)
  const corte = dia.fecha === fechaCorte
  const titulo = `pagos-dia-${dia.fecha}`

  return (
    <div
      style={LETRA}
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/45 p-3 backdrop-blur-[2px] animate-in fade-in duration-150 sm:p-6"
      onClick={onCerrar}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby={titulo}
        onClick={(event) => event.stopPropagation()}
        className="flex h-[min(88vh,920px)] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-surface shadow-[0_32px_80px_rgba(43,55,51,0.28)] ring-1 ring-black/5 animate-in fade-in zoom-in-95 duration-200"
      >
        <header className="shrink-0 border-b border-line-soft px-6 pt-5 pb-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[12px] font-medium uppercase tracking-[0.1em] text-accent">
                Pagos del día{corte && ' · día de corte'}
              </p>
              <h2 id={titulo} className="mt-1 text-[24px] font-semibold tracking-[-0.02em] text-ink">
                {fechaLarga(dia.fecha)}
              </h2>
            </div>
            <button
              onClick={onCerrar}
              aria-label="Cerrar"
              className="inline-flex size-9 shrink-0 items-center justify-center rounded-full text-ink-soft transition hover:bg-raised hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-dark/30"
            >
              <X className="size-5" />
            </button>
          </div>

          <div className="mt-4 flex flex-wrap items-end justify-between gap-x-10 gap-y-4">
            <div className="flex flex-wrap gap-x-10 gap-y-3">
              <Dato etiqueta="Facturas" valor={formatNumber(dia.pagos.length)} />
              <Dato etiqueta="Importe" valor={formatImporte(deCentimos(dia.centimos))} />
              <Dato etiqueta="Vencidas" valor={vencidas ? formatNumber(vencidas) : 'Ninguna'} />
            </div>
            <label className="relative w-full sm:w-[300px]">
              <span className="sr-only">Buscar en las facturas del día</span>
              <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted" />
              <input
                ref={buscarRef}
                value={texto}
                onChange={(event) => setTexto(event.target.value)}
                placeholder="Proveedor, factura o fichero"
                className="h-10 w-full rounded-xl border border-line bg-surface pr-3 pl-9 text-[14px] text-ink outline-none transition placeholder:text-muted focus:border-accent focus:bg-surface focus:ring-2 focus:ring-accent-dark/15"
              />
            </label>
          </div>
        </header>

        <div
          className={`${COLUMNAS} shrink-0 border-b border-line-soft bg-surface px-6 py-2.5 text-[11px] font-medium uppercase tracking-[0.08em] text-muted`}
        >
          <span>Proveedor</span>
          <span>Factura</span>
          <span className="hidden sm:block">Vencimiento</span>
          <span className="text-right">Importe</span>
          <span className="hidden sm:block" aria-hidden />
        </div>

        {pagos.length === 0 ? (
          <p className="flex flex-1 items-center justify-center p-10 text-[14px] text-muted">
            Ninguna factura de este día coincide con «{texto}».
          </p>
        ) : (
          <ul className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
            {pagos.map((pago) => (
              <li
                key={pago.file_id}
                {...rowLink(ficheroHref(pago.file_id))}
                aria-label={`Abrir ${pago.file_id}`}
                className={`${COLUMNAS} group cursor-pointer border-b border-line-soft px-6 py-3 transition-colors hover:bg-accent-soft focus-visible:bg-accent-soft focus-visible:outline-none`}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-raised text-[12px] font-semibold text-accent-dark">
                    {initials(pago.beneficiario)}
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-[14px] font-medium text-ink">{pago.beneficiario}</p>
                    <p className="truncate text-[12px] text-muted">{pago.proveedor_id}</p>
                  </div>
                </div>
                <div className="min-w-0">
                  <p className="truncate text-[14px] text-ink">{pago.referencia}</p>
                  <p className="truncate font-mono text-[12px] text-muted" title={pago.file_id}>
                    {pago.file_id}
                  </p>
                </div>
                <div className="hidden sm:block">
                  <p className="text-[14px] text-ink">{formatDate(pago.vencimiento)}</p>
                  <p className="text-[12px] text-muted">{pago.vencido ? 'Vencida' : 'En plazo'}</p>
                </div>
                <p className="text-right text-[15px] font-semibold text-ink">{formatImporte(pago.importe_eur)}</p>
                <ChevronRight
                  aria-hidden
                  className="hidden size-4 text-muted/60 transition group-hover:translate-x-0.5 group-hover:text-accent-dark sm:block"
                />
              </li>
            ))}
          </ul>
        )}

        <footer className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-line-soft bg-surface px-6 py-3 text-[12px] text-muted">
          <span>
            {texto
              ? `${formatNumber(pagos.length)} de ${formatNumber(dia.pagos.length)} facturas · ${formatImporte(deCentimos(centimosFiltrados))}`
              : 'Todas son decisiones PAGAR vigentes. Pulsa una fila para ver la factura.'}
          </span>
          <span>Borrador: no se ha hecho ninguna transferencia.</span>
        </footer>
      </section>
    </div>
  )
}
