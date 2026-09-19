import type { EstadoFichero, PanelResumen, VentanaPasada } from '@/lib/types'
import {
  formatDate,
  formatDateTime,
  formatEur,
  formatNumber,
  formatPercent,
  formatSeconds,
  formatTime,
} from '@/lib/format'
import { Card } from '@/components/ui/Card'
import { MetricCard, type MetricGlow, type MetricTone } from '@/components/dashboard/MetricCard'

const TILES: Array<{
  estado: EstadoFichero
  label: string
  hint: string
  glow: MetricGlow
  tone: MetricTone
}> = [
  { estado: 'PAGAR', label: 'PAGAR', hint: 'Se pagan', glow: 'mint', tone: 'up' },
  { estado: 'ESCALAR', label: 'ESCALAR', hint: 'Los ve una persona', glow: 'lime', tone: 'warn' },
  { estado: 'NO_PAGAR', label: 'NO_PAGAR', hint: 'No se pagan', glow: 'rose', tone: 'down' },
  { estado: 'PENDIENTE', label: 'PENDIENTE', hint: 'Sin decisión vigente', glow: 'fog', tone: 'neutral' },
]

function shareOf(count: number, total: number): number {
  return total > 0 ? (count / total) * 100 : 0
}

/** Coste LLM: 2 decimales salvo importes < 1 céntimo, que si no se ven como 0,00 €. */
function formatCosteLlm(value: number): string {
  const digits = value > 0 && value < 0.01 ? 4 : 2
  return formatEur(value, digits)
}

/** La ventana suele caber en el mismo minuto: no repetir la misma hora a ambos lados. */
function formatVentana(ventana: VentanaPasada): string {
  const resumen = `${formatNumber(ventana.ficheros)} ficheros en ${formatSeconds(ventana.segundos)}`
  if (!ventana.desde || !ventana.hasta) return resumen
  const mismoDia = formatDate(ventana.desde) === formatDate(ventana.hasta)
  const mismaHora = formatDateTime(ventana.desde) === formatDateTime(ventana.hasta)
  if (mismaHora) return `${resumen} · ${formatDateTime(ventana.desde)}`
  if (mismoDia) return `${resumen} · ${formatTime(ventana.desde)} – ${formatTime(ventana.hasta)}`
  return `${resumen} · ${formatDateTime(ventana.desde)} → ${formatDateTime(ventana.hasta)}`
}

function formatRitmo(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '—'
  return value.toFixed(2).replace('.', ',')
}

/** Tarjeta "Ficheros": decisiones vigentes por resultado. Cada casilla abre la cola filtrada. */
export function ProcessingHealth({ panel }: { panel: PanelResumen }) {
  const decididos = panel.ficheros - panel.porEstado.PENDIENTE
  const { operacion } = panel
  const { ventana } = operacion
  /** El histórico sólo se menciona si difiere: lo gastado en runs anteriores no es el coste de esta decisión. */
  const historico =
    operacion.costeEurHistorico !== null && Math.abs(operacion.costeEurHistorico - operacion.costeEur) >= 0.005
      ? operacion.costeEurHistorico
      : null
  const costeTooltip =
    historico === null
      ? operacion.costeEur === 0
        ? 'Extracción vigente a 0 €: plantilla, caché o modelos sin coste marginal.'
        : 'Coste de la extracción vigente: los hechos que deciden hoy.'
      : `Vigente ${formatCosteLlm(operacion.costeEur)}. Histórico ${formatEur(historico, 2)} (runs anteriores y relecturas).`

  const stats: Array<{ label: string; value: string; unit?: string; tooltip: string }> = [
    {
      label: 'Ritmo',
      value: formatRitmo(operacion.ficherosPorSegundo),
      unit: 'ficheros/s',
      tooltip: ventana ? formatVentana(ventana) : 'Velocidad de la última pasada de ingest/extract.',
    },
    {
      label: 'Coste LLM',
      value: formatCosteLlm(operacion.costeEur),
      tooltip: costeTooltip,
    },
    {
      label: 'Con LLM',
      value: operacion.pctLlm === null ? '—' : formatPercent(operacion.pctLlm),
      tooltip: 'Ficheros cuya extracción tocó el LLM (texto o visión). El resto salió de plantilla o caché.',
    },
    {
      label: 'Reintentos',
      value: formatNumber(operacion.reintentos),
      tooltip: 'Eventos con intento > 1: ORA-00600, 429 u otras etapas que tuvieron que repetir.',
    },
  ]
  /** Sólo se enseña el reparto por lote cuando hay más de uno: con la Caja sola el total ya lo dice. */
  const lotes = panel.porLote.length > 1 || panel.porLote.some((lote) => lote.lote !== 1) ? panel.porLote : []

  return (
    <Card className="overflow-visible">
      <div className="flex items-center justify-between gap-4 px-5 pt-5">
        <div>
          <h2 className="text-[17px] font-semibold tracking-[-0.02em]">Ficheros</h2>
          {lotes.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {lotes.map((lote) => (
                <span
                  key={lote.lote}
                  className="text-[12px] text-muted cifra"
                >
                  {lote.lote === 1 ? 'Caja' : `Lote ${lote.lote}`} · {formatNumber(lote.ficheros)}
                </span>
              ))}
            </div>
          )}
        </div>
        <p className="leading-none">
          <span className="text-[34px] font-semibold tracking-[-0.06em] text-[#176d59] tabular-nums">
            {formatNumber(decididos)}
          </span>
          <span className="text-[16px] font-medium text-[#9aa39e] tabular-nums">
            {' '}
            / {formatNumber(panel.ficheros)}
          </span>
        </p>
      </div>

      <div className="px-5 pb-5 pt-4">
        <div className="grid grid-cols-2 gap-3">
          {TILES.map((tile) => {
            const count = panel.porEstado[tile.estado]
            const share = shareOf(count, panel.ficheros)
            const tone = tile.estado === 'PENDIENTE' && count > 0 ? 'warn' : tile.tone
            return (
              <MetricCard
                key={tile.estado}
                href={`/invoices?estado=${tile.estado}`}
                label={tile.label}
                value={formatNumber(count)}
                glow={tile.glow}
                percent={{ value: share, tone, caption: 'del total' }}
                tooltip={`${tile.hint} · ${formatNumber(count)} de ${formatNumber(panel.ficheros)}. Abrir la cola filtrada.`}
                ariaLabel={`${tile.label}: ${formatNumber(count)} ficheros (${formatPercent(share)} del total). Abrir la cola filtrada.`}
              />
            )
          })}
        </div>

        <div className="mt-4 grid grid-cols-2 gap-x-8 gap-y-3 border-t border-[#edf0ec] pt-3.5 sm:grid-cols-4">
          {stats.map((stat) => (
            <div key={stat.label} className="group relative z-0 min-w-0 hover:z-20">
              <p className="text-[12px] text-[#8b9790]">{stat.label}</p>
              <p className="mt-1 flex items-baseline gap-1.5 text-[#17211e]">
                <span className="text-[18px] font-semibold leading-none tracking-[-0.03em] tabular-nums">
                  {stat.value}
                </span>
                {stat.unit ? <span className="text-[12px] text-[#8b9790]">{stat.unit}</span> : null}
              </p>
              <span
                role="tooltip"
                className="pointer-events-none absolute bottom-[calc(100%+8px)] left-0 z-30 w-max max-w-[240px] rounded-[var(--radius-ui)] bg-[#17211e] px-3 py-1.5 text-left text-[12px] font-medium leading-snug text-white opacity-0 transition duration-150 group-hover:opacity-100"
              >
                {stat.tooltip}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  )
}
