'use client'

import { useEffect } from 'react'
import { ApiError } from '@/lib/api/client'
import { ErrorCard } from '@/components/ui/states'

/** Last line of defence: a render crash in a route shows this instead of a blank screen. */
export default function RouteError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="mx-auto max-w-[720px] p-6 pt-16">
      <ErrorCard
        error={new ApiError(error.message || 'No se pudo mostrar la pantalla.', 500)}
        title="Esta pantalla ha fallado"
        onRetry={reset}
      />
    </div>
  )
}
