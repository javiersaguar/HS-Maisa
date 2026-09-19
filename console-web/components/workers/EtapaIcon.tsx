import { Database, FileInput, Scale, ScanText, Send, ShieldCheck } from 'lucide-react'
import type { Etapa, EtapaResumen } from '@/lib/types'
import { ETAPA_GRANO } from '@/lib/format'
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

function coberturaEtapa(etapa: EtapaResumen, ficheros: number): number | null {
  const grano = ETAPA_GRANO[etapa.etapa]
  if (grano !== 'fichero') {
    const relevantes = etapa.porEstado.ok + etapa.porEstado.error + etapa.porEstado.pendiente
    if (!relevantes) return 100
    return Math.round((etapa.porEstado.ok / relevantes) * 1000) / 10
  }
  if (!ficheros) return null
  if (etapa.etapa === 'emit' && etapa.ficherosOk === 0 && etapa.porEstado.ok > 0) {
    return etapa.porEstado.error > 0 || etapa.porEstado.pendiente > 0 ? null : 100
  }
  return Math.round((etapa.ficherosOk / ficheros) * 1000) / 10
}

/**
 * Salud de una etapa a partir de sus eventos. ingest/extract/decide se miden
 * contra los ficheros; validate y enrich no (duplicados y peticiones ERP).
 * Los reintentos superados no son un problema; lo que queda en `error` o
 * `pendiente`, sí.
 */
export function saludEtapa(
  etapa: EtapaResumen,
  ficheros: number,
): { label: string; tone: Tone; cobertura: number | null } {
  const grano = ETAPA_GRANO[etapa.etapa]
  if (etapa.eventos === 0) {
    // emit no anota fichero hasta `package`; si la norma ya cubre la Caja, la etapa está lista.
    if (etapa.etapa === 'emit') {
      const lista = ficheros > 0
      return { label: lista ? 'Al día' : 'Sin empaquetar', tone: lista ? 'green' : 'gray', cobertura: lista ? 100 : null }
    }
    if (grano === 'cambio') return { label: 'Sin cambios', tone: 'green', cobertura: 100 }
    return { label: 'Sin eventos', tone: 'gray', cobertura: grano === 'fichero' && ficheros ? 0 : null }
  }

  const cobertura = coberturaEtapa(etapa, ficheros)
  if (etapa.porEstado.error > 0) return { label: 'Con errores', tone: 'red', cobertura }
  if (etapa.porEstado.pendiente > 0) return { label: 'Con pendientes', tone: 'yellow', cobertura }
  return { label: 'Al día', tone: 'green', cobertura }
}

/** Errores o pendientes: un anillo gris o "sin cambios" no es una incidencia. */
export function etapaConIncidencia(etapa: EtapaResumen, ficheros: number): boolean {
  const { tone } = saludEtapa(etapa, ficheros)
  return tone === 'red' || tone === 'yellow'
}
