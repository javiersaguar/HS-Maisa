import Link from 'next/link'
import { Minus, TrendingDown, TrendingUp } from 'lucide-react'
import { formatPercent } from '@/lib/format'

export type MetricGlow = 'mint' | 'lime' | 'rose' | 'fog'
export type MetricTone = 'up' | 'down' | 'warn' | 'neutral'

const GLOW: Record<MetricGlow, string> = {
  mint: 'bg-[radial-gradient(120%_90%_at_100%_0%,rgba(214,245,42,0.42),rgba(103,212,173,0.16)_42%,transparent_72%)]',
  lime: 'bg-[radial-gradient(120%_90%_at_100%_0%,rgba(214,245,42,0.55),rgba(255,246,201,0.4)_45%,transparent_72%)]',
  rose: 'bg-[radial-gradient(120%_90%_at_100%_0%,rgba(240,91,91,0.22),rgba(255,240,240,0.6)_45%,transparent_72%)]',
  fog: 'bg-[radial-gradient(120%_90%_at_100%_0%,rgba(103,212,173,0.2),rgba(247,248,245,0.85)_45%,transparent_72%)]',
}

const PILL: Record<MetricTone, string> = {
  up: 'border-[#b7e8d2] bg-[#eefbf5] text-[#176d59]',
  down: 'border-[#f1c4c4] text-[#bd3434]',
  warn: 'border-[#e8d36a] text-[#8a7400]',
  neutral: 'border-[#e1e7e2] bg-[var(--color-raised)] text-[#5a655f]',
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
      {caption ? <span className="text-[12px] leading-4 text-[#8b9790]">{caption}</span> : null}
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
        className={`pointer-events-none absolute inset-0 rounded-[inherit] opacity-0 transition-opacity duration-300 group-hover:opacity-100 group-focus-visible:opacity-100 ${GLOW[glow]}`}
      />
      <div className="relative flex items-baseline justify-between gap-3">
        <p className="text-[13px] font-semibold text-[#5a655f]">{label}</p>
        <p className="text-[28px] font-semibold leading-none tracking-[-0.05em] text-[#17211e] tabular-nums">
          {value}
        </p>
      </div>
      <div className="relative mt-2.5">
        {percent ? (
          <PercentPill value={percent.value} tone={percent.tone} caption={percent.caption} />
        ) : caption ? (
          <p className="text-[12px] leading-4 text-[#8b9790]">{caption}</p>
        ) : null}
      </div>
    </>
  )

  const shell =
    'relative block overflow-hidden rounded-[var(--radius-card)] border border-[#e6ebe6] bg-white px-4 py-3.5 transition duration-200 group-hover:-translate-y-0.5 group-hover:border-[#d5e2da] group-hover:'

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
          className="pointer-events-none absolute bottom-[calc(100%+8px)] left-1/2 z-30 w-max max-w-[240px] -translate-x-1/2 rounded-[var(--radius-ui)] bg-[#17211e] px-3 py-1.5 text-center text-[12px] font-medium leading-snug text-white opacity-0 transition duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
        >
          {tooltip}
          <i
            aria-hidden
            className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-[#17211e]"
          />
        </span>
      ) : null}
    </div>
  )
}
