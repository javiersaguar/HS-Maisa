import type { ReactNode } from 'react'

/** Superficie base: borde de 1px, radio corto y ninguna sombra. */
export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <section className={`border border-line bg-surface ${className}`}>{children}</section>
  )
}
