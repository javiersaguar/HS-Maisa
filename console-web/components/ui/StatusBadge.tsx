import type { ReactNode } from 'react'
import type { Tone } from '@/lib/theme'

const TONES: Record<Tone, string> = {
  green: 'bg-accent-soft text-accent-dark',
  yellow: 'bg-warn-soft text-warn',
  red: 'bg-bad-soft text-bad',
  gray: 'bg-raised text-muted',
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
    <span
      className={`inline-flex items-center px-2 py-0.5 text-[13px] font-medium ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  )
}
