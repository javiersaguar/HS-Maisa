import type { ReactNode } from 'react'
import type { Tone } from '@/lib/theme'

const TONES: Record<Tone, string> = {
  green: 'bg-[#edf9f4] text-[#087b5b]',
  yellow: 'bg-[#fff9e6] text-[#a87000]',
  red: 'bg-[#fff0f0] text-[#bd3434]',
  gray: 'bg-[#f3f4f1] text-[#8a918c]',
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
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[13px] font-medium ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  )
}
