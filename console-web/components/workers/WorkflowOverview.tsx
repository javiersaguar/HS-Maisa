import { FileText } from 'lucide-react'
import type { EtapaResumen } from '@/lib/types'
import { ETAPAS, ETAPA_LABELS } from '@/lib/format'
import { Card } from '@/components/ui/Card'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { saludEtapa } from './EtapaIcon'

/** El pipeline fijo: PDF → ingest → extract → validate → enrich → decide → emit → outcomes.jsonl. */
export function WorkflowOverview({ etapas, ficheros }: { etapas: EtapaResumen[]; ficheros: number }) {
  const incidencias = etapas.filter((etapa) => saludEtapa(etapa, ficheros).tone !== 'green').length
  const steps = ['PDF de la Caja', ...ETAPAS.map((etapa) => `${ETAPA_LABELS[etapa]} · ${etapa}`)]

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-[#e5e8e3] bg-[#fbfcfa] px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
          <div className="min-w-0">
            <h2 className="text-[15px] font-semibold">Secuencia del pipeline</h2>
            <p className="mt-1 text-[14px] text-[#8a958e]">Lo que hace albertitos run con cada PDF</p>
          </div>
          <StatusBadge tone={incidencias ? 'yellow' : 'green'} className="shrink-0 whitespace-nowrap">
            {incidencias ? `${incidencias} incidencia${incidencias === 1 ? '' : 's'}` : 'Al día'}
          </StatusBadge>
        </div>
      </div>
      <div className="p-5">
        <div className="mb-5 flex items-center justify-between text-[14px] font-semibold uppercase tracking-wide text-[#8a958e]">
          <span>Entrada</span>
          <span className="font-mono normal-case">outcomes.jsonl</span>
        </div>
        <div className="flex flex-col">
          {steps.map((step, index) => (
            <div key={step} className="flex items-center gap-3">
              <div className="flex flex-col items-center">
                <span
                  className={`flex size-8 items-center justify-center rounded-full text-[13px] font-semibold ${index === 0 ? 'bg-[#164f45] text-white' : 'bg-[#eff8f4] text-[#176d59]'}`}
                >
                  {index === 0 ? <FileText className="size-3.5" /> : index}
                </span>
                {index < steps.length - 1 && <span className="h-7 w-px bg-[#cfe0d7]" />}
              </div>
              <p className="text-[14px] font-medium">{step}</p>
            </div>
          ))}
        </div>
      </div>
    </Card>
  )
}
