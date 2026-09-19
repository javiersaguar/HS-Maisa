'use client'

import type { Event } from '@/lib/types'
import { describirEvento, ETAPA_LABELS, formatMs, formatRelative } from '@/lib/format'
import { useRowLink } from '@/hooks/useRowLink'
import { EmptyState } from '@/components/ui/states'
import { EventoBadge } from '@/components/invoices/badges'
import { ficheroHref } from '@/lib/routes'

/** Últimas filas de `eventos`. `showEtapa` añade la columna de etapa (vista general). */
export function EventosTable({ eventos, showEtapa = false }: { eventos: Event[]; showEtapa?: boolean }) {
  const rowLink = useRowLink()

  if (!eventos.length) {
    return (
      <EmptyState
        title="Sin eventos todavía"
        description="ingest, extract y decide anotan un fichero; validate sólo duplicados; enrich son peticiones al ERP; emit aparece al empaquetar."
      />
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[620px] text-left">
        <thead>
          <tr className="border-b border-line text-[14px] uppercase tracking-wide text-muted">
            <th className="px-5 py-3 font-medium">Fichero</th>
            {showEtapa && <th className="px-5 py-3 font-medium">Etapa</th>}
            <th className="px-5 py-3 font-medium">Estado</th>
            <th className="px-5 py-3 font-medium">Latencia</th>
            <th className="px-5 py-3 font-medium">Detalle</th>
            <th className="px-5 py-3 font-medium">Cuándo</th>
          </tr>
        </thead>
        <tbody>
          {eventos.map((evento, index) => (
            <tr
              key={`${evento.file_id}-${evento.etapa}-${evento.intento}-${index}`}
              {...rowLink(evento.file_id ? ficheroHref(evento.file_id) : null)}
              className={`border-b border-line-soft text-[14px] transition-colors last:border-0 hover:bg-[var(--color-raised)] ${evento.file_id ? 'cursor-pointer' : ''}`}
            >
              <td className="max-w-[220px] truncate px-5 py-3 font-mono text-[13px]" title={evento.file_id ?? undefined}>
                {evento.file_id ?? '—'}
              </td>
              {showEtapa && <td className="px-5 py-3">{ETAPA_LABELS[evento.etapa]}</td>}
              <td className="px-5 py-3 whitespace-nowrap">
                <EventoBadge estado={evento.estado} />
                {evento.intento > 1 && <span className="ml-1.5 text-[12px] text-muted">#{evento.intento}</span>}
              </td>
              <td className="px-5 py-3 text-ink-soft tabular-nums">{formatMs(evento.latencia_ms)}</td>
              <td className="max-w-[320px] truncate px-5 py-3 text-[13px] text-ink-soft" title={describirEvento(evento)}>
                {describirEvento(evento)}
              </td>
              <td className="px-5 py-3 whitespace-nowrap text-muted">{formatRelative(evento.ts)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
