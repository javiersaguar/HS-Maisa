import Link from 'next/link'
import type { ReactNode } from 'react'

/** The "← Back to …" control repeated across detail screens. */
export function BackLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="group inline-flex items-center gap-2 rounded-lg border border-[#d8e2dc] bg-white px-3.5 py-2 text-[14px] font-semibold text-[#315d53] shadow-[0_1px_2px_rgba(20,45,35,0.04)] transition hover:border-[#164f45] hover:bg-[#eff8f3] hover:text-[#164f45]"
    >
      <span className="text-[16px] leading-none transition-transform group-hover:-translate-x-0.5">
        ←
      </span>
      {children}
    </Link>
  )
}
