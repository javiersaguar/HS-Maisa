'use client'

import { useCallback, useState } from 'react'
import { usePanel } from '@/hooks/usePanel'
import { BRAND } from '@/lib/config'
import { downloadCsv } from '@/lib/csv'
import { motivoPrincipal } from '@/lib/format'
import { ActivityChart } from '@/components/dashboard/ActivityChart'
import { DecisionDistribution } from '@/components/dashboard/DecisionDistribution'
import { PipelineCard } from '@/components/dashboard/PipelineCard'
import { ProcessingHealth } from '@/components/dashboard/ProcessingHealth'
import { RecentDecisions } from '@/components/dashboard/RecentDecisions'
import { ErrorCard, LoadingCard } from '@/components/ui/states'
import { Toast } from '@/components/ui/Toast'

export default function PanelPage() {
  const { data, error, loading, initialLoading, refresh } = usePanel({ live: true })
  const [toast, setToast] = useState<string | null>(null)
  const dismissToast = useCallback(() => setToast(null), [])

  if (error) {
    return (
      <div className="mx-auto max-w-[1380px] p-6 pt-5">
        <ErrorCard error={error} onRetry={refresh} retrying={loading} />
      </div>
    )
  }

  if (initialLoading || !data) {
    return (
      <div className="mx-auto flex max-w-[1380px] flex-col gap-4 p-6 pt-5">
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[.9fr_1.1fr]">
          <LoadingCard label="Cargando etapas" rows={3} />
          <LoadingCard label="Cargando contadores" rows={4} />
        </div>
        <LoadingCard label="Cargando últimas decisiones" rows={5} />
      </div>
    )
  }

  const exportRecientes = () => {
    downloadCsv(
      'albertitos-ultimas-decisiones.csv',
      ['file_id', 'result', 'motivo', 'norma_version'],
      data.recientes.map((fichero) => [
        fichero.file_id,
        fichero.estado,
        fichero.decision ? motivoPrincipal(fichero) : '',
        fichero.decision?.norma_version ?? '',
      ]),
    )
    setToast(`${data.recientes.length} decisiones exportadas a CSV`)
  }

  return (
    <div className="mx-auto flex max-w-[1380px] flex-col gap-4 p-6 pt-5">
      <title>{`Panel · ${BRAND}`}</title>
      <div className="grid grid-cols-1 items-stretch gap-4 xl:grid-cols-[.9fr_1.1fr]">
        <PipelineCard
          etapas={data.etapas}
          ficheros={data.ficheros}
          actions={
            <button
              onClick={exportRecientes}
              disabled={!data.recientes.length}
              className="hidden rounded-lg border border-[#dfe4de] px-3 py-1.5 text-[13px] font-medium text-[#59635e] transition hover:bg-[#f5f7f3] disabled:opacity-40 sm:block"
            >
              Exportar CSV
            </button>
          }
        />
        <div className="flex flex-col gap-4">
          <ProcessingHealth panel={data} />
          <DecisionDistribution shares={data.distribucion} />
          <ActivityChart data={data.porMes} />
        </div>
      </div>
      <RecentDecisions ficheros={data.recientes} />
      {toast && <Toast message={toast} onDismiss={dismissToast} />}
    </div>
  )
}
