import type { Aviso, EstadoEvento, EstadoFichero } from '@/lib/types'
import { AVISO_LABELS, ESTADO_EVENTO_LABELS } from '@/lib/format'
import { estadoTone, eventoTone } from '@/lib/theme'
import { StatusBadge } from '@/components/ui/StatusBadge'

const PREFIX: Record<EstadoFichero, string> = {
  PAGAR: '✓ ',
  ESCALAR: '! ',
  NO_PAGAR: '× ',
  PENDIENTE: '◷ ',
}

/** Resultado vigente de la norma (`PAGAR | NO_PAGAR | ESCALAR`) o `PENDIENTE` sin decisión. */
export function ResultadoBadge({ estado, withIcon = true }: { estado: EstadoFichero | null; withIcon?: boolean }) {
  if (!estado) return <span className="text-muted">—</span>
  return (
    <StatusBadge tone={estadoTone(estado)}>
      {withIcon ? PREFIX[estado] : ''}
      {estado}
    </StatusBadge>
  )
}

export function EventoBadge({ estado }: { estado: EstadoEvento }) {
  return (
    <StatusBadge tone={eventoTone(estado)}>
      {estado === 'retry' && <span className="mr-1.5 size-1.5 animate-pulse rounded-full bg-current" />}
      {ESTADO_EVENTO_LABELS[estado]}
    </StatusBadge>
  )
}

/** Señal de extract/validate. No es una decisión: se pinta neutra salvo el texto que instruye. */
export function AvisoChip({ aviso }: { aviso: Aviso }) {
  const grave = aviso === 'texto_instruccion'
  return (
    <span
      title={aviso}
      className={`inline-flex items-center border px-1.5 py-0.5 text-[11px] ${grave ? 'border-warn-line bg-warn-soft text-warn' : 'border-line bg-canvas text-ink-soft'}`}
    >
      {AVISO_LABELS[aviso]}
    </span>
  )
}
