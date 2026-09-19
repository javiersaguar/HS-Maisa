'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Activity, FileText, LayoutDashboard, Sparkles, Workflow } from 'lucide-react'
import { BRAND } from '@/lib/config'
import { formatNumber } from '@/lib/format'
import { useEtapas } from '@/hooks/useEtapas'
import { saludEtapa } from '@/components/workers/EtapaIcon'

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

export function Sidebar() {
  const pathname = usePathname() ?? '/'
  const { data, error } = useEtapas({ live: true })

  const etapas = data?.etapas ?? []
  const conIncidencias = etapas.filter((etapa) => saludEtapa(etapa, data?.ficheros ?? 0).tone !== 'green').length

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

      <div className="mt-auto shrink-0 border-t border-[#e2e5df] p-4">
        <div className="flex items-center gap-2 text-[14px] font-medium text-[#46504b]">
          <span
            className={`size-2 rounded-full transition-colors ${
              error ? 'bg-[#f05b5b]' : !data ? 'animate-pulse bg-[#c9cec9]' : conIncidencias ? 'bg-[#e0c95a]' : 'bg-[#63d5aa]'
            }`}
          />
          {error
            ? 'Sin datos del pipeline'
            : !data
              ? 'Conectando…'
              : conIncidencias
                ? `${conIncidencias} ${conIncidencias === 1 ? 'etapa' : 'etapas'} con incidencias`
                : 'Pipeline al día'}
        </div>
        <p className="mt-1 pl-4 text-[14px] text-[#a0a6a2]">
          {error ? 'Reintentando en segundo plano' : !data ? 'Leyendo eventos…' : `${formatNumber(data.ficheros)} ficheros · sólo lectura`}
        </p>
      </div>
    </aside>
  )
}
