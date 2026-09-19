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
  { icon: '▤', color: '#176d59', iconBg: '#e4f8ef', pill: 'Caja + lotes' },
  { icon: '↗', color: '#6354a8', iconBg: '#f0edff', pill: 'Tabla eventos' },
  { icon: '✓', color: '#16825f', iconBg: '#e4f8ef', pill: 'Estado ok' },
  { icon: '€', color: '#b36a35', iconBg: '#fff1e4', pill: 'LLM' },
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
        <header className="border-b border-[#e2e5df] pb-5">
          <h1 className="text-[22px] font-semibold tracking-[-0.03em]">Etapas</h1>
          <p className="mt-1 text-[13px] text-[#8d9891]">
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
                    className="overflow-hidden rounded-2xl border-[#e5e9e4] bg-[#fffefa] p-5 shadow-[0_7px_24px_rgba(20,55,45,0.045)]"
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className="flex size-9 shrink-0 items-center justify-center rounded-xl text-[18px] font-semibold"
                        style={{ color: style.color, backgroundColor: style.iconBg }}
                      >
                        {style.icon}
                      </span>
                      <p
                        className="min-w-0 flex-1 text-[30px] font-bold leading-none tracking-[-0.06em] tabular-nums"
                        style={{ color: style.color }}
                      >
                        {value}
                      </p>
                      <span
                        className="shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold"
                        style={{ color: style.color, backgroundColor: style.iconBg }}
                      >
                        {style.pill}
                      </span>
                    </div>
                    <h3 className="mt-4 text-[14px] font-semibold text-[#354940]">{label}</h3>
                    <p className="mt-1 text-[13px] text-[#829088]">{description}</p>
                  </Card>
                )
              })}
            </section>

            <section className="mt-5">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h2 className="text-[15px] font-semibold">Etapas del pipeline</h2>
                  <p className="text-[14px] text-[#9aa39e]">El anillo es la salud de la etapa, no siempre un recuento de ficheros</p>
                </div>
                <span className="text-[13px] text-[#8d9891]">{data.etapas.length} etapas</span>
              </div>
              <div className="-mx-1 overflow-x-auto px-1 pb-4 [scrollbar-color:#b8d8ca_transparent] [scrollbar-width:thin]">
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
                <div className="flex items-center justify-between gap-4 border-b border-[#e5e8e3] px-5 py-4">
                  <h2 className="text-[14px] font-semibold">Últimos eventos</h2>
                  <p className="text-[14px] text-[#9aa39e]">De todas las etapas</p>
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
