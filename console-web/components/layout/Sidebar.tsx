'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Activity, FileText, LayoutDashboard, PanelLeftClose, PanelLeftOpen, Workflow } from 'lucide-react'

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
 * Navegación. El elemento activo se marca con una barra de 2px y negrita, no con un bloque relleno:
 * en una herramienta de trabajo el color se reserva para los estados, no para decir dónde estás.
 */
export function Sidebar() {
  const pathname = usePathname() ?? '/'
  const [abierto, setAbierto] = useState(true)

  return (
    <aside
      className={`flex h-full shrink-0 flex-col border-r border-line bg-surface transition-[width] duration-150 ease-out ${
        abierto ? 'w-[196px]' : 'w-[52px]'
      }`}
    >
      <div
        className={`flex h-12 shrink-0 items-center border-b border-line ${
          abierto ? 'justify-between px-3' : 'justify-center px-0'
        }`}
      >
        {abierto && (
          <Link href="/" className="text-[14px] font-semibold tracking-[-0.01em] text-ink">
            Albertito
          </Link>
        )}
        <button
          type="button"
          onClick={() => setAbierto((v) => !v)}
          aria-expanded={abierto}
          title={abierto ? 'Plegar el panel' : 'Desplegar el panel'}
          className="flex size-8 shrink-0 items-center justify-center rounded-[var(--radius-ui)] text-faint transition hover:text-ink"
        >
          {abierto ? <PanelLeftClose className="size-4" /> : <PanelLeftOpen className="size-4" />}
        </button>
      </div>

      <nav className="flex min-h-0 flex-col overflow-y-auto py-1">
        {ITEMS.map(({ label, href, icon: Icon }) => {
          const activo = isActive(pathname, href)
          return (
            <Link
              key={href}
              href={href}
              title={abierto ? undefined : label}
              aria-current={activo ? 'page' : undefined}
              className={`flex h-9 items-center border-l-2 text-[13px] transition-colors ${
                abierto ? 'gap-2.5 pl-3 pr-3' : 'justify-center'
              } ${activo ? 'border-accent font-semibold text-ink' : 'border-transparent text-muted hover:text-ink'}`}
            >
              <Icon className="size-4 shrink-0" />
              {abierto && <span className="truncate">{label}</span>}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
