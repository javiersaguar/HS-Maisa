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
  if (!estado) return <span className="text-[#a1aaa5]">—</span>
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
      className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[11px] ${grave ? 'border-[#eee8bd] bg-[#fff9e6] text-[#a87000]' : 'border-[#e1e5df] bg-[#f7f8f5] text-[#68736d]'}`}
    >
      {AVISO_LABELS[aviso]}
    </span>
  )
}
