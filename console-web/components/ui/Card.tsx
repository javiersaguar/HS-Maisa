import type { ReactNode } from 'react'

/** The surface used by every screen. Extracted from the original prototype. */
export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={`rounded-xl border border-line bg-surface ${className}`}
    >
      {children}
    </section>
  )
}
