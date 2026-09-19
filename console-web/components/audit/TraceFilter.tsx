'use client'

import type { CategoriaTraza } from '@/lib/types'
import { ETAPAS, ETAPA_LABELS } from '@/lib/format'
import { Select } from '@/components/ui/Select'

const OPTIONS: Array<{ value: CategoriaTraza | 'all'; label: string }> = [
  { value: 'all', label: 'Todos los pasos' },
  { value: 'norma', label: 'Reglas de la norma' },
  { value: 'incidencias', label: 'Incidencias (reintentos, errores, pendientes)' },
  ...ETAPAS.map((etapa) => ({ value: etapa, label: `Etapa · ${ETAPA_LABELS[etapa]}` })),
]

export function TraceFilter({
  value,
  onChange,
}: {
  value: CategoriaTraza | 'all'
  onChange: (value: CategoriaTraza | 'all') => void
}) {
  return (
    <Select
      aria-label="Filtrar la traza"
      value={value}
      onChange={onChange}
      options={OPTIONS}
      className="min-w-[240px] text-[13px]"
    />
  )
}
