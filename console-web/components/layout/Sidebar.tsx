'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Activity,
  Database,
  FileText,
  FlaskConical,
  LayoutDashboard,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
  Workflow,
} from 'lucide-react'
import { USE_MOCK } from '@/lib/config'
import { ORIGEN_DATOS } from '@/lib/api/salud'
import { formatNumber, formatRelative } from '@/lib/format'
import { useSalud } from '@/hooks/useSalud'

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

/**
 * De dónde salen los datos. Se enseña siempre: en la defensa nadie debe confundir el mock con la Caja.
 *  - mock: datos de ejemplo (`NEXT_PUBLIC_USE_MOCK=true`).
 *  - http: Caja de Alberto, puente sin Caja (503) o sin conexión (red).
 *
 * Con el lateral plegado queda sólo el icono con su color, y el detalle en el `title`: la señal no
 * se pierde nunca, porque confundir el mock con la Caja cuesta la defensa.
 */
function OrigenDatos({ compacto }: { compacto: boolean }) {
  const { data, error } = useSalud({ live: !USE_MOCK })

  if (USE_MOCK) {
    const title = 'NEXT_PUBLIC_USE_MOCK=true: 510 ficheros inventados. No es la Caja.'
    if (compacto) {
      return (
        <div
          title={title}
          className="flex justify-center rounded-lg border border-[#eee8bd] bg-[#fffbe8] py-2 text-[#8a7400]"
        >
          <FlaskConical className="size-4" />
        </div>
      )
    }
    return (
      <div title={title} className="rounded-lg border border-[#eee8bd] bg-[#fffbe8] px-2.5 py-1.5 text-[12px] text-[#8a7400]">
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

  if (compacto) {
    return (
      <div title={`${label} · ${detail}`} className={`flex justify-center rounded-lg border py-2 ${tone}`}>
        <Database className="size-4" />
      </div>
    )
  }

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

export function Sidebar() {
  const pathname = usePathname() ?? '/'
  const [abierto, setAbierto] = useState(true)

  return (
    <aside
      className={`flex h-full shrink-0 flex-col overflow-hidden rounded-[28px] border border-[#e2e5df] bg-white shadow-[0_8px_24px_rgba(20,55,45,0.06)] transition-[width] duration-200 ease-out ${
        abierto ? 'w-[220px]' : 'w-[76px]'
      }`}
    >
      <div
        className={`flex shrink-0 items-center gap-2 border-b border-[#e2e5df] py-4 ${
          abierto ? 'justify-between px-4' : 'flex-col justify-center px-3'
        }`}
      >
        <Link
          href="/"
          aria-label="Ir a la portada"
          className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-[#155247] text-white transition hover:bg-[#0d4037]"
        >
          <Sparkles className="size-[18px]" />
        </Link>
        <button
          type="button"
          onClick={() => setAbierto((v) => !v)}
          aria-expanded={abierto}
          title={abierto ? 'Plegar el panel' : 'Desplegar el panel'}
          className="flex size-9 shrink-0 items-center justify-center rounded-lg text-[#8b9790] transition hover:bg-[#f1f5f1] hover:text-[#164f45]"
        >
          {abierto ? <PanelLeftClose className="size-[18px]" /> : <PanelLeftOpen className="size-[18px]" />}
        </button>
      </div>

      <nav className={`flex min-h-0 flex-col gap-1 overflow-y-auto py-3 ${abierto ? 'px-3' : 'px-3.5'}`}>
        {ITEMS.map(({ label, href, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            title={abierto ? undefined : label}
            aria-current={isActive(pathname, href) ? 'page' : undefined}
            className={`flex h-9 items-center rounded-lg text-left text-[14px] transition-colors ${
              abierto ? 'gap-3 px-3' : 'justify-center'
            } ${
              isActive(pathname, href)
                ? 'bg-[#164f45] font-semibold text-white shadow-sm'
                : 'text-[#6b716e] hover:bg-[#f1f5f1] hover:text-[#164f45]'
            }`}
          >
            <Icon className="size-[17px] shrink-0" />
            {abierto && <span className="truncate">{label}</span>}
          </Link>
        ))}
      </nav>

      <div className={`mt-auto shrink-0 border-t border-[#e2e5df] ${abierto ? 'p-4' : 'px-3.5 py-4'}`}>
        <OrigenDatos compacto={!abierto} />
      </div>
    </aside>
  )
}
