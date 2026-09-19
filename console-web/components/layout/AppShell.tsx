'use client'

import { useEffect, useRef, useState, type ReactNode } from 'react'
import { usePathname } from 'next/navigation'
import { ChevronLeft } from 'lucide-react'
import { Sidebar } from './Sidebar'

/** Sobrevive al cambio de página y a una recarga, no a cerrar la pestaña. */
const NAV_KEY = 'albertitos.nav.collapsed'

/**
 * Persistent chrome: the sidebar is a fixed island and only the content area
 * scrolls, so the navigation never moves while reading a long screen.
 * Every console route renders inside this shell.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const mainRef = useRef<HTMLElement>(null)
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    try {
      setCollapsed(sessionStorage.getItem(NAV_KEY) === '1')
    } catch {
      // sessionStorage bloqueado: el nav empieza abierto.
    }
  }, [])

  const toggle = () => {
    const next = !collapsed
    setCollapsed(next)
    try {
      sessionStorage.setItem(NAV_KEY, next ? '1' : '0')
    } catch {
      // Sin persistencia; el estado vale para esta vista.
    }
  }

  /** New screen starts at the top. Only on path changes, so URL filter updates do not jump. */
  useEffect(() => {
    mainRef.current?.scrollTo({ top: 0 })
  }, [pathname])

  return (
    <div className="flex h-screen w-full overflow-hidden bg-canvas py-3 pl-3 text-ink">
      <div className="relative flex shrink-0">
        <Sidebar collapsed={collapsed} />
        <button
          onClick={toggle}
          aria-expanded={!collapsed}
          aria-label={collapsed ? 'Mostrar navegación' : 'Ocultar navegación'}
          title={collapsed ? 'Mostrar navegación' : 'Ocultar navegación'}
          className="absolute -right-3 top-1/2 z-20 flex size-6 min-h-0 -translate-y-1/2 items-center justify-center rounded-full border border-line bg-surface text-muted shadow-sm transition hover:text-accent-dark focus-visible:ring-2 focus-visible:ring-accent-dark/30"
        >
          <ChevronLeft className={`size-3.5 transition-transform duration-200 ${collapsed ? 'rotate-180' : ''}`} />
        </button>
      </div>
      <main ref={mainRef} className="ml-3 min-w-0 flex-1 overflow-x-hidden overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
