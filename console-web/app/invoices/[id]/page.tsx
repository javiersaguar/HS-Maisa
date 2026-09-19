'use client'

import { useRef, useState, type KeyboardEvent } from 'react'
import { useParams } from 'next/navigation'
import { BRAND } from '@/lib/config'
import { formatTime, motivoPrincipal } from '@/lib/format'
import { COLORS } from '@/lib/theme'
import { useFichero } from '@/hooks/useFicheros'
import { useTraza } from '@/hooks/useTraza'
import { ChainOfWork } from '@/components/audit/ChainOfWork'
import { AvisoChip, ResultadoBadge } from '@/components/invoices/badges'
import { ErpMatchPanel } from '@/components/invoices/ErpMatchPanel'
import { ExtractedFields, type CampoHecho } from '@/components/invoices/ExtractedFields'
import { InvoiceDocument } from '@/components/invoices/InvoiceDocument'
import { Linaje } from '@/components/invoices/Linaje'
import { BackLink } from '@/components/ui/BackLink'
import { Card } from '@/components/ui/Card'
import { ErrorCard, ErrorState, LoadingCard, LoadingState, Skeleton } from '@/components/ui/states'

const TABS = ['Decisión', 'Maestro y ERP', 'Traza'] as const
type Tab = (typeof TABS)[number]

/** El segmento de la URL es el file_id codificado; el contrato lo quiere en NFC. */
function fileIdFrom(param: string | undefined): string {
  if (!param) return ''
  try {
    return decodeURIComponent(param).normalize('NFC')
  } catch {
    return param.normalize('NFC')
  }
}

export default function FicheroDetailPage() {
  const { id } = useParams<{ id: string }>()
  const fileId = fileIdFrom(id)

  const { data: fichero, error, loading, initialLoading, refresh } = useFichero(fileId)
  const traza = useTraza({ file_id: fileId }, { enabled: Boolean(fileId) })

  const [zoom, setZoom] = useState(100)
  const [highlight, setHighlight] = useState(true)
  const [activeField, setActiveField] = useState<CampoHecho | null>(null)
  const [tab, setTab] = useState<Tab>('Decisión')
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([])

  /** Flechas para moverse entre pestañas, como en cualquier tablist. */
  const onTabKey = (event: KeyboardEvent, index: number) => {
    const delta = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0
    if (!delta) return
    const next = (index + delta + TABS.length) % TABS.length
    setTab(TABS[next])
    tabRefs.current[next]?.focus()
  }

  const header = (
    <div className="mb-5">
      <title>{`${fileId} · ${BRAND}`}</title>
      <BackLink href="/invoices">Volver a ficheros</BackLink>
      <h1 className="mt-2 break-all text-[26px] font-semibold tracking-[-0.03em]">{fileId}</h1>
      {fichero && (
        <p className="mt-1.5 flex items-center gap-2 text-[13px] text-[#8a958e] animate-in fade-in duration-200">
          Lote {fichero.lote}
          <ResultadoBadge estado={fichero.estado} />
        </p>
      )}
    </div>
  )

  if (error) {
    return (
      <div className="px-4 py-4 sm:px-6">
        <div className="mx-auto max-w-[1540px]">
          {header}
          <ErrorCard
            error={error}
            onRetry={refresh}
            retrying={loading}
            title={error.isNotFound ? `No existe el fichero ${fileId}` : undefined}
          />
        </div>
      </div>
    )
  }

  if (initialLoading || !fichero) {
    return (
      <div className="px-4 py-4 sm:px-6">
        <div className="mx-auto max-w-[1540px]">
          {header}
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_500px]">
            <LoadingCard label="Cargando documento" rows={8} />
            <LoadingCard label="Cargando decisión" rows={5} />
          </div>
        </div>
      </div>
    )
  }

  const { hechos, decision } = fichero
  const pasos = traza.data ?? []
  /** Últimos eventos, del más antiguo al más nuevo, para el resumen de la pestaña Decisión. */
  const recientes = pasos.filter((paso) => paso.tipo === 'evento').slice(-3)
  const incidencia = [...pasos].reverse().find((paso) => paso.tipo === 'evento' && paso.evento.estado !== 'ok')
  const chainHeading = (
    <div>
      <h2 className="text-[22px] font-semibold tracking-[-0.025em]">Traza</h2>
      <p className="mt-1 text-[13px] text-[#8a958e]">
        Hechos → maestro → asiento ERP → reglas con evidencia → resultado. Con latencias, reintentos, tokens y coste.
      </p>
    </div>
  )

  return (
    <div className="px-4 py-4 sm:px-6">
      <div className="mx-auto max-w-[1540px]">
        {header}
        <div className="grid min-h-[calc(100vh-112px)] gap-5 lg:grid-cols-[minmax(0,1fr)_500px]">
          <InvoiceDocument
            fichero={fichero}
            zoom={zoom}
            onZoom={setZoom}
            highlight={highlight}
            onToggleHighlight={() => setHighlight(!highlight)}
            activeField={activeField}
          />
          <aside className="min-w-0">
            <Card className="h-full overflow-hidden border-[#d9e2dc] shadow-[0_8px_30px_rgba(30,55,45,0.06)]">
              <div className="flex border-b border-[#e3e9e4] bg-white px-2" role="tablist" aria-label="Análisis del fichero">
                {TABS.map((item, index) => (
                  <button
                    key={item}
                    ref={(element) => {
                      tabRefs.current[index] = element
                    }}
                    role="tab"
                    id={`tab-${index}`}
                    aria-selected={tab === item}
                    aria-controls="fichero-tabpanel"
                    tabIndex={tab === item ? 0 : -1}
                    onClick={() => setTab(item)}
                    onKeyDown={(event) => onTabKey(event, index)}
                    className={`relative flex flex-1 items-center justify-center gap-1.5 px-3 py-3 text-[13px] font-semibold transition-colors ${tab === item ? 'text-[#164f45]' : 'text-[#9aa39e] hover:text-[#315d53]'}`}
                  >
                    {item}
                    {item === 'Traza' && traza.data && (
                      <span className="rounded-full bg-[#eff8f3] px-1.5 text-[11px] text-[#176d59] tabular-nums">
                        {pasos.length}
                      </span>
                    )}
                    <span
                      className={`absolute inset-x-3 bottom-0 h-0.5 rounded bg-[#164f45] transition-all duration-300 ${tab === item ? 'opacity-100' : 'scale-x-0 opacity-0'}`}
                    />
                  </button>
                ))}
              </div>
              <div
                key={tab}
                id="fichero-tabpanel"
                role="tabpanel"
                aria-labelledby={`tab-${TABS.indexOf(tab)}`}
                className="max-h-[calc(100vh-165px)] overflow-y-auto p-5 animate-in fade-in slide-in-from-bottom-1 duration-200"
              >
                {tab === 'Decisión' && (
                  <>
                    <div className="rounded-xl border border-[#e4e5df] bg-[#f1f1ef] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <ResultadoBadge estado={fichero.estado} withIcon={false} />
                        <span className="text-[13px] text-[#7d8580]">
                          {decision ? `${decision.motivos.filter((motivo) => !motivo.ok).length} de ${decision.motivos.length} reglas incumplidas` : 'sin decisión vigente'}
                        </span>
                      </div>
                      <p className="mt-3 text-[13px] leading-5 text-[#52605a]">
                        {decision
                          ? motivoPrincipal(fichero)
                          : incidencia?.tipo === 'evento'
                            ? `${incidencia.evento.error_codigo ?? incidencia.evento.estado}: ${incidencia.evento.detalle ?? ''}`
                            : 'El fichero no tiene decisión vigente.'}
                      </p>
                    </div>

                    <Linaje decision={decision} />

                    {hechos?.texto_sospechoso && (
                      <div className="mt-4 rounded-xl border border-dashed border-[#e0c95a] bg-[#fffbe8] p-4">
                        <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#a08400]">
                          El documento intenta instruir
                        </p>
                        <p className="mt-1.5 text-[13px] italic leading-5 text-[#5f5b2e]">“{hechos.texto_sospechoso}”</p>
                        <p className="mt-2 text-[12px] text-[#8a7f45]">
                          Es evidencia, no una orden: la norma lo trata como anomalía (R6) y decide con las reglas.
                        </p>
                      </div>
                    )}

                    <h3 className="mt-6 text-[13px] font-bold uppercase tracking-wide">Reglas de la norma</h3>
                    {decision ? (
                      <ul className="mt-2 overflow-hidden rounded-lg border border-[#dfe4de] text-[13px] leading-5 text-[#68736d]">
                        {decision.motivos.map((motivo) => (
                          <li
                            key={motivo.regla_id}
                            className="grid grid-cols-[10px_52px_minmax(0,1fr)] items-start gap-2 border-b border-[#edf0ec] bg-[#fafbf9] px-3 py-2 last:border-b-0"
                          >
                            <span
                              aria-label={motivo.ok ? 'Cumple' : motivo.evidencia.no_pagar ? 'No pagar' : 'Escalar'}
                              className="mt-[6px] size-2 rounded-full"
                              style={{
                                background: motivo.ok ? COLORS.mint : motivo.evidencia.no_pagar ? COLORS.dangerSoft : '#c9a800',
                              }}
                            />
                            <b className="font-mono text-[12px] text-[#17211e]">{motivo.regla_id}</b>
                            <span>{motivo.detalle}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-2 text-[13px] text-[#9aa39e]">La norma todavía no se ha aplicado a este fichero.</p>
                    )}
                    <p className="mt-2 text-[13px]">
                      <button onClick={() => setTab('Traza')} className="min-h-0 text-[#315d53] underline">
                        Ver evidencia en la traza
                      </button>
                    </p>

                    {hechos && hechos.avisos.length > 0 && (
                      <>
                        <h3 className="mt-6 text-[13px] font-bold uppercase tracking-wide">Avisos al leer el PDF</h3>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {hechos.avisos.map((aviso) => (
                            <AvisoChip key={aviso} aviso={aviso} />
                          ))}
                        </div>
                      </>
                    )}

                    <h3 className="mt-6 text-[13px] font-bold uppercase tracking-wide">Hechos extraídos</h3>
                    <ExtractedFields
                      hechos={hechos}
                      activeField={activeField}
                      onSelect={(key) => setActiveField(activeField === key ? null : key)}
                    />

                    <h3 className="mt-6 text-[13px] font-bold uppercase tracking-wide">Últimos eventos</h3>
                    {traza.error ? (
                      <p className="mt-2 text-[13px] text-[#bd3434]">
                        Traza no disponible: {traza.error.message}{' '}
                        <button onClick={traza.refresh} className="min-h-0 font-semibold underline">
                          Reintentar
                        </button>
                      </p>
                    ) : !traza.data ? (
                      <div className="mt-2 flex flex-col gap-3 border-l-2 border-[#e7e9e5] pl-3">
                        <Skeleton className="h-8 w-3/4" />
                        <Skeleton className="h-8 w-2/3" />
                      </div>
                    ) : recientes.length === 0 ? (
                      <p className="mt-2 text-[13px] text-[#9aa39e]">Sin eventos registrados todavía.</p>
                    ) : (
                      <div className="mt-2 flex flex-col gap-4 border-l-2 border-[#b9dfd0] pl-3 text-[14px]">
                        {recientes.map((paso) =>
                          paso.tipo === 'evento' ? (
                            <div key={paso.id} className="animate-in fade-in slide-in-from-left-1 duration-300">
                              <b className="font-mono">{paso.evento.etapa}</b>
                              <span className="ml-2 text-[#a0a7a2]">{formatTime(paso.ts)}</span>
                              <p className="text-[#9aa39e]">{paso.evento.detalle ?? paso.evento.estado}</p>
                            </div>
                          ) : null,
                        )}
                      </div>
                    )}
                  </>
                )}

                {tab === 'Maestro y ERP' && <ErpMatchPanel fuentes={fichero.fuentes} hechos={hechos} />}

                {tab === 'Traza' &&
                  (traza.error ? (
                    <>
                      {chainHeading}
                      <div className="mt-5">
                        <ErrorState error={traza.error} onRetry={traza.refresh} retrying={traza.loading} />
                      </div>
                    </>
                  ) : !traza.data ? (
                    <>
                      {chainHeading}
                      <div className="mt-5">
                        <LoadingState label="Cargando traza" rows={4} />
                      </div>
                    </>
                  ) : (
                    <ChainOfWork pasos={pasos} header={chainHeading} showDate={false} showFile={false} />
                  ))}
              </div>
            </Card>
          </aside>
        </div>
      </div>
    </div>
  )
}
