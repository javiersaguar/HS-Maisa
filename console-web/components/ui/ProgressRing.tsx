'use client'

import { useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Info } from 'lucide-react'
import { COLORS, progressColor } from '@/lib/theme'

/** Half-ring gauge used on worker cards and the dashboard pipeline. Fills from 0 on mount. */
export function ProgressRing({ value, tooltip }: { value: number | null; tooltip?: string }) {
  const [shown, setShown] = useState<number | null>(null)
  const [tip, setTip] = useState<{ top: number; left: number; side: 'left' | 'right' } | null>(null)
  const ref = useRef<HTMLDivElement>(null)
  const tipId = useId()

  useEffect(() => {
    const frame = requestAnimationFrame(() => setShown(value))
    return () => cancelAnimationFrame(frame)
  }, [value])

  const place = () => {
    const box = ref.current?.getBoundingClientRect()
    if (!box || !tooltip) return
    const showLeft = box.left >= 280
    setTip({
      top: box.top + box.height / 2,
      left: showLeft ? box.left - 10 : box.right + 10,
      side: showLeft ? 'left' : 'right',
    })
  }

  const active = value !== null && value > 0
  const color = progressColor(value)
  const label = tooltip ?? (active ? `${Math.round(value)}% de cobertura` : 'Sin cobertura')

  return (
    <div
      ref={ref}
      className="group/ring relative h-[76px] w-[116px] shrink-0"
      role="img"
      aria-label={label}
      aria-describedby={tooltip ? tipId : undefined}
      onMouseEnter={place}
      onMouseLeave={() => setTip(null)}
    >
      {tooltip ? (
        <Info
          aria-hidden
          className="absolute right-0.5 top-0 size-3.5 text-[#9aa39e] transition-colors duration-150 group-hover/ring:text-[#176d59]"
        />
      ) : null}
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
      {tooltip && tip
        ? createPortal(
            <span
              id={tipId}
              role="tooltip"
              className={`pointer-events-none fixed z-[80] w-max max-w-[260px] -translate-y-1/2 bg-[#17211e] px-3 py-1.5 text-left text-[12px] font-medium leading-snug text-white ${
                tip.side === 'left' ? '-translate-x-full' : ''
              }`}
              style={{ top: tip.top, left: tip.left }}
            >
              {tooltip}
              <i
                aria-hidden
                className={`absolute top-1/2 -translate-y-1/2 border-4 border-transparent ${
                  tip.side === 'left' ? 'left-full border-l-[#17211e]' : 'right-full border-r-[#17211e]'
                }`}
              />
            </span>,
            document.body,
          )
        : null}
    </div>
  )
}
