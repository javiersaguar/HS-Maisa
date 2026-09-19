import Link from 'next/link'
import type { EstadoFichero, PanelResumen } from '@/lib/types'
import { ERP_NOMBRE } from '@/lib/config'
import { formatDateTime, formatEur, formatNumber, formatPercent, formatSeconds, shortHash } from '@/lib/format'
import { Card } from '@/components/ui/Card'

const TILES: Array<{
  estado: EstadoFichero
  label: string
  icon: string
  pill: string
  border: string
  iconClass: string
  valueClass: string
  labelClass: string
  shadow: string
}> = [
  {
    estado: 'PAGAR',
    label: 'Se pagan',
    icon: '✓',
    pill: 'PAGAR',
    border: 'border-[#dcefe6]',
    iconClass: 'bg-[#e4f8ef] text-[#16825f]',
    valueClass: 'text-[#176e5a]',
    labelClass: 'text-[#415f55]',
    shadow: 'shadow-[0_5px_18px_rgba(30,80,60,0.05)]',
  },
  {
    estado: 'ESCALAR',
    label: 'Los ve una persona',
    icon: '!',
    pill: 'ESCALAR',
    border: 'border-[#eee8bd]',
    iconClass: 'bg-[#fff6c9] text-[#a08400]',
    valueClass: 'text-[#927b00]',
    labelClass: 'text-[#5f5b2e]',
    shadow: 'shadow-[0_5px_18px_rgba(130,120,30,0.04)]',
  },
  {
    estado: 'NO_PAGAR',
    label: 'No se pagan',
    icon: '×',
    pill: 'NO_PAGAR',
    border: 'border-[#f1dada]',
    iconClass: 'bg-[#fff0f0] text-[#c94343]',
    valueClass: 'text-[#bd3434]',
    labelClass: 'text-[#713d3d]',
    shadow: 'shadow-[0_5px_18px_rgba(150,50,50,0.04)]',
  },
  {
    estado: 'PENDIENTE',
    label: 'Sin decisión vigente',
    icon: '◷',
    pill: 'PENDIENTE',
    border: 'border-[#e3e9e5]',
    iconClass: 'bg-[#eef3f1] text-[#315d53]',
    valueClass: 'text-[#164f45]',
    labelClass: 'text-[#415f55]',
    shadow: 'shadow-[0_5px_18px_rgba(30,80,60,0.04)]',
  },
]

/** Tarjeta "Ficheros": decisiones vigentes por resultado. Cada casilla abre la cola filtrada. */
export function ProcessingHealth({ panel }: { panel: PanelResumen }) {
  const decididos = panel.ficheros - panel.porEstado.PENDIENTE
  const { operacion, versiones } = panel
  const { ventana } = operacion
  /** El histórico sólo se menciona si difiere: lo gastado en runs anteriores no es el coste de esta decisión. */
  const historico =
    operacion.costeEurHistorico !== null && Math.abs(operacion.costeEurHistorico - operacion.costeEur) >= 0.005
      ? operacion.costeEurHistorico
      : null
  const stats: Array<{ label: string; value: string; hint: string; title?: string }> = [
    {
      label: 'Ritmo',
      value:
        operacion.ficherosPorSegundo === null ? '—' : `${String(operacion.ficherosPorSegundo).replace('.', ',')} ficheros/s`,
      hint: ventana
        ? `${formatNumber(ventana.ficheros)} ficheros en ${formatSeconds(ventana.segundos)} (última pasada)`
        : 'velocidad de la última pasada',
      title: ventana ? `Ingest/extract desde ${formatDateTime(ventana.desde)} hasta ${formatDateTime(ventana.hasta)}` : undefined,
    },
    {
      label: 'Coste LLM',
      value: formatEur(operacion.costeEur, 2),
      hint: historico === null ? 'extracción vigente' : `extracción vigente · ${formatEur(historico, 2)} acumulado`,
      title: historico === null ? undefined : 'El acumulado incluye runs anteriores y relecturas; no es el coste de las decisiones de hoy.',
    },
    { label: 'Con LLM', value: formatPercent(operacion.pctLlm), hint: 'el resto salió de plantilla o caché' },
    { label: 'Reintentos', value: formatNumber(operacion.reintentos), hint: 'ERP u otras etapas que tuvieron que repetir' },
  ]
  /** Sólo se enseña el reparto por lote cuando hay más de uno: con la Caja sola el total ya lo dice. */
  const lotes = panel.porLote.length > 1 || panel.porLote.some((lote) => lote.lote !== 1) ? panel.porLote : []
  /** Si conviven dos normas (v3 y v4 el sábado), el chip lo dice y el tooltip reparte. */
  const normas = versiones.normas.length > 1 ? versiones.normas : []
  const versionChips: Array<{ label: string; title?: string }> = [
    {
      label: normas.length ? `Norma ${normas.map((item) => item.norma).join(' + ')}` : `Norma ${versiones.norma ?? '—'}`,
      title: normas.length ? normas.map((item) => `${item.norma}: ${formatNumber(item.ficheros)} ficheros`).join(' · ') : undefined,
    },
    { label: 'Excel proveedores', title: `Maestro ${shortHash(versiones.maestro, 12)}` },
    { label: `${ERP_NOMBRE} · ${versiones.erp ?? '—'}` },
  ]

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-[#e5e8e3] bg-[#fbfcfa] px-5 py-4">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-[17px] font-semibold tracking-[-0.015em]">Ficheros</h2>
          <div className="flex items-center gap-4">
            {lotes.length > 0 && (
              <div className="hidden flex-wrap justify-end gap-1.5 sm:flex">
                {lotes.map((lote) => (
                  <span
                    key={lote.lote}
                    className="rounded-full border border-[#e1e7e2] bg-white px-2 py-0.5 text-[12px] text-[#68736d] tabular-nums"
                  >
                    {lote.lote === 1 ? 'Caja' : `Lote ${lote.lote} ·`} {formatNumber(lote.ficheros)}
                  </span>
                ))}
              </div>
            )}
            <div className="text-right">
              <p className="text-[30px] font-bold leading-none tracking-[-0.06em] tabular-nums">
                {formatNumber(decididos)}
                <span className="text-[18px] text-[#9aa39e]">/{formatNumber(panel.ficheros)}</span>
              </p>
              <p className="mt-1 text-[12px] text-[#89928c]">con decisión vigente</p>
            </div>
          </div>
        </div>
      </div>
      <div className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-[13px] font-semibold text-[#64736b]">Resultado de la norma</p>
          <div className="flex flex-wrap gap-1.5">
            {versionChips.map((chip) => (
              <span
                key={chip.label}
                title={chip.title}
                className="rounded-md bg-[#f3f5f1] px-1.5 py-0.5 text-[12px] text-[#68736d]"
              >
                {chip.label}
              </span>
            ))}
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3">
          {TILES.map((tile) => (
            <Link
              key={tile.estado}
              href={`/invoices?estado=${tile.estado}`}
              aria-label={`${tile.pill}: ${panel.porEstado[tile.estado]} ficheros. Abrir la cola filtrada.`}
              className={`rounded-2xl border ${tile.border} bg-white p-4 ${tile.shadow} transition hover:-translate-y-0.5 hover:shadow-[0_10px_24px_rgba(30,80,60,0.09)] active:translate-y-0`}
            >
              <div className="flex items-center gap-3">
                <span className={`flex size-8 shrink-0 items-center justify-center rounded-xl ${tile.iconClass}`}>
                  {tile.icon}
                </span>
                <p
                  className={`min-w-0 flex-1 truncate text-[20px] font-bold leading-none tracking-[-0.04em] tabular-nums transition-colors ${tile.valueClass}`}
                >
                  {formatNumber(panel.porEstado[tile.estado])}
                </p>
                <span className={`shrink-0 rounded-full px-2 py-1 font-mono text-[11px] font-semibold ${tile.iconClass}`}>
                  {tile.pill}
                </span>
              </div>
              <p className={`mt-3 text-[13px] font-semibold ${tile.labelClass}`}>{tile.label}</p>
            </Link>
          ))}
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 border-t border-[#edf0ec] pt-4 sm:grid-cols-4">
          {stats.map((stat) => (
            <div key={stat.label} className="min-w-0" title={stat.title}>
              <p className="text-[12px] text-[#8b9790]">{stat.label}</p>
              <p className="mt-0.5 text-[16px] font-bold tracking-[-0.03em] text-[#233f35] tabular-nums">{stat.value}</p>
              <p className="mt-0.5 text-[12px] leading-4 text-[#9aa39e]">{stat.hint}</p>
            </div>
          ))}
        </div>
      </div>
    </Card>
  )
}
