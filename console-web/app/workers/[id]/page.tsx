'use client'

import { useParams } from 'next/navigation'
import type { Etapa } from '@/lib/types'
import { ApiError } from '@/lib/api/client'
import { BRAND } from '@/lib/config'
import {
  ESTADO_EVENTO_LABELS,
  ETAPAS,
  ETAPA_DESCRIPCIONES,
  ETAPA_GRANO,
  ETAPA_LABELS,
  formatEur,
  formatMs,
  formatNumber,
  formatPercent,
  pieCoberturaEtapa,
} from '@/lib/format'
import { useEtapas, useEventos } from '@/hooks/useEtapas'
import { useTraza } from '@/hooks/useTraza'
import { ChainOfWork } from '@/components/audit/ChainOfWork'
import { EtapaIcon, saludEtapa } from '@/components/workers/EtapaIcon'
import { EventosTable } from '@/components/workers/EventosTable'
import { WorkerKpi } from '@/components/workers/WorkerKpi'
import { BackLink } from '@/components/ui/BackLink'
import { Activity, Clock, Euro, RotateCw, Target } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { ErrorCard, ErrorState, LoadingCard, LoadingState } from '@/components/ui/states'

const TONE_STYLE = {
  green: { color: 'var(--color-ok)', tint: 'var(--color-ok-soft)' },
  yellow: { color: 'var(--color-warn)', tint: 'var(--color-warn-soft)' },
  red: { color: 'var(--color-bad)', tint: 'var(--color-bad-soft)' },
  gray: { color: 'var(--color-muted)', tint: 'var(--color-raised)' },
} as const

export default function EtapaDetailPage() {
  const { id } = useParams<{ id: string }>()
  const etapaId = ETAPAS.includes(id as Etapa) ? (id as Etapa) : null

  const { data, error, loading, initialLoading, refresh } = useEtapas({ live: true })
  const eventos = useEventos(etapaId)
  const traza = useTraza({ etapa: etapaId ?? undefined }, { enabled: Boolean(etapaId) })

  const back = (
    <div className="mb-5">
      <title>{`${etapaId ? ETAPA_LABELS[etapaId] : 'Etapa'} · ${BRAND}`}</title>
      <BackLink href="/workers">Volver a etapas</BackLink>
    </div>
  )

  const shell = (children: React.ReactNode) => (
    <div className="px-5 py-6 sm:px-8">
      <div className="mx-auto max-w-[1380px]">
        {back}
        {children}
      </div>
    </div>
  )

  if (!etapaId) {
    return shell(
      <ErrorCard
        error={new ApiError(`Las etapas son: ${ETAPAS.join(', ')}.`, 404)}
        title={`No existe la etapa ${id}`}
      />,
    )
  }

  if (error) return shell(<ErrorCard error={error} onRetry={refresh} retrying={loading} />)

  const etapa = data?.etapas.find((item) => item.etapa === etapaId)
  if (initialLoading || !data || !etapa) return shell(<LoadingCard label="Cargando etapa" rows={4} />)

  const salud = saludEtapa(etapa, data.ficheros)
  const incidencias = etapa.eventos - etapa.porEstado.ok
  const hasCost = etapa.costeEur > 0
  const chainHeading = (
    <div>
      <h2 className="text-[14px] font-semibold">Traza</h2>
      <p className="text-[14px] text-muted">Últimos pasos de esta etapa{etapaId === 'decide' ? ', con las reglas de la norma' : ''}</p>
    </div>
  )

  return shell(
    <>
      <header className="flex items-center gap-4 border-b border-line pb-5">
        <div className="flex size-12 items-center justify-center rounded-xl bg-accent-soft text-accent-dark">
          <EtapaIcon etapa={etapaId} className="size-6" />
        </div>
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-[22px] font-semibold tracking-[-0.03em]">{ETAPA_LABELS[etapaId]}</h1>
            <span className="font-mono text-[14px] text-muted">{etapaId}</span>
            <StatusBadge tone={salud.tone}>{salud.label}</StatusBadge>
          </div>
          <p className="mt-1 text-[13px] text-muted">
            {ETAPA_DESCRIPCIONES[etapaId]}
            {etapa.version ? ` · versión ${etapa.version}` : ''}
          </p>
        </div>
      </header>

      <section className={`mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 ${hasCost ? 'xl:grid-cols-5' : 'xl:grid-cols-4'}`}>
        <WorkerKpi
          icon={<Target className="size-4" />}
          label={ETAPA_GRANO[etapaId] === 'lote' ? 'Peticiones OK' : 'Cobertura'}
          value={ETAPA_GRANO[etapaId] === 'lote' ? formatNumber(etapa.eventos) : formatPercent(salud.cobertura)}
          {...TONE_STYLE[salud.tone]}
        >
          {pieCoberturaEtapa(etapa, data.ficheros)}
        </WorkerKpi>
        <WorkerKpi
          icon={<Activity className="size-4" />}
          label="Eventos"
          value={formatNumber(etapa.eventos)}
          color="var(--color-ink-soft)"
          tint="var(--color-raised)"
        >
          {incidencias
            ? (Object.keys(etapa.porEstado) as Array<keyof typeof etapa.porEstado>)
                .filter((estado) => estado !== 'ok' && etapa.porEstado[estado] > 0)
                .map((estado) => `${etapa.porEstado[estado]} ${ESTADO_EVENTO_LABELS[estado].toLowerCase()}`)
                .join(' · ')
            : 'Todos en estado ok'}
        </WorkerKpi>
        <WorkerKpi
          icon={<RotateCw className="size-4" />}
          label="Reintentos"
          value={formatNumber(etapa.reintentos)}
          color="var(--color-ok)"
          tint="var(--color-ok-soft)"
        >
          Eventos con intento &gt; 1
        </WorkerKpi>
        <WorkerKpi
          icon={<Clock className="size-4" />}
          label="Latencia media"
          value={formatMs(etapa.latenciaMediaMs)}
          color="var(--color-warn)"
          tint="var(--color-warn-soft)"
        >
          Por evento
        </WorkerKpi>
        {hasCost && (
          <WorkerKpi
            icon={<Euro className="size-4" />}
            label="Coste"
            value={formatEur(etapa.costeEur, 2)}
            color="var(--color-accent-dark)"
            tint="var(--color-accent-soft)"
          >
            {formatNumber(etapa.tokensIn)} tokens de entrada · {formatNumber(etapa.tokensOut)} de salida
          </WorkerKpi>
        )}
      </section>

      <div className="mt-5 grid gap-5 lg:grid-cols-[1.2fr_.8fr]">
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between gap-4 border-b border-line px-5 py-4">
            <h2 className="text-[14px] font-semibold">Últimos eventos</h2>
            <p className="text-[14px] text-muted">Filas de la tabla eventos con etapa = {etapaId}</p>
          </div>
          {eventos.error ? (
            <ErrorState error={eventos.error} onRetry={eventos.refresh} retrying={eventos.loading} />
          ) : !eventos.data ? (
            <LoadingState label="Cargando eventos" rows={4} />
          ) : (
            <EventosTable eventos={eventos.data} />
          )}
        </Card>
        <Card className="p-5">
          {traza.error ? (
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
                <LoadingState label="Cargando traza" rows={3} />
              </div>
            </>
          ) : (
            <ChainOfWork pasos={traza.data.slice(0, 8)} emptyTitle="Sin pasos en esta etapa" header={chainHeading} />
          )}
        </Card>
      </div>
    </>,
  )
}
