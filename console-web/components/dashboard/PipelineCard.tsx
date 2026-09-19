import type { ReactNode } from 'react'
import Link from 'next/link'
import type { EtapaResumen } from '@/lib/types'
import { ETAPA_DESCRIPCIONES, ETAPA_LABELS, lineaResumenEtapa, tooltipCoberturaEtapa } from '@/lib/format'
import { Card } from '@/components/ui/Card'
import { ProgressRing } from '@/components/ui/ProgressRing'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { EtapaIcon, etapaConIncidencia, saludEtapa } from '@/components/workers/EtapaIcon'

/** Columna izquierda del panel: las seis etapas y su salud según los eventos reales. */
export function PipelineCard({ etapas, ficheros, actions }: { etapas: EtapaResumen[]; ficheros: number; actions?: ReactNode }) {
  const incidencias = etapas.filter((etapa) => etapaConIncidencia(etapa, ficheros)).length
  const alDia = etapas.length - incidencias
  return (
    <Card className="flex min-h-[720px] flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <div>
          <h2 className="text-[14px] font-semibold">Etapas del pipeline</h2>
          <p className="text-[14px] text-muted">Salud de cada etapa según sus eventos</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <StatusBadge tone={incidencias ? 'yellow' : 'green'} className="whitespace-nowrap">
            {alDia} de {etapas.length}
          </StatusBadge>
          {actions}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {etapas.map((etapa) => {
          const salud = saludEtapa(etapa, ficheros)
          const ok = salud.tone === 'green'
          return (
            <Link
              key={etapa.etapa}
              href={`/workers/${etapa.etapa}`}
              className="group flex items-center justify-between gap-3 border-b border-line-soft px-5 py-4 transition last:border-0 hover:bg-surface"
            >
              <div className="flex min-w-0 items-center gap-4">
                <div
                  className={`flex size-8 shrink-0 items-center justify-center transition-colors duration-500 ${
                    ok ? 'bg-raised text-accent-dark' : salud.tone === 'gray' ? 'bg-raised text-ink-soft' : ' text-warn'
                  }`}
                >
                  <EtapaIcon etapa={etapa.etapa} className="size-4" />
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-[14px] font-semibold">{ETAPA_LABELS[etapa.etapa]}</p>
                    <span className="font-mono text-[12px] text-muted">{etapa.etapa}</span>
                    <StatusBadge tone={salud.tone}>{salud.label}</StatusBadge>
                  </div>
                  <p className="mt-0.5 text-[14px] text-ink-soft">{ETAPA_DESCRIPCIONES[etapa.etapa]}</p>
                  <p className="mt-1 text-[13px] text-muted">{lineaResumenEtapa(etapa, ficheros)}</p>
                </div>
              </div>
              <ProgressRing value={salud.cobertura} tooltip={tooltipCoberturaEtapa(etapa, ficheros, salud.cobertura)} />
            </Link>
          )
        })}
      </div>
    </Card>
  )
}
