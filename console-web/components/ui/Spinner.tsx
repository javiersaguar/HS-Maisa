import { Loader2 } from 'lucide-react'

/** Inline activity indicator for buttons and inputs while a request is in flight. */
export function Spinner({ className = 'size-3.5' }: { className?: string }) {
  return <Loader2 aria-hidden="true" className={`animate-spin ${className}`} />
}
