'use client'

import { Search, X } from 'lucide-react'
import type { EstadoFichero } from '@/lib/types'
import { ESTADOS_FICHERO } from '@/lib/format'
import { LOTE_BANDEJA } from '@/lib/api/inbox'
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

/** Una sola fila compacta: sin tarjeta que la envuelva y sin títulos que repitan lo evidente. */
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

  const set = <K extends keyof FicheroFilters>(key: K, value: FicheroFilters[K]) =>
    onChange({ ...filters, [key]: value })

  return (
    <div className="mt-5 flex flex-wrap items-center gap-2">
      <div className="relative min-w-[240px] flex-1">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-faint" />
        <input
          value={filters.q}
          onChange={(event) => set('q', event.target.value)}
          placeholder="Buscar por file_id, proveedor, nº de factura, pedido o NIF…"
          aria-label="Buscar ficheros"
          onKeyDown={(event) => {
            if (event.key === 'Escape') set('q', '')
          }}
          className="h-9 w-full border border-line bg-surface pl-8 pr-16 text-[13px] outline-none transition placeholder:text-faint focus:border-accent"
        />
        <span className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1.5 text-faint">
          {searching && <Spinner className="size-3.5" />}
          {filters.q && (
            <button
              onClick={() => set('q', '')}
              aria-label="Borrar búsqueda"
              className="flex size-5 min-h-0 items-center justify-center transition hover:text-ink"
            >
              <X className="size-3.5" />
            </button>
          )}
        </span>
      </div>

      <Select
        aria-label="Filtrar por resultado"
        value={filters.estado}
        onChange={(estado) => set('estado', estado)}
        className="w-[170px]"
        options={[
          { value: 'all' as const, label: 'Todos los resultados' },
          ...ESTADOS_FICHERO.map((estado) => ({ value: estado, label: estado })),
        ]}
      />
      <Select
        aria-label="Filtrar por regla incumplida"
        value={filters.regla}
        onChange={(regla) => set('regla', regla)}
        className="w-[210px]"
        options={[{ value: 'all', label: 'Cualquier regla' }, ...REGLAS]}
      />
      <Select
        aria-label="Filtrar por lote"
        value={String(filters.lote)}
        onChange={(lote) => set('lote', lote === 'all' ? 'all' : Number(lote))}
        className="w-[150px]"
        options={[
          { value: 'all', label: 'Todos los lotes' },
          { value: '1', label: 'Lote 1 · Caja' },
          { value: '2', label: 'Lote 2' },
          { value: String(LOTE_BANDEJA), label: `Lote ${LOTE_BANDEJA} · Bandeja` },
        ]}
      />

      {active > 0 && (
        <button
          onClick={onReset}
          className="h-9 px-2 text-[13px] text-muted transition hover:text-ink"
        >
          Quitar filtros ({active})
        </button>
      )}

      <span className="ml-auto text-[13px] text-muted cifra">
        {matching !== null && total !== null ? `${matching} de ${total} coinciden` : 'Cargando…'}
      </span>
    </div>
  )
}
