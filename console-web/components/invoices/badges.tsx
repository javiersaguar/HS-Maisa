import type { Aviso, EstadoEvento, EstadoFichero } from '@/lib/types'
import { AVISO_LABELS, ESTADO_EVENTO_LABELS } from '@/lib/format'
import { estadoTone, eventoTone } from '@/lib/theme'
import { StatusBadge } from '@/components/ui/StatusBadge'

/** Resultado vigente de la norma (`PAGAR | NO_PAGAR | ESCALAR`) o `PENDIENTE` sin decisión. */
export function ResultadoBadge({ estado }: { estado: EstadoFichero | null; withIcon?: boolean }) {
  if (!estado) return <span className="text-faint">—</span>
  return <StatusBadge tone={estadoTone(estado)}>{estado}</StatusBadge>
}

export function EventoBadge({ estado }: { estado: EstadoEvento }) {
  return <StatusBadge tone={eventoTone(estado)}>{ESTADO_EVENTO_LABELS[estado]}</StatusBadge>
}

/** Señal de extract/validate. No es una decisión: texto con un borde fino, nada de relleno. */
export function AvisoChip({ aviso }: { aviso: Aviso }) {
  const grave = aviso === 'texto_instruccion'
  return (
    <span
      title={aviso}
      className={`inline-flex items-center rounded-[var(--radius-ui)] border px-1.5 py-0.5 text-[12px] ${
        grave ? 'border-warn/40 text-warn' : 'border-line text-muted'
      }`}
    >
      {AVISO_LABELS[aviso]}
    </span>
  )
}
