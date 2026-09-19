'use client'

import { Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import type { EstadoFichero, Fichero } from '@/lib/types'
import { DEFAULT_PAGE_SIZE, fetchFicheros } from '@/lib/api/ficheros'
import { toApiError } from '@/lib/api/client'
import { LOTE_BANDEJA } from '@/lib/api/inbox'
import { BRAND } from '@/lib/config'
import { downloadCsv } from '@/lib/csv'
import { ESTADOS_FICHERO, formatNumber, motivoPrincipal } from '@/lib/format'
import { useFicheros } from '@/hooks/useFicheros'
import { usePanel } from '@/hooks/usePanel'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { EMPTY_FILTERS, FilterBar, REGLAS, type FicheroFilters } from '@/components/invoices/FilterBar'
import { InvoiceTable } from '@/components/invoices/InvoiceTable'
import { Card } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { EmptyState, ErrorState, LoadingState, Skeleton } from '@/components/ui/states'
import { Toast } from '@/components/ui/Toast'

/** Mismas columnas que una línea de outcomes.jsonl: file_id, result y la traza permitida. */
function exportRows(fileName: string, ficheros: Fichero[]) {
  downloadCsv(
    fileName,
    ['file_id', 'result', 'motivo', 'norma_version', 'regla', 'lote'],
    ficheros.map((fichero) => {
      const fallo = fichero.decision?.motivos.find((motivo) => !motivo.ok)
      return [
        fichero.file_id,
        fichero.estado,
        fichero.decision ? motivoPrincipal(fichero) : '',
        fichero.decision?.norma_version ?? '',
        fallo?.regla_id ?? '',
        fichero.lote,
      ]
    }),
  )
}

/** Los filtros viven en la URL: al volver de un fichero se recupera la misma cola. */
function readUrl(params: URLSearchParams): { filters: FicheroFilters; page: number } {
  const estado = params.get('estado')
  const regla = params.get('regla')
  const lote = Number(params.get('lote'))
  const page = Number(params.get('page'))
  return {
    filters: {
      q: params.get('q') ?? '',
      estado: ESTADOS_FICHERO.includes(estado as EstadoFichero) ? (estado as EstadoFichero) : 'all',
      regla: REGLAS.some((item) => item.value === regla) ? (regla as string) : 'all',
      lote: lote === 1 || lote === 2 || lote === LOTE_BANDEJA ? lote : 'all',
    },
    page: Number.isInteger(page) && page > 1 ? page : 1,
  }
}

function writeUrl(filters: FicheroFilters, page: number): string {
  const params = new URLSearchParams()
  if (filters.q) params.set('q', filters.q)
  if (filters.estado !== 'all') params.set('estado', filters.estado)
  if (filters.regla !== 'all') params.set('regla', filters.regla)
  if (filters.lote !== 'all') params.set('lote', String(filters.lote))
  if (page > 1) params.set('page', String(page))
  const query = params.toString()
  return query ? `?${query}` : ''
}

function FicherosScreen() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [initial] = useState(() => readUrl(searchParams))
  const [filters, setFilters] = useState<FicheroFilters>(initial.filters)
  const [page, setPage] = useState(initial.page)
  const [selected, setSelected] = useState<Record<string, Fichero>>({})
  const [exporting, setExporting] = useState(false)
  const [toast, setToast] = useState<{ message: string; tone: 'success' | 'error' } | null>(null)
  const dismissToast = useCallback(() => setToast(null), [])
  const tableRef = useRef<HTMLDivElement>(null)

  const q = useDebouncedValue(filters.q)
  const query = {
    q,
    estado: filters.estado,
    regla: filters.regla,
    lote: filters.lote,
    page,
    pageSize: DEFAULT_PAGE_SIZE,
  }
  const { data, error, loading, refresh } = useFicheros(query)
  const { data: summary, error: summaryError } = usePanel()
  const searching = loading || q !== filters.q

  useEffect(() => {
    router.replace(`${pathname}${writeUrl({ ...filters, q }, page)}`, { scroll: false })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, filters.estado, filters.regla, filters.lote, page])

  const ficheros = data?.items ?? []
  const pageCount = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1
  const selectedIds = Object.keys(selected)

  const changeFilters = (next: FicheroFilters) => {
    setFilters(next)
    setPage(1)
  }

  const goToPage = (next: number) => {
    setPage(next)
    tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const toggle = (id: string) =>
    setSelected((current) => {
      const next = { ...current }
      if (next[id]) delete next[id]
      else {
        const fichero = ficheros.find((item) => item.file_id === id)
        if (fichero) next[id] = fichero
      }
      return next
    })

  const toggleAll = () =>
    setSelected((current) => {
      const next = { ...current }
      const allOn = ficheros.every((fichero) => next[fichero.file_id])
      ficheros.forEach((fichero) => {
        if (allOn) delete next[fichero.file_id]
        else next[fichero.file_id] = fichero
      })
      return next
    })

  /** Exporta la selección si la hay; si no, todos los ficheros que cumplen los filtros. */
  const exportFicheros = async () => {
    if (selectedIds.length) {
      exportRows('albertitos-seleccion.csv', Object.values(selected))
      setToast({ message: `${selectedIds.length} ficheros exportados a CSV`, tone: 'success' })
      return
    }
    if (!data) return
    setExporting(true)
    try {
      const all = await fetchFicheros({ ...query, page: 1, pageSize: Math.max(data.total, 1) })
      exportRows('albertitos-ficheros.csv', all.items)
      setToast({ message: `${all.items.length} ficheros exportados a CSV`, tone: 'success' })
    } catch (caught) {
      setToast({ message: `No se pudo exportar: ${toApiError(caught).message}`, tone: 'error' })
    } finally {
      setExporting(false)
    }
  }

  const pagerButton =
    'inline-flex h-8 items-center gap-1.5 rounded-[var(--radius-ui)] border border-line bg-surface px-2.5 text-ink transition hover:border-faint disabled:text-faint disabled:hover:border-line'

  return (
    <div className="px-6 py-6">
      <title>{`Ficheros · ${BRAND}`}</title>
      <div className="mx-auto max-w-[1380px]">
        <header className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-[22px] font-semibold tracking-[-0.02em]">Ficheros</h1>
            {summary ? (
              <p className="mt-1 text-[13px] text-muted cifra">
                {formatNumber(summary.ficheros)} ficheros
                {' · '}
                <button
                  onClick={() => changeFilters({ ...EMPTY_FILTERS, estado: 'ESCALAR' })}
                  aria-pressed={filters.estado === 'ESCALAR'}
                  className={`min-h-0 underline-offset-2 hover:underline ${summary.porEstado.ESCALAR > 0 ? 'text-warn' : ''}`}
                >
                  {formatNumber(summary.porEstado.ESCALAR)} escalados
                </button>
                {summary.porEstado.PENDIENTE > 0 && (
                  <>
                    {' · '}
                    <button
                      onClick={() => changeFilters({ ...EMPTY_FILTERS, estado: 'PENDIENTE' })}
                      aria-pressed={filters.estado === 'PENDIENTE'}
                      className="min-h-0 underline-offset-2 hover:underline"
                    >
                      {formatNumber(summary.porEstado.PENDIENTE)} pendiente
                      {summary.porEstado.PENDIENTE === 1 ? '' : 's'}
                    </button>
                  </>
                )}
              </p>
            ) : summaryError ? null : (
              <Skeleton className="mt-1 h-4 w-56" />
            )}
          </div>
          <button
            onClick={exportFicheros}
            disabled={exporting || (!data?.total && !selectedIds.length)}
            className="inline-flex h-9 shrink-0 items-center gap-2 rounded-[var(--radius-ui)] border border-line bg-surface px-3 text-[13px] transition hover:border-faint disabled:opacity-50"
          >
            {exporting && <Spinner />}
            {exporting ? 'Exportando…' : selectedIds.length ? `Exportar ${selectedIds.length} seleccionados` : 'Exportar CSV'}
          </button>
        </header>

        <FilterBar
          filters={filters}
          onChange={changeFilters}
          onReset={() => changeFilters(EMPTY_FILTERS)}
          matching={data ? data.total : null}
          total={summary ? summary.ficheros : null}
          searching={searching}
        />

        <div ref={tableRef} className="scroll-mt-4">
          <Card className="mt-4 overflow-hidden">
            {error ? (
              <ErrorState error={error} onRetry={refresh} retrying={loading} />
            ) : !data ? (
              <LoadingState label="Cargando ficheros" rows={6} />
            ) : ficheros.length === 0 ? (
              <EmptyState
                title="Ningún fichero cumple estos filtros"
                description="Prueba otra búsqueda o quita los filtros."
                action={
                  <button
                    onClick={() => changeFilters(EMPTY_FILTERS)}
                    className="h-9 rounded-[var(--radius-ui)] border border-line bg-surface px-3 text-[13px] transition hover:border-faint"
                  >
                    Quitar filtros
                  </button>
                }
              />
            ) : (
              <div aria-busy={loading} className={`transition-opacity duration-200 ${loading ? 'opacity-60' : ''}`}>
                <InvoiceTable ficheros={ficheros} selected={selectedIds} onToggle={toggle} onToggleAll={toggleAll} />
              </div>
            )}
            {data && data.total > 0 && (
              <div className="flex items-center justify-between border-t border-line px-3 py-2 text-[13px] text-muted">
                <span className="flex items-center gap-2">
                  {loading && <Spinner className="size-3" />}
                  Mostrando {(data.page - 1) * data.pageSize + 1}–{(data.page - 1) * data.pageSize + ficheros.length} de{' '}
                  {data.total} ficheros
                </span>
                <div className="flex items-center gap-1">
                  <button onClick={() => goToPage(Math.max(1, page - 1))} disabled={page <= 1 || loading} className={pagerButton}>
                    Anterior
                  </button>
                  <span className="rounded-lg border border-[#d5e2da] bg-white px-3 py-1.5 font-semibold text-[#315d53] tabular-nums">
                    {page} / {pageCount}
                  </span>
                  <button
                    onClick={() => goToPage(Math.min(pageCount, page + 1))}
                    disabled={page >= pageCount || loading}
                    className={pagerButton}
                  >
                    Siguiente
                  </button>
                </div>
              </div>
            )}
          </Card>
        </div>

        {selectedIds.length > 0 && (
          <div className="sticky bottom-4 mt-6 flex items-center justify-between gap-3 rounded-xl border border-[#68d4ad] bg-[#e2f8ee] px-5 py-3 text-[14px] font-semibold shadow-[0_10px_24px_rgba(20,75,60,0.12)] animate-in fade-in slide-in-from-bottom-2 duration-200">
            {selectedIds.length} fichero{selectedIds.length === 1 ? '' : 's'} seleccionado{selectedIds.length === 1 ? '' : 's'}
            <span className="flex items-center gap-3">
              <button
                onClick={exportFicheros}
                className="rounded-lg bg-[#164f45] px-3 py-1.5 text-[13px] font-semibold text-white transition hover:bg-[#0d4037]"
              >
                Exportar selección
              </button>
              <button onClick={() => setSelected({})} className="text-[13px] font-semibold text-[#315d53] underline">
                Quitar selección
              </button>
            </span>
          </div>
        )}
      </div>
      {toast && <Toast message={toast.message} tone={toast.tone} onDismiss={dismissToast} />}
    </div>
  )
}

export default function FicherosPage() {
  return (
    <Suspense fallback={<LoadingState label="Cargando ficheros" rows={6} />}>
      <FicherosScreen />
    </Suspense>
  )
}
