import Link from 'next/link'
import { Minus, TrendingDown, TrendingUp } from 'lucide-react'
import { formatPercent } from '@/lib/format'

export type MetricGlow = 'mint' | 'lime' | 'rose' | 'fog'
export type MetricTone = 'up' | 'down' | 'warn' | 'neutral'

const GLOW: Record<MetricGlow, string> = {
  mint: '',
  lime: '',
  rose: '',
  fog: '',
}

const PILL: Record<MetricTone, string> = {
  up: 'border-accent bg-raised text-accent-dark',
  down: 'border-bad text-bad',
  warn: 'border-warn text-warn',
  neutral: 'border-line bg-[var(--color-raised)] text-ink-soft',
}

function ToneIcon({ tone }: { tone: MetricTone }) {
  const className = 'size-3 shrink-0'
  if (tone === 'up') return <TrendingUp className={className} aria-hidden />
  if (tone === 'down') return <TrendingDown className={className} aria-hidden />
  if (tone === 'warn') return <Minus className={className} aria-hidden />
  return null
}

export function PercentPill({
  value,
  tone,
  caption,
}: {
  value: number
  tone: MetricTone
  caption?: string
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span
        className={`inline-flex items-center gap-1 text-[12px] font-medium tabular-nums ${PILL[tone]}`}
      >
        <ToneIcon tone={tone} />
        {formatPercent(value)}
      </span>
      {caption ? <span className="text-[12px] leading-4 text-muted">{caption}</span> : null}
    </div>
  )
}

/** KPI: etiqueta a la izquierda, cifra a la derecha; chip de % debajo. Brillo + tooltip al hover. */
export function MetricCard({
  label,
  value,
  percent,
  caption,
  tooltip,
  href,
  glow = 'fog',
  ariaLabel,
}: {
  label: string
  value: string
  percent?: { value: number; tone: MetricTone; caption: string }
  caption?: string
  tooltip?: string
  href?: string
  glow?: MetricGlow
  ariaLabel?: string
}) {
  const inner = (
    <>
      <span
        aria-hidden
        className={`pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100 group-focus-visible:opacity-100 ${GLOW[glow]}`}
      />
      <div className="relative flex items-baseline justify-between gap-3">
        <p className="text-[13px] font-semibold text-ink-soft">{label}</p>
        <p className="text-[28px] font-semibold leading-none tracking-[-0.05em] text-ink tabular-nums">
          {value}
        </p>
      </div>
      <div className="relative mt-2.5">
        {percent ? (
          <PercentPill value={percent.value} tone={percent.tone} caption={percent.caption} />
        ) : caption ? (
          <p className="text-[12px] leading-4 text-muted">{caption}</p>
        ) : null}
      </div>
    </>
  )

  const shell =
    'relative block overflow-hidden border border-line bg-surface px-4 py-3.5 transition duration-200 group-hover:-translate-y-0.5 group-hover:border-line'

  return (
    <div className="group relative z-0 hover:z-20 focus-within:z-20">
      {href ? (
        <Link href={href} aria-label={ariaLabel} className={shell}>
          {inner}
        </Link>
      ) : (
        <div className={shell}>{inner}</div>
      )}
      {tooltip ? (
        <span
          role="tooltip"
          className="pointer-events-none absolute bottom-[calc(100%+8px)] left-1/2 z-30 w-max max-w-[240px] -translate-x-1/2 bg-accent-dark px-3 py-1.5 text-center text-[12px] font-medium leading-snug text-canvas opacity-0 transition duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
        >
          {tooltip}
          <i
            aria-hidden
            className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-ink"
          />
        </span>
      ) : null}
    </div>
  )
}
