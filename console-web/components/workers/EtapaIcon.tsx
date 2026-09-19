import { Database, FileInput, Scale, ScanText, Send, ShieldCheck } from 'lucide-react'
import type { Etapa, EtapaResumen } from '@/lib/types'
import type { Tone } from '@/lib/theme'

const ICONS: Record<Etapa, typeof FileInput> = {
  ingest: FileInput,
  extract: ScanText,
  validate: ShieldCheck,
  enrich: Database,
  decide: Scale,
  emit: Send,
}

export function EtapaIcon({ etapa, className = 'size-5' }: { etapa: Etapa; className?: string }) {
  const Icon = ICONS[etapa]
  return <Icon className={className} />
}

/**
 * Salud de una etapa a partir de sus eventos. Los reintentos superados no son un problema
 * (se cuentan aparte); lo que queda en `error` o `pendiente`, sí.
 */
export function saludEtapa(etapa: EtapaResumen, ficheros: number): { label: string; tone: Tone; cobertura: number | null } {
  const cobertura = ficheros ? Math.round((etapa.ficherosOk / ficheros) * 1000) / 10 : null
  if (etapa.eventos === 0) return { label: 'Sin eventos', tone: 'gray', cobertura }
  if (etapa.porEstado.error > 0) return { label: 'Con errores', tone: 'red', cobertura }
  if (etapa.porEstado.pendiente > 0) return { label: 'Con pendientes', tone: 'yellow', cobertura }
  return { label: 'Al día', tone: 'green', cobertura }
}
