import Link from 'next/link'
import type { ReactNode } from 'react'

/** The "← Back to …" control repeated across detail screens. */
export function BackLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="group inline-flex items-center gap-2 rounded-[var(--radius-ui)] border border-[#d8e2dc] bg-white px-3.5 py-2 text-[14px] font-semibold text-[#315d53] transition hover:border-[#164f45] hover:text-[#164f45]"
    >
      <span className="text-[16px] leading-none transition-transform group-hover:-translate-x-0.5">
        ←
      </span>
      {children}
    </Link>
  )
}
