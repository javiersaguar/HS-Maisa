import type { Resultado, ResultadoShare } from '@/lib/types'
import { COLORS } from '@/lib/theme'
import { Card } from '@/components/ui/Card'

const RESULTADO_COLORS: Record<Resultado, string> = {
  PAGAR: COLORS.mint,
  NO_PAGAR: COLORS.primary,
  ESCALAR: COLORS.lime,
}

/** Reparto de las decisiones vigentes. Los PENDIENTE no tienen decisión y no entran. */
export function DecisionDistribution({ shares }: { shares: ResultadoShare[] }) {
  let cursor = 0
  const stops = shares
    .map((share) => {
      const start = cursor
      cursor += share.percent
      return `${RESULTADO_COLORS[share.resultado]} ${start}% ${cursor}%`
    })
    .join(', ')

  return (
    <Card className="p-5">
      <h2 className="text-[16px] font-semibold tracking-[-0.01em]">Decisiones vigentes</h2>
      <div className="mt-4 flex items-center gap-6">
        <div
          role="img"
          aria-label={shares.map((share) => `${share.resultado} ${share.percent} %`).join(', ')}
          className="relative size-[98px] shrink-0 rounded-full animate-in fade-in zoom-in-90 duration-500"
          style={{ background: stops ? `conic-gradient(${stops})` : COLORS.track }}
        >
          <div className="absolute inset-[16px] rounded-full bg-white" />
        </div>
        <div className="flex-1 space-y-3 text-[13px]">
          {shares.map((share) => (
            <div key={share.resultado}>
              <div className="flex justify-between">
                <span className="flex items-center gap-2 font-mono text-[#5a655f]">
                  <i className="size-2 rounded-full" style={{ backgroundColor: RESULTADO_COLORS[share.resultado] }} />
                  {share.resultado}
                </span>
                <span>
                  <b>{share.percent}%</b>
                  <span className="ml-2 text-[#9aa39e] tabular-nums">{share.count}</span>
                </span>
              </div>
              <div className="mt-1 h-1 rounded-full bg-[#e4e6df]">
                <div
                  className="h-full rounded-full transition-[width] duration-700 ease-out"
                  style={{ width: `${share.percent}%`, backgroundColor: RESULTADO_COLORS[share.resultado] }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  )
}
