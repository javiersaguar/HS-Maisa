'use client'

import { BRAND } from '@/lib/config'
import { formatEur, formatNumber, formatPercent } from '@/lib/format'
import { useEtapas } from '@/hooks/useEtapas'
import { EtapaCard } from '@/components/workers/EtapaCard'
import { EventosTable } from '@/components/workers/EventosTable'
import { WorkflowOverview } from '@/components/workers/WorkflowOverview'
import { Card } from '@/components/ui/Card'
import { ErrorCard, LoadingCard } from '@/components/ui/states'

const KPI_STYLES = [
  { pill: 'Caja + lotes' },
  { pill: 'Tabla eventos' },
  { pill: 'Estado ok' },
  { pill: 'LLM' },
]

export default function EtapasPage() {
  const { data, error, loading, initialLoading, refresh } = useEtapas({ live: true })

  const eventos = data?.etapas.reduce((sum, etapa) => sum + etapa.eventos, 0) ?? 0
  const ok = data?.etapas.reduce((sum, etapa) => sum + etapa.porEstado.ok, 0) ?? 0
  const coste = data?.etapas.reduce((sum, etapa) => sum + etapa.costeEur, 0) ?? 0

  const kpis = data
    ? [
        ['Ficheros', formatNumber(data.ficheros), 'PDFs registrados en la base de datos'],
        ['Eventos', formatNumber(eventos), 'Al menos uno por etapa y fichero'],
        ['Eventos OK', formatPercent(eventos ? (ok / eventos) * 100 : null), 'El resto: reintentos, errores y pendientes'],
        ['Coste acumulado', formatEur(coste, 2), 'Tokens de extracción con LLM'],
      ]
    : []

  return (
    <div className="px-5 py-6 sm:px-8">
      <title>{`Etapas · ${BRAND}`}</title>
      <div className="mx-auto max-w-[1380px]">
        <header className="border-b border-line pb-5">
          <h1 className="titulo text-[24px] text-ink">Etapas</h1>
          <p className="mt-1 text-[13px] text-muted">
            Las seis etapas del pipeline, del PDF a la línea de entrega. Todo sale de la tabla de eventos.
          </p>
        </header>

        {error ? (
          <div className="mt-6">
            <ErrorCard error={error} onRetry={refresh} retrying={loading} />
          </div>
        ) : initialLoading || !data ? (
          <div className="mt-6 grid gap-4 xl:grid-cols-2">
            <LoadingCard label="Cargando etapas" rows={3} />
            <LoadingCard label="Cargando eventos" rows={3} />
          </div>
        ) : (
          <>
            <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {kpis.map(([label, value, description], index) => {
                const style = KPI_STYLES[index]
                return (
                  <Card
                    key={label}
                    className="overflow-hidden border-line bg-surface p-5"
                  >
                    <div className="flex items-baseline justify-between gap-3">
                      <p className="min-w-0 flex-1 text-[26px] font-semibold leading-none tracking-[-0.03em] text-ink cifra">
                        {value}
                      </p>
                      <span className="shrink-0 text-[12px] text-muted">{style.pill}</span>
                    </div>
                    <h3 className="mt-4 text-[14px] font-semibold text-ink">{label}</h3>
                    <p className="mt-1 text-[13px] text-muted">{description}</p>
                  </Card>
                )
              })}
            </section>

            <section className="mt-5">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h2 className="text-[15px] font-semibold">Etapas del pipeline</h2>
                  <p className="text-[14px] text-muted">El anillo es la salud de la etapa, no siempre un recuento de ficheros</p>
                </div>
                <span className="text-[13px] text-muted">{data.etapas.length} etapas</span>
              </div>
              <div className="-mx-1 overflow-x-auto px-1 pb-4 [scrollbar-color:var(--color-line)_transparent] [scrollbar-width:thin]">
                <div className="flex min-w-max gap-4">
                  {data.etapas.map((etapa) => (
                    <EtapaCard key={etapa.etapa} etapa={etapa} ficheros={data.ficheros} />
                  ))}
                </div>
              </div>
            </section>

            <div className="mt-5 grid gap-5 xl:grid-cols-[.72fr_1.28fr]">
              <WorkflowOverview etapas={data.etapas} ficheros={data.ficheros} />
              <Card className="overflow-hidden">
                <div className="flex items-center justify-between gap-4 border-b border-line px-5 py-4">
                  <h2 className="text-[14px] font-semibold">Últimos eventos</h2>
                  <p className="text-[14px] text-muted">De todas las etapas</p>
                </div>
                <EventosTable eventos={data.recientes} showEtapa />
              </Card>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
