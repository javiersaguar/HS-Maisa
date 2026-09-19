'use client'

import { useState } from 'react'
import type { CategoriaTraza } from '@/lib/types'
import { BRAND } from '@/lib/config'
import { useTraza } from '@/hooks/useTraza'
import { ChainOfWork } from '@/components/audit/ChainOfWork'
import { TraceFilter } from '@/components/audit/TraceFilter'
import { Card } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { ErrorState, LoadingState } from '@/components/ui/states'

export default function TrazaPage() {
  const [categoria, setCategoria] = useState<CategoriaTraza | 'all'>('all')
  const { data, error, loading, refresh } = useTraza({ categoria })

  return (
    <div className="mx-auto max-w-[980px] p-6 pt-3 sm:p-8 sm:pt-4">
      <title>{`Traza · ${BRAND}`}</title>
      <Card className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="titulo text-[24px] text-ink">Traza</h1>
            <p className="mt-1 text-[13px] text-muted">
              Chain of Work del pipeline: eventos de cada etapa (latencia, reintentos, tokens, coste) y cada regla de
              la norma con su evidencia. Lo más reciente primero.
            </p>
          </div>
          <TraceFilter value={categoria} onChange={setCategoria} />
        </div>
        {error ? (
          <ErrorState error={error} onRetry={refresh} retrying={loading} />
        ) : !data ? (
          <LoadingState label="Cargando traza" rows={5} />
        ) : (
          <div aria-busy={loading} className={`mt-5 transition-opacity duration-200 ${loading ? 'opacity-60' : ''}`}>
            <ChainOfWork
              key={categoria}
              pasos={data}
              emptyTitle="Ningún paso con este filtro"
              emptyDescription="Prueba con otro filtro."
              header={
                <p className="flex items-center gap-2 text-[13px] font-semibold text-ink-soft" aria-live="polite">
                  {loading && <Spinner className="size-3" />}
                  {data.length} {data.length === 1 ? 'paso' : 'pasos'}
                  {data.length >= 200 ? ' (los 200 más recientes)' : ''}
                </p>
              }
            />
          </div>
        )}
      </Card>
    </div>
  )
}
