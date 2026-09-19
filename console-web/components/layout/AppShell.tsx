'use client'

import { useEffect, useRef, type ReactNode } from 'react'
import { usePathname } from 'next/navigation'
import { Sidebar } from './Sidebar'

/**
 * Persistent chrome: the sidebar is a fixed island and only the content area
 * scrolls, so the navigation never moves while reading a long screen.
 * Every console route renders inside this shell.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const mainRef = useRef<HTMLElement>(null)

  /** New screen starts at the top. Only on path changes, so URL filter updates do not jump. */
  useEffect(() => {
    mainRef.current?.scrollTo({ top: 0 })
  }, [pathname])

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#f7f8f5] py-3 pl-3 text-[#17211e]">
      <Sidebar />
      <main ref={mainRef} className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto">
        {children}
      </main>
    </div>
  )
}
