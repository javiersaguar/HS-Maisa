'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Activity, Database, FileText, FlaskConical, LayoutDashboard, Sparkles, Workflow } from 'lucide-react'
import { BRAND, USE_MOCK } from '@/lib/config'
import { ORIGEN_DATOS } from '@/lib/api/salud'
import type { Etapa } from '@/lib/types'
import { formatNumber, formatRelative } from '@/lib/format'
import { useEtapas } from '@/hooks/useEtapas'
import { useSalud } from '@/hooks/useSalud'
import { etapaConIncidencia, saludEtapa } from '@/components/workers/EtapaIcon'

const ITEMS = [
  { label: 'Panel', href: '/', icon: LayoutDashboard },
  { label: 'Ficheros', href: '/invoices', icon: FileText },
  { label: 'Etapas', href: '/workers', icon: Workflow },
  { label: 'Traza', href: '/audit', icon: Activity },
] as const

function isActive(pathname: string, href: string) {
  if (href === '/') return pathname === '/'
  return pathname === href || pathname.startsWith(`${href}/`)
}

function listarNombres(nombres: string[]): string {
  if (nombres.length <= 1) return nombres[0] ?? ''
  if (nombres.length === 2) return `${nombres[0]} y ${nombres[1]}`
  return `${nombres.slice(0, -1).join(', ')} y ${nombres[nombres.length - 1]}`
}

/** Nombres de etapa en minúscula, para caber en una frase del pie. */
const ETAPA_EN_FRASE: Record<Etapa, string> = {
  ingest: 'ingesta',
  extract: 'extracción',
  validate: 'validación',
  enrich: 'maestro y ERP',
  decide: 'la norma',
  emit: 'entrega',
}

/**
 * De dónde salen los datos. Se enseña siempre: en la defensa nadie debe confundir el mock con la Caja.
 *  - mock: datos de ejemplo (`NEXT_PUBLIC_USE_MOCK=true`).
 *  - http: Caja de Alberto, puente sin Caja (503) o sin conexión (red).
 */
function OrigenDatos() {
  const { data, error } = useSalud({ live: !USE_MOCK })

  if (USE_MOCK) {
    return (
      <div
        title="NEXT_PUBLIC_USE_MOCK=true: 510 ficheros inventados. No es la Caja."
        className="rounded-lg border border-[#eee8bd] bg-[#fffbe8] px-2.5 py-1.5 text-[12px] text-[#8a7400]"
      >
        <div className="flex items-center gap-2 font-semibold">
          <FlaskConical className="size-3.5 shrink-0" />
          Datos de ejemplo
        </div>
        <p className="mt-0.5 pl-[22px] font-medium opacity-80">No es la Caja</p>
      </div>
    )
  }

  const bd = data?.bd ?? null
  const tone = error
    ? 'border-[#f1dada] bg-[#fff0f0] text-[#bd3434]'
    : !data
      ? 'border-[#e1e7e2] bg-[#f7f8f5] text-[#8a958e]'
      : bd
        ? 'border-[#dcefe6] bg-[#eff8f3] text-[#176d59]'
        : 'border-[#f1dada] bg-[#fff0f0] text-[#bd3434]'
  const label = error ? 'Sin conexión' : !data ? 'Conectando…' : bd ? 'Caja de Alberto' : 'Aún no hay Caja'
  const detail = error
    ? 'El puente no responde'
    : !data
      ? 'Comprobando la Caja…'
      : bd
        ? bd.pendientes
          ? `${formatNumber(bd.ficheros)} facturas · ${formatNumber(bd.pendientes)} sin decidir`
          : `${formatNumber(bd.ficheros)} facturas`
        : 'Falta ingest de la Caja'
  const title = error
    ? `${error.message}. Arranca: uv run python -m albertitos.console.api`
    : bd
      ? `${ORIGEN_DATOS} · último evento ${formatRelative(bd.ultimoEventoEn)}${bd.identidades ? ' · identidades (mismo PDF, dos nombres)' : ''}`
      : ORIGEN_DATOS

  return (
    <div title={title} className={`rounded-lg border px-2.5 py-1.5 text-[12px] ${tone}`}>
      <div className="flex items-center gap-2 font-semibold">
        <Database className="size-3.5 shrink-0" />
        {label}
      </div>
      <p className="mt-0.5 truncate pl-[22px] font-medium opacity-80">{detail}</p>
    </div>
  )
}

function EstadoPipeline() {
  const { data, error } = useEtapas({ live: true })
  const etapas = data?.etapas ?? []
  const ficheros = data?.ficheros ?? 0
  const conAvisos = etapas.filter((etapa) => etapaConIncidencia(etapa, ficheros))
  const sinCorrer = etapas.length > 0 && etapas.every((etapa) => saludEtapa(etapa, ficheros).tone === 'gray')
  const ultimo = data?.recientes.find((evento) => evento.ts)?.ts ?? null

  let titulo: string
  let detalle: string
  let tone: 'red' | 'pulse' | 'yellow' | 'green' = 'green'
  if (error) {
    titulo = 'No llegan los eventos'
    detalle = 'Reintentando en segundo plano'
    tone = 'red'
  } else if (!data) {
    titulo = 'Conectando…'
    detalle = 'Leyendo el pipeline'
    tone = 'pulse'
  } else if (conAvisos.length > 0) {
    const nombres = conAvisos.map((etapa) => ETAPA_EN_FRASE[etapa.etapa])
    titulo = `Mirar ${listarNombres(nombres)}`
    detalle = ultimo ? `Última actividad ${formatRelative(ultimo)}` : 'Ábrelo en Etapas'
    tone = 'yellow'
  } else if (sinCorrer) {
    titulo = 'Aún no ha corrido'
    detalle = 'El pipeline no ha dejado eventos'
    tone = 'yellow'
  } else {
    titulo = 'Etapas al día'
    detalle = ultimo ? `Última actividad ${formatRelative(ultimo)}` : 'Las seis etapas, sin avisos'
    tone = 'green'
  }

  const irAEtapas = Boolean(data && !error && (conAvisos.length > 0 || sinCorrer))

  const dot =
    tone === 'red'
      ? 'bg-[#f05b5b]'
      : tone === 'pulse'
        ? 'animate-pulse bg-[#c9cec9]'
        : tone === 'yellow'
          ? 'bg-[#e0c95a]'
          : 'bg-[#63d5aa]'

  const inner = (
    <>
      <div className="flex items-center gap-2 text-[14px] font-medium text-[#46504b]">
        <span className={`size-2 rounded-full transition-colors ${dot}`} />
        {titulo}
      </div>
      <p className="mt-1 pl-4 text-[13px] text-[#a0a6a2]">{detalle}</p>
    </>
  )

  if (irAEtapas) {
    return (
      <Link href="/workers" className="rounded-lg outline-none hover:text-[#164f45] focus-visible:ring-2 focus-visible:ring-[#164f45]/30">
        {inner}
      </Link>
    )
  }

  return <div>{inner}</div>
}

export function Sidebar() {
  const pathname = usePathname() ?? '/'

  return (
    <aside className="flex h-full w-[220px] shrink-0 flex-col overflow-hidden rounded-[28px] border border-[#e2e5df] bg-white shadow-[0_8px_24px_rgba(20,55,45,0.06)]">
      <Link href="/" className="flex h-[84px] shrink-0 items-center gap-3 border-b border-[#e2e5df] px-5">
        <div className="flex size-8 items-center justify-center rounded-lg bg-[#155247] text-white">
          <Sparkles className="size-4" />
        </div>
        <div>
          <p className="text-[14px] font-semibold tracking-tight text-[#17211e]">{BRAND}</p>
          <p className="text-[14px] text-[#9aa39e]">Cuentas a pagar</p>
        </div>
      </Link>

      <nav className="flex min-h-0 flex-col gap-1 overflow-y-auto px-3 py-3">
        {ITEMS.map(({ label, href, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            aria-current={isActive(pathname, href) ? 'page' : undefined}
            className={`flex h-9 items-center gap-3 rounded-lg px-3 text-left text-[14px] transition-colors ${
              isActive(pathname, href)
                ? 'bg-[#164f45] font-semibold text-white shadow-sm'
                : 'text-[#6b716e] hover:bg-[#f1f5f1] hover:text-[#164f45]'
            }`}
          >
            <Icon className="size-[17px]" />
            {label}
          </Link>
        ))}
      </nav>

      <div className="mt-auto flex shrink-0 flex-col gap-3 border-t border-[#e2e5df] p-4">
        <OrigenDatos />
        <EstadoPipeline />
      </div>
    </aside>
  )
}
