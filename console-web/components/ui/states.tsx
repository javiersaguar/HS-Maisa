'use client'

import type { ReactNode } from 'react'
import { AlertTriangle, Inbox, Lock, RefreshCw, WifiOff } from 'lucide-react'
import type { ApiError } from '@/lib/api/client'
import { Card } from './Card'
import { Spinner } from './Spinner'

/** Grey block used while data is in flight. */
export function Skeleton({ className = '' }: { className?: string }) {
  return <span className={`block animate-pulse bg-[#eceeea] ${className}`} />
}

export function LoadingState({
  label = 'Cargando…',
  rows = 3,
}: {
  label?: string
  rows?: number
}) {
  return (
    <div className="p-6" role="status" aria-live="polite">
      <p className="sr-only">{label}</p>
      <Skeleton className="h-4 w-40" />
      <div className="mt-4 flex flex-col gap-3">
        {Array.from({ length: rows }).map((_, index) => (
          <Skeleton key={index} className="h-12 w-full" />
        ))}
      </div>
    </div>
  )
}

export function LoadingCard({ label, rows = 3 }: { label?: string; rows?: number }) {
  return (
    <Card>
      <LoadingState label={label} rows={rows} />
    </Card>
  )
}

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string
  description?: string
  action?: ReactNode
  icon?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center animate-in fade-in duration-300">
      <span className="flex size-11 items-center justify-center bg-[var(--color-raised)] text-[#6b8078]">
        {icon ?? <Inbox className="size-5" />}
      </span>
      <h3 className="mt-4 text-[15px] font-semibold text-[#17211e]">{title}</h3>
      {description && (
        <p className="mt-1.5 max-w-[420px] text-[14px] leading-5 text-[#8a958e]">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

/**
 * One error surface for the whole product. Distinguishes the three failures a
 * user can actually hit: no backend, no permission, everything else.
 */
export function ErrorState({
  error,
  onRetry,
  retrying = false,
  title,
}: {
  error: ApiError
  onRetry?: () => void
  /** Pass the hook's `loading` so the retry button shows it is working. */
  retrying?: boolean
  title?: string
}) {
  const isNetwork = error.isNetwork
  const isUnauthorized = error.isUnauthorized

  const heading =
    title ??
    (isUnauthorized
      ? 'No tienes acceso a estos datos'
      : isNetwork
        ? 'No se puede contactar con el puente'
        : error.isUnavailable
          ? 'El puente no tiene base de datos'
          : error.isNotFound
            ? 'No encontrado'
            : 'Algo ha fallado')

  const description = isNetwork
    ? 'Arranca `uv run python -m albertitos.console.api`, revisa NEXT_PUBLIC_API_URL o pon NEXT_PUBLIC_USE_MOCK=true para trabajar sin red.'
    : error.message

  return (
    <div
      className="flex flex-col items-center justify-center px-6 py-14 text-center animate-in fade-in duration-300"
      role="alert"
    >
      <span className="flex size-11 items-center justify-center text-[#bd3434]">
        {isUnauthorized ? (
          <Lock className="size-5" />
        ) : isNetwork ? (
          <WifiOff className="size-5" />
        ) : (
          <AlertTriangle className="size-5" />
        )}
      </span>
      <h3 className="mt-4 text-[15px] font-semibold text-[#17211e]">{heading}</h3>
      <p className="mt-1.5 max-w-[460px] text-[14px] leading-5 text-[#8a958e]">{description}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          disabled={retrying}
          className="mt-5 inline-flex items-center gap-2 border border-[#d5e0d9] bg-white px-4 py-2 text-[14px] font-semibold text-[#315d53] transition hover:border-[#164f45] disabled:opacity-60"
        >
          {retrying ? <Spinner /> : <RefreshCw className="size-3.5" />}
          {retrying ? 'Reintentando…' : 'Reintentar'}
        </button>
      )}
    </div>
  )
}

export function ErrorCard(props: Parameters<typeof ErrorState>[0]) {
  return (
    <Card>
      <ErrorState {...props} />
    </Card>
  )
}
