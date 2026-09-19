import type { ReactNode } from 'react'

/** Re-mounted on every navigation: gives each route a short fade-in while the sidebar stays put. */
export default function Template({ children }: { children: ReactNode }) {
  return <div className="animate-in fade-in slide-in-from-bottom-1 duration-300">{children}</div>
}
