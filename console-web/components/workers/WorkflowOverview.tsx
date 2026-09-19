import { FileText } from 'lucide-react'
import type { EtapaResumen } from '@/lib/types'
import { ETAPAS, ETAPA_LABELS } from '@/lib/format'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { etapaConIncidencia } from './EtapaIcon'

/** El pipeline fijo: PDF → ingest → extract → validate → enrich → decide → emit → outcomes.jsonl. */
export function WorkflowOverview({ etapas, ficheros }: { etapas: EtapaResumen[]; ficheros: number }) {
  const incidencias = etapas.filter((etapa) => etapaConIncidencia(etapa, ficheros)).length
  const steps = ['PDF de la Caja', ...ETAPAS.map((etapa) => `${ETAPA_LABELS[etapa]} · ${etapa}`)]

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-line bg-[var(--color-raised)] px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <div className="min-w-0">
            <h2 className="text-[15px] font-semibold">Secuencia del pipeline</h2>
            <p className="mt-1 text-[14px] text-muted">Lo que hace albertitos run con cada PDF</p>
          </div>
          <StatusBadge tone={incidencias ? 'yellow' : 'green'} className="shrink-0 whitespace-nowrap">
            {incidencias ? `${incidencias} incidencia${incidencias === 1 ? '' : 's'}` : 'Al día'}
          </StatusBadge>
        </div>
      </div>
      <div className="p-5">
        <div className="mb-5 flex items-center justify-between text-[14px] font-semibold uppercase tracking-wide text-muted">
          <span>Entrada</span>
          <span className="font-mono normal-case">outcomes.jsonl</span>
        </div>
        <div className="flex flex-col">
          {steps.map((step, index) => (
            <div key={step} className="flex items-center gap-3">
              <div className="flex flex-col items-center">
                <span
                  className={`flex size-7 items-center justify-center text-[12px] font-medium ${index === 0 ? 'bg-accent-dark text-canvas' : 'bg-raised text-accent-dark'}`}
                >
                  {index === 0 ? <FileText className="size-3.5" /> : index}
                </span>
                {index < steps.length - 1 && <span className="h-7 w-px bg-raised" />}
              </div>
              <p className="text-[14px] font-medium">{step}</p>
            </div>
          ))}
        </div>
      </div>
    </Card>
  )
}
