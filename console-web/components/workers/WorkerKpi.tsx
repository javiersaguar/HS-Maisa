import type { ReactNode } from 'react'
import { Card } from '@/components/ui/Card'

/**
 * KPI tile for the worker detail header. Same language as the tiles on
 * /workers: tinted icon, large number, label, and one line of context.
 */
export function WorkerKpi({
  icon,
  label,
  value,
  color,
  tint,
  children,
}: {
  icon: ReactNode
  label: string
  value: ReactNode
  color: string
  tint: string
  /** Extra context under the label: a live dot, a bar, a unit. */
  children?: ReactNode
}) {
  return (
    <Card className="border-line bg-surface p-4">
      <div className="flex items-center justify-between gap-3">
        <span
          className="flex size-9 shrink-0 items-center justify-center text-[16px] font-semibold"
          style={{ color, backgroundColor: tint }}
        >
          {icon}
        </span>
        <p className="text-[24px] font-bold leading-none tracking-[-0.05em] tabular-nums" style={{ color }}>
          {value}
        </p>
      </div>
      <h3 className="mt-3 text-[14px] font-semibold text-ink">{label}</h3>
      {children && <div className="mt-1.5 text-[13px] text-muted">{children}</div>}
    </Card>
  )
}
