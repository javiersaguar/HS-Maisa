'use client'

import { useEffect } from 'react'
import { AlertTriangle, Check, X } from 'lucide-react'

/**
 * Feedback for an action that already happened through the API client.
 * It never announces something the backend did not do.
 * Errors stay a little longer and are announced assertively.
 */
export function Toast({
  message,
  tone = 'success',
  onDismiss,
}: {
  message: string
  tone?: 'success' | 'error'
  onDismiss: () => void
}) {
  useEffect(() => {
    const timer = window.setTimeout(onDismiss, tone === 'error' ? 6000 : 3200)
    return () => window.clearTimeout(timer)
  }, [message, tone, onDismiss])

  return (
    <div
      key={message}
      role={tone === 'error' ? 'alert' : 'status'}
      className={`fixed bottom-5 left-1/2 z-50 flex max-w-[calc(100vw-32px)] -translate-x-1/2 items-center gap-3 px-4 py-2.5 text-[14px] font-semibold shadow-[0_12px_30px_rgba(43,55,51,0.18)] animate-in fade-in slide-in-from-bottom-3 duration-300 ${
        tone === 'error' ? 'bg-bad text-canvas' : 'bg-accent-dark text-canvas'
      }`}
    >
      {tone === 'success' ? <Check className="size-4 shrink-0" /> : <AlertTriangle className="size-4 shrink-0" />}
      {message}
      <button onClick={onDismiss} aria-label="Cerrar aviso" className="opacity-70 transition hover:opacity-100">
        <X className="size-3.5" />
      </button>
    </div>
  )
}
