'use client'

import { useEffect, useState } from 'react'
import { COLORS, progressColor } from '@/lib/theme'

/** Half-ring gauge used on worker cards and the dashboard pipeline. Fills from 0 on mount. */
export function ProgressRing({ value }: { value: number | null }) {
  const [shown, setShown] = useState<number | null>(null)

  useEffect(() => {
    const frame = requestAnimationFrame(() => setShown(value))
    return () => cancelAnimationFrame(frame)
  }, [value])

  const active = value !== null && value > 0
  const color = progressColor(value)
  return (
    <div
      className="relative h-[76px] w-[116px] shrink-0"
      role="img"
      aria-label={active ? `${Math.round(value)}% complete` : 'Waiting'}
    >
      <svg className="h-full w-full" viewBox="0 0 116 76" aria-hidden="true">
        <path
          d="M 10 64 A 48 48 0 0 1 106 64"
          fill="none"
          stroke={COLORS.track}
          strokeWidth="10"
          strokeLinecap="round"
        />
        {active && (
          <path
            d="M 10 64 A 48 48 0 0 1 106 64"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            pathLength="100"
            strokeDasharray="100"
            strokeDashoffset={100 - (shown ?? 0)}
            className="transition-[stroke-dashoffset,stroke] duration-700 ease-out"
          />
        )}
      </svg>
      <span
        className="absolute inset-x-0 bottom-0 text-center text-[18px] font-bold tracking-[-0.04em] transition-colors duration-500"
        style={{ color }}
      >
        {active ? `${Math.round(value)}%` : '—'}
      </span>
    </div>
  )
}
