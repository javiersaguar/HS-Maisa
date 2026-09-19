'use client'

import { useState } from 'react'
import { ChevronDown, Search, X } from 'lucide-react'
import type { EstadoFichero } from '@/lib/types'
import { ESTADOS_FICHERO } from '@/lib/format'
import { LOTE_BANDEJA } from '@/lib/api/inbox'
import { Card } from '@/components/ui/Card'
import { Select } from '@/components/ui/Select'
import { Spinner } from '@/components/ui/Spinner'

export interface FicheroFilters {
  q: string
  estado: EstadoFichero | 'all'
  /** Regla incumplida: "R1"…"R6". */
  regla: string | 'all'
  lote: number | 'all'
}

export const EMPTY_FILTERS: FicheroFilters = { q: '', estado: 'all', regla: 'all', lote: 'all' }

/** Reglas de la norma v3 (`rules/norma_v3.py`), para filtrar por la que falla. */
export const REGLAS: Array<{ value: string; label: string }> = [
  { value: 'R1', label: 'R1 · NIF e IBAN del maestro' },
  { value: 'R2', label: 'R2 · Pedido e importe' },
  { value: 'R3', label: 'R3 · IVA y total' },
  { value: 'R4', label: 'R4 · Fecha válida' },
  { value: 'R5', label: 'R5 · Asiento ERP pendiente' },
  { value: 'R6', label: 'R6 · Anomalías para humano' },
]

const labelClass = 'text-[11px] font-bold uppercase tracking-[0.12em] text-muted'

export function FilterBar({
  filters,
  onChange,
  onReset,
  matching,
  total,
  searching = false,
}: {
  filters: FicheroFilters
  onChange: (next: FicheroFilters) => void
  onReset: () => void
  matching: number | null
  total: number | null
  searching?: boolean
}) {
  const active =
    (filters.q ? 1 : 0) +
    (filters.estado !== 'all' ? 1 : 0) +
    (filters.regla !== 'all' ? 1 : 0) +
    (filters.lote !== 'all' ? 1 : 0)

  // Empieza plegado; si la URL ya trae filtros, abierto para que se vea qué se está filtrando.
  const [open, setOpen] = useState(active > 0)

  const set = <K extends keyof FicheroFilters>(key: K, value: FicheroFilters[K]) =>
    onChange({ ...filters, [key]: value })

  return (
    <Card className="mt-4 overflow-hidden rounded-2xl border-line shadow-[0_8px_28px_rgba(43,55,51,0.05)]">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls="filtros-ficheros"
        className={`flex w-full cursor-pointer items-center justify-between gap-3 bg-surface px-5 py-3 text-left transition hover:bg-raised ${open ? 'border-b border-line-soft' : ''}`}
      >
        <span className="flex min-w-0 items-center gap-2 text-[15px] font-semibold text-ink">
          <ChevronDown className={`size-4 shrink-0 transition-transform duration-200 ${open ? '' : '-rotate-90'}`} />
          Filtros
          {active > 0 && (
            <span className="rounded-full bg-accent-dark px-2 py-0.5 text-[11px] font-bold text-canvas tabular-nums">
              {active}
            </span>
          )}
        </span>
        {matching !== null && (
          <span className="shrink-0 rounded-full bg-accent-soft px-3 py-1 text-[13px] font-semibold text-accent-dark tabular-nums">
            {matching} coinciden
          </span>
        )}
      </button>
      {open && (
        <div id="filtros-ficheros" className="p-5 animate-in fade-in slide-in-from-top-1 duration-150">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
            <input
              value={filters.q}
              onChange={(event) => set('q', event.target.value)}
              placeholder="Buscar por file_id, proveedor, nº de factura, pedido o NIF…"
              aria-label="Buscar ficheros"
              onKeyDown={(event) => {
                if (event.key === 'Escape') set('q', '')
              }}
              className="h-11 w-full rounded-xl border border-line bg-surface pl-10 pr-20 text-[14px] outline-none transition placeholder:text-muted focus:border-accent focus:ring-4 focus:ring-line-soft"
            />
            <span className="absolute right-3 top-1/2 flex -translate-y-1/2 items-center gap-2 text-muted">
              {searching && <Spinner className="size-4" />}
              {filters.q && (
                <button
                  onClick={() => set('q', '')}
                  aria-label="Borrar búsqueda"
                  className="flex size-6 min-h-0 items-center justify-center rounded-md transition hover:bg-accent-soft hover:text-accent-dark animate-in fade-in zoom-in-90 duration-150"
                >
                  <X className="size-3.5" />
                </button>
              )}
            </span>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className={labelClass}>
              Resultado
              <Select
                aria-label="Filtrar por resultado"
                value={filters.estado}
                onChange={(estado) => set('estado', estado)}
                radius="xl"
                className="mt-1.5 h-10 py-0"
                options={[
                  { value: 'all' as const, label: 'Todos los resultados' },
                  ...ESTADOS_FICHERO.map((estado) => ({ value: estado, label: estado })),
                ]}
              />
            </div>
            <div className={labelClass}>
              Regla incumplida
              <Select
                aria-label="Filtrar por regla incumplida"
                value={filters.regla}
                onChange={(regla) => set('regla', regla)}
                radius="xl"
                className="mt-1.5 h-10 py-0"
                options={[{ value: 'all', label: 'Cualquier regla' }, ...REGLAS]}
              />
            </div>
            <div className={labelClass}>
              Lote
              <Select
                aria-label="Filtrar por lote"
                value={String(filters.lote)}
                onChange={(lote) => set('lote', lote === 'all' ? 'all' : Number(lote))}
                radius="xl"
                className="mt-1.5 h-10 py-0"
                options={[
                  { value: 'all', label: 'Todos los lotes' },
                  { value: '1', label: 'Lote 1 · Caja' },
                  { value: '2', label: 'Lote 2' },
                  { value: String(LOTE_BANDEJA), label: `Lote ${LOTE_BANDEJA} · Bandeja` },
                ]}
              />
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between border-t border-line-soft pt-4 text-[13px]">
            <span className="font-medium text-ink-soft">
              {matching !== null && total !== null ? (
                <>
                  Mostrando <strong className="text-ink">{matching}</strong> de {total} ficheros
                </>
              ) : (
                'Cargando ficheros…'
              )}
            </span>
            <button
              onClick={onReset}
              disabled={active === 0}
              className="rounded-lg px-3 py-1.5 font-semibold text-accent-dark transition hover:bg-accent-soft disabled:opacity-40 disabled:hover:bg-transparent"
            >
              Quitar filtros{active > 0 ? ` (${active})` : ''}
            </button>
          </div>
        </div>
      )}
    </Card>
  )
}
