import type { ReactNode } from 'react'

/** The surface used by every screen. Extracted from the original prototype. */
export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <section
      className={`rounded-xl border border-[#e1e5df] bg-white shadow-[0_1px_2px_rgba(20,45,35,0.02)] ${className}`}
    >
      {children}
    </section>
  )
}
