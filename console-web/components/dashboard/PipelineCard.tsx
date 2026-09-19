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
      <div className="flex items-center justify-between border-b border-[#e5e8e3] px-5 py-4">
        <div>
          <h2 className="text-[14px] font-semibold">Etapas del pipeline</h2>
          <p className="text-[14px] text-[#9aa39e]">Salud de cada etapa según sus eventos</p>
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
              className="group flex items-center justify-between gap-3 border-b border-[#edf0ec] px-5 py-4 transition last:border-0 hover:bg-[#fafcf9]"
            >
              <div className="flex min-w-0 items-center gap-4">
                <div
                  className={`flex size-8 shrink-0 items-center justify-center rounded-lg transition-colors duration-500 ${
                    ok ? 'bg-[#effaf6] text-[#176d59]' : salud.tone === 'gray' ? 'bg-[#f1f5f3] text-[#63756d]' : 'bg-[#fff9e6] text-[#a87000]'
                  }`}
                >
                  <EtapaIcon etapa={etapa.etapa} className="size-4" />
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-[14px] font-semibold">{ETAPA_LABELS[etapa.etapa]}</p>
                    <span className="font-mono text-[12px] text-[#9aa39e]">{etapa.etapa}</span>
                    <StatusBadge tone={salud.tone}>{salud.label}</StatusBadge>
                  </div>
                  <p className="mt-0.5 text-[14px] text-[#69736d]">{ETAPA_DESCRIPCIONES[etapa.etapa]}</p>
                  <p className="mt-1 text-[13px] text-[#8d9891]">{lineaResumenEtapa(etapa, ficheros)}</p>
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
