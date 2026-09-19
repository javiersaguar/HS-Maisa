import Link from 'next/link'
import type { ReactNode } from 'react'

/** The "← Back to …" control repeated across detail screens. */
export function BackLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="group inline-flex items-center gap-2 border border-line bg-surface px-3.5 py-2 text-[14px] font-semibold text-accent-dark shadow-[0_1px_2px_rgba(43,55,51,0.04)] transition hover:border-accent-dark hover:bg-accent-soft hover:text-accent-dark"
    >
      <span className="text-[16px] leading-none transition-transform group-hover:-translate-x-0.5">
        ←
      </span>
      {children}
    </Link>
  )
}
