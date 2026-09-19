import type { ReactNode } from 'react'
import type { Tone } from '@/lib/theme'

/**
 * Estado como punto de color y texto. Sin fondo, sin borde y sin forma ovalada: el color es la
 * señal y el texto la dice; el resto era decoración.
 */
const PUNTO: Record<Tone, string> = {
  green: 'bg-ok',
  yellow: 'bg-warn',
  red: 'bg-bad',
  gray: 'bg-faint',
}

const TEXTO: Record<Tone, string> = {
  green: 'text-ok',
  yellow: 'text-warn',
  red: 'text-bad',
  gray: 'text-muted',
}

export function StatusBadge({
  children,
  tone = 'green',
  className = '',
}: {
  children: ReactNode
  tone?: Tone
  className?: string
}) {
  return (
    <span className={`inline-flex items-center gap-2 text-[13px] font-medium ${TEXTO[tone]} ${className}`}>
      <span aria-hidden className={`size-2 shrink-0 rounded-full ${PUNTO[tone]}`} />
      {children}
    </span>
  )
}
