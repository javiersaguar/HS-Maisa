'use client'

import type { KeyboardEvent } from 'react'
import { useRouter } from 'next/navigation'

/**
 * Makes a table row behave like a link: click, Enter and Space navigate,
 * and the row is reachable with Tab.
 */
export function useRowLink() {
  const router = useRouter()
  return (href: string | null) =>
    href
      ? {
          role: 'link' as const,
          tabIndex: 0,
          onClick: () => router.push(href),
          onKeyDown: (event: KeyboardEvent) => {
            if (event.target !== event.currentTarget) return
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault()
              router.push(href)
            }
          },
        }
      : {}
}
