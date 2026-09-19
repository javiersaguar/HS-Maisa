'use client'

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
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
import { useAsync } from '@/hooks/useAsync'
import { useConfianzaDisponible, useConfianzaFicheros, useConfianzaMap } from '@/hooks/useConfianza'
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
function readUrl(params: URLSearchParams): { filters: FicheroFilters; page: number; revisar: boolean } {
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
    revisar: params.get('revisar') === '1',
  }
}

function writeUrl(filters: FicheroFilters, page: number, revisar: boolean): string {
  const params = new URLSearchParams()
  if (revisar) params.set('revisar', '1')
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
  /** «Revisar primero»: las de banda baja de K3, de menor a mayor confianza, sin paginar. */
  const [revisar, setRevisar] = useState(initial.revisar)
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
  const { data: confianza } = useConfianzaMap()
  const { data: resumenConfianza, disponible } = useConfianzaDisponible()
  const porRevisar = resumenConfianza?.bandas.baja ?? 0
  const revisando = revisar && disponible !== false

  // Las de banda baja vienen ya ordenadas; se cruzan con todos los ficheros para tener proveedor y total.
  // No se usa la paginación normal: las 13 no caben en la página 1 de la cola completa.
  const baja = useConfianzaFicheros({ banda: 'baja', limite: 1000 }, revisando)
  const todos = useAsync(useCallback(() => fetchFicheros({ page: 1, pageSize: 1000 }), []), [], { enabled: revisando })
  const revisarItems = useMemo(() => {
    if (!baja.data || !todos.data) return null
    const porId = new Map(todos.data.items.map((fichero) => [fichero.file_id, fichero]))
    return baja.data.items.flatMap((item) => porId.get(item.file_id.normalize('NFC')) ?? [])
  }, [baja.data, todos.data])

  const searching = loading || q !== filters.q

  useEffect(() => {
    router.replace(`${pathname}${writeUrl({ ...filters, q }, page, revisando)}`, { scroll: false })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, filters.estado, filters.regla, filters.lote, page, revisando])

  const ficheros = (revisando ? revisarItems : data?.items) ?? []
  const pageCount = data ? Math.max(1, Math.ceil(data.total / data.pageSize)) : 1
  const selectedIds = Object.keys(selected)

  const changeFilters = (next: FicheroFilters) => {
    setFilters(next)
    setPage(1)
    setRevisar(false)
  }

  const toggleRevisar = () => {
    setRevisar((current) => !current)
    setFilters(EMPTY_FILTERS)
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
    if (revisando) {
      exportRows('albertitos-revisar-primero.csv', ficheros)
      setToast({ message: `${ficheros.length} ficheros exportados a CSV`, tone: 'success' })
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

  /** Un chip por resultado: tono del badge, con cantidad. Pinchar filtra; pinchar el activo quita el filtro. */
  const CHIP_TONE: Record<EstadoFichero, { on: string; off: string }> = {
    PAGAR: { on: 'border-ok bg-ok-soft text-ok', off: 'border-line bg-surface text-ok hover:bg-ok-soft' },
    ESCALAR: { on: 'border-warn bg-warn-soft text-warn', off: 'border-warn-line bg-surface text-warn hover:bg-warn-soft' },
    NO_PAGAR: { on: 'border-bad bg-bad-soft text-bad', off: 'border-bad-line bg-surface text-bad hover:bg-bad-soft' },
    PENDIENTE: { on: 'border-ink-soft bg-raised text-ink-soft', off: 'border-line bg-canvas text-ink-soft hover:bg-raised' },
  }

  const pagerButton =
    'inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface px-3 py-1.5 font-semibold text-accent-dark transition hover:bg-accent-soft disabled:border-line disabled:bg-transparent disabled:font-normal disabled:text-muted'

  return (
    <div className="px-5 py-6 sm:px-8">
      <title>{`Ficheros · ${BRAND}`}</title>
      <div className="mx-auto max-w-[1380px]">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-x-7 gap-y-3">
            <h1 className="text-[32px] font-semibold tracking-[-0.04em]">Ficheros</h1>
            {summary ? (
              <div className="flex flex-wrap items-center gap-2 text-[13px] font-semibold tabular-nums animate-in fade-in duration-300">
                <span className="rounded-full border border-line bg-surface px-3 py-1 text-ink-soft">
                  {formatNumber(summary.ficheros)} ficheros
                </span>
                <button
                  onClick={() => changeFilters({ ...EMPTY_FILTERS, estado: 'ESCALAR' })}
                  aria-pressed={filters.estado === 'ESCALAR'}
                  className={`rounded-full border px-3 py-1 text-warn transition hover:bg-warn-soft ${filters.estado === 'ESCALAR' ? 'border-warn bg-warn-soft' : 'border-warn-line bg-surface'}`}
                >
                  {formatNumber(summary.porEstado.ESCALAR)} escalados
                </button>
                {disponible && porRevisar > 0 && (
                  <button
                    onClick={toggleRevisar}
                    aria-pressed={revisando}
                    title="Se escalan sólo porque no se leyeron con seguridad: si el original está limpio, lo correcto sería PAGAR."
                    className={`rounded-full border px-3 py-1 text-bad transition hover:bg-bad-soft ${revisando ? 'border-bad bg-bad-soft' : 'border-bad-line bg-surface'}`}
                  >
                    Revisar primero · {formatNumber(porRevisar)}
                  </button>
                )}
                {summary.porEstado.PENDIENTE > 0 && (
                  <button
                    onClick={() => changeFilters({ ...EMPTY_FILTERS, estado: 'PENDIENTE' })}
                    aria-pressed={filters.estado === 'PENDIENTE'}
                    className={`rounded-full border px-3 py-1 text-ink-soft transition hover:bg-raised ${filters.estado === 'PENDIENTE' ? 'border-line bg-raised' : 'border-line bg-canvas'}`}
                  >
                    {formatNumber(summary.porEstado.PENDIENTE)} pendiente{summary.porEstado.PENDIENTE === 1 ? '' : 's'}
                  </button>
                )}
              </div>
            ) : summaryError ? null : (
              <Skeleton className="h-6 w-64" />
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={exportFicheros}
              disabled={exporting || (!data?.total && !selectedIds.length)}
              className="inline-flex items-center gap-2 rounded-lg border border-line bg-surface px-4 py-2 text-[14px] font-semibold transition hover:bg-accent-soft disabled:opacity-50"
            >
              {exporting && <Spinner />}
              {exporting ? 'Exportando…' : selectedIds.length ? `Exportar ${selectedIds.length} seleccionados` : 'Exportar CSV'}
            </button>
          </div>
        </header>

        {summary && (
          <div role="group" aria-label="Filtrar por resultado" className="mt-5 flex flex-wrap gap-2 animate-in fade-in duration-300">
            {ESTADOS_FICHERO.map((estado) => {
              const activo = !revisando && filters.estado === estado
              return (
                <button
                  key={estado}
                  onClick={() => changeFilters({ ...filters, estado: activo ? 'all' : estado })}
                  aria-pressed={activo}
                  className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[13px] font-semibold transition ${CHIP_TONE[estado][activo ? 'on' : 'off']}`}
                >
                  {estado}
                  <span className="tabular-nums opacity-80">{formatNumber(summary.porEstado[estado])}</span>
                </button>
              )
            })}
          </div>
        )}

        <FilterBar
          filters={filters}
          onChange={changeFilters}
          onReset={() => changeFilters(EMPTY_FILTERS)}
          matching={revisando ? (revisarItems?.length ?? null) : data ? data.total : null}
          total={summary ? summary.ficheros : null}
          searching={searching}
        />

        <div ref={tableRef} className="scroll-mt-4">
          <Card className="mt-7 overflow-hidden rounded-2xl border-line shadow-[0_8px_28px_rgba(43,55,51,0.045)]">
            {revisando && (
              <p className="border-b border-bad-line bg-bad-soft px-5 py-3 text-[13px] text-bad">
                <strong>Revisar primero:</strong> se escalan sólo porque no se leyeron con seguridad. De menor a mayor
                confianza en la clasificación (no es probabilidad de pago).{' '}
                <button onClick={toggleRevisar} className="font-semibold underline">
                  Volver a la cola
                </button>
              </p>
            )}
            {revisando ? (
              todos.error ? (
                <ErrorState error={todos.error} onRetry={todos.refresh} retrying={todos.loading} />
              ) : !revisarItems ? (
                <LoadingState label="Cargando las de confianza baja" rows={6} />
              ) : ficheros.length === 0 ? (
                <EmptyState title="Nada que revisar primero" description="Ninguna factura tiene confianza baja." />
              ) : (
                <InvoiceTable
                  ficheros={ficheros}
                  selected={selectedIds}
                  onToggle={toggle}
                  onToggleAll={toggleAll}
                  confianza={confianza}
                />
              )
            ) : error ? (
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
                    className="rounded-lg border border-line bg-surface px-4 py-2 text-[14px] font-semibold text-accent-dark transition hover:bg-accent-soft"
                  >
                    Quitar filtros
                  </button>
                }
              />
            ) : (
              <div aria-busy={loading} className={`transition-opacity duration-200 ${loading ? 'opacity-60' : ''}`}>
                <InvoiceTable
                  ficheros={ficheros}
                  selected={selectedIds}
                  onToggle={toggle}
                  onToggleAll={toggleAll}
                  confianza={confianza}
                />
              </div>
            )}
            {!revisando && data && data.total > 0 && (
              <div className="flex items-center justify-between border-t border-line-soft px-5 py-3 text-[13px] text-muted">
                <span className="flex items-center gap-2">
                  {loading && <Spinner className="size-3 text-accent-dark" />}
                  Mostrando {(data.page - 1) * data.pageSize + 1}–{(data.page - 1) * data.pageSize + ficheros.length} de{' '}
                  {data.total} ficheros
                </span>
                <div className="flex items-center gap-1">
                  <button onClick={() => goToPage(Math.max(1, page - 1))} disabled={page <= 1 || loading} className={pagerButton}>
                    Anterior
                  </button>
                  <span className="rounded-lg border border-line bg-surface px-3 py-1.5 font-semibold text-accent-dark tabular-nums">
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
          <div className="sticky bottom-4 mt-6 flex items-center justify-between gap-3 rounded-xl border border-accent bg-accent-soft px-5 py-3 text-[14px] font-semibold shadow-[0_10px_24px_rgba(43,55,51,0.12)] animate-in fade-in slide-in-from-bottom-2 duration-200">
            {selectedIds.length} fichero{selectedIds.length === 1 ? '' : 's'} seleccionado{selectedIds.length === 1 ? '' : 's'}
            <span className="flex items-center gap-3">
              <button
                onClick={exportFicheros}
                className="rounded-lg bg-accent-dark px-3 py-1.5 text-[13px] font-semibold text-canvas transition hover:bg-ink"
              >
                Exportar selección
              </button>
              <button onClick={() => setSelected({})} className="text-[13px] font-semibold text-accent-dark underline">
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
