'use client'

import { Suspense, useRef, useState, type KeyboardEvent } from 'react'
import { useSearchParams } from 'next/navigation'
import { BRAND } from '@/lib/config'
import { describirEvento, frase, loteNombre, motivoPrincipal, resumenReglas, tituloEvento, tituloRegla } from '@/lib/format'
import { COLORS } from '@/lib/theme'
import { useFichero } from '@/hooks/useFicheros'
import { useTraza } from '@/hooks/useTraza'
import { useConfianzaFichero } from '@/hooks/useConfianza'
import { ChainOfWork } from '@/components/audit/ChainOfWork'
import { AvisoChip, ResultadoBadge } from '@/components/invoices/badges'
import { ErpMatchPanel } from '@/components/invoices/ErpMatchPanel'
import { ExtractedFields, type CampoHecho } from '@/components/invoices/ExtractedFields'
import { InvoiceDocument } from '@/components/invoices/InvoiceDocument'
import { Linaje } from '@/components/invoices/Linaje'
import { ConfianzaChip } from '@/components/confianza/ConfianzaChip'
import { ConfianzaTarjeta } from '@/components/confianza/ConfianzaTarjeta'
import { BackLink } from '@/components/ui/BackLink'
import { Card } from '@/components/ui/Card'
import { EmptyState, ErrorCard, ErrorState, LoadingCard, LoadingState, Skeleton } from '@/components/ui/states'

const TABS = ['Decisión', 'Maestro y ERP', 'Traza'] as const
type Tab = (typeof TABS)[number]

/** `useSearchParams` exige un Suspense para que Next pueda prerenderizar la ruta. */
export default function FicheroDetailPage() {
  return (
    <Suspense fallback={null}>
      <FicheroDetail />
    </Suspense>
  )
}

function FicheroDetail() {
  // `?file=` ya llega decodificado (ver lib/routes.ts); el contrato lo quiere en NFC.
  const fileId = (useSearchParams().get('file') ?? '').normalize('NFC')

  const { data: fichero, error, loading, initialLoading, refresh } = useFichero(fileId)
  const traza = useTraza({ file_id: fileId }, { enabled: Boolean(fileId) })
  // K3: null si no responde o si no hay decisión vigente (404); entonces ni chip ni tarjeta.
  const { data: confianza } = useConfianzaFichero(fileId || null)

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
    <div className="mb-5 flex items-start justify-between gap-4">
      <title>{`${fileId} · ${BRAND}`}</title>
      <div className="min-w-0">
        <h1 className="break-all text-[26px] font-semibold tracking-[-0.03em]">{fileId}</h1>
        {fichero && (
          <p className="mt-1.5 flex items-center gap-2 text-[13px] text-[#8a958e] animate-in fade-in duration-200">
            Factura de {loteNombre(fichero.lote)}
            <ResultadoBadge estado={fichero.estado} />
            {confianza && fichero.decision && (
              <ConfianzaChip puntuacion={confianza.puntuacion} banda={confianza.banda} razon={confianza.razones[0]} />
            )}
          </p>
        )}
      </div>
      <div className="shrink-0">
        <BackLink href="/invoices">Volver a ficheros</BackLink>
      </div>
    </div>
  )

  if (!fileId) {
    return (
      <div className="px-4 py-4 sm:px-6">
        <div className="mx-auto max-w-[1540px]">
          {header}
          <Card>
            <EmptyState
              title="Falta el fichero"
              description="El enlace no dice qué fichero abrir (?file=). Vuelve a la lista y elige uno."
            />
          </Card>
        </div>
      </div>
    )
  }

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
  /** Sin decisión vigente el fichero está PENDIENTE: la traza es lo único que explica por qué. */
  const pendiente = !decision
  /** Eventos, del más antiguo al más nuevo: los 3 últimos o, si está PENDIENTE, todos. */
  const eventos = pasos.filter((paso) => paso.tipo === 'evento')
  const recientes = pendiente ? eventos : eventos.slice(-3)
  const incidencia = [...pasos].reverse().find((paso) => paso.tipo === 'evento' && paso.evento.estado !== 'ok')
  const pasosRecientes = (
    <>
      <h3 className="mt-6 text-[13px] font-bold uppercase tracking-wide">Qué ha pasado con este fichero</h3>
      {traza.error ? (
        <p className="mt-2 text-[13px] text-[#bd3434]">
          No se han podido cargar los pasos.{' '}
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
        <p className="mt-2 text-[13px] text-[#9aa39e]">Todavía no hay pasos registrados.</p>
      ) : (
        <div className="mt-2 flex flex-col gap-4 border-l-2 border-[#b9dfd0] pl-3 text-[14px]">
          {recientes.map((paso) =>
            paso.tipo === 'evento' ? (
              <div key={paso.id} className="animate-in fade-in slide-in-from-left-1 duration-300">
                <b className="font-semibold text-[#17211e]">{tituloEvento(paso.evento)}</b>
                <p className="mt-0.5 text-[13px] leading-5 text-[#68736d]">{describirEvento(paso.evento)}</p>
              </div>
            ) : null,
          )}
        </div>
      )}
    </>
  )
  const chainHeading = (
    <div>
      <h2 className="text-[22px] font-semibold tracking-[-0.025em]">Traza</h2>
      <p className="mt-1 text-[13px] text-[#8a958e]">
        Cómo se ha leído, cruzado y decidido este fichero, paso a paso.
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
                          {decision ? resumenReglas(decision) : 'Todavía no hay decisión'}
                        </span>
                      </div>
                      <p className="mt-3 text-[13px] leading-5 text-[#52605a]">
                        {decision
                          ? motivoPrincipal(fichero)
                          : incidencia?.tipo === 'evento'
                            ? describirEvento(incidencia.evento)
                            : 'Este fichero todavía no tiene una decisión.'}
                      </p>
                      {pendiente && (
                        <p className="mt-2 text-[12px] leading-5 text-[#7d8580]">
                          Está <b className="font-semibold">PENDIENTE</b>: no hay hechos validados, así que la norma no
                          se ha aplicado y nunca se paga. Abajo, lo que sí ha pasado.
                        </p>
                      )}
                    </div>

                    {decision && confianza && <ConfianzaTarjeta ficha={confianza} />}

                    {pendiente && pasosRecientes}

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

                    <h3 className="mt-6 text-[13px] font-bold uppercase tracking-wide">Qué ha comprobado la norma</h3>
                    {decision ? (
                      <ul className="mt-2 overflow-hidden rounded-lg border border-[#dfe4de] text-[13px] leading-5 text-[#68736d]">
                        {decision.motivos.map((motivo) => (
                          <li
                            key={motivo.regla_id}
                            className="grid grid-cols-[10px_minmax(0,1fr)] items-start gap-2 border-b border-[#edf0ec] bg-[#fafbf9] px-3 py-2 last:border-b-0"
                          >
                            <span
                              aria-label={motivo.ok ? 'Cumple' : motivo.evidencia.no_pagar ? 'No pagar' : 'Escalar'}
                              className="mt-[6px] size-2 rounded-full"
                              style={{
                                background: motivo.ok ? COLORS.mint : motivo.evidencia.no_pagar ? COLORS.dangerSoft : '#c9a800',
                              }}
                            />
                            <span>
                              <b className="font-semibold text-[#17211e]">{tituloRegla(motivo.regla_id)}.</b>{' '}
                              {frase(motivo.detalle)}
                            </span>
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
                        <h3 className="mt-6 text-[13px] font-bold uppercase tracking-wide">Al leer el PDF se vio</h3>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {hechos.avisos.map((aviso) => (
                            <AvisoChip key={aviso} aviso={aviso} />
                          ))}
                        </div>
                      </>
                    )}

                    <h3 className="mt-6 text-[13px] font-bold uppercase tracking-wide">Datos leídos del PDF</h3>
                    <ExtractedFields
                      hechos={hechos}
                      activeField={activeField}
                      onSelect={(key) => setActiveField(activeField === key ? null : key)}
                    />

                    {!pendiente && pasosRecientes}
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
