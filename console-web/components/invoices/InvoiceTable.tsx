'use client'

import { useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import type { ConfianzaItem, Fichero } from '@/lib/types'
import { formatAmount, initials, motivoPrincipal } from '@/lib/format'
import { ficheroHref } from '@/lib/routes'
import { useRowLink } from '@/hooks/useRowLink'
import { ConfianzaChip } from '@/components/confianza/ConfianzaChip'
import { ResultadoBadge } from './badges'

export function InvoiceTable({
  ficheros,
  selected,
  onToggle,
  onToggleAll,
  confianza = null,
}: {
  ficheros: Fichero[]
  selected: string[]
  onToggle: (fileId: string) => void
  onToggleAll: () => void
  /** file_id → confianza de K3 (una sola GET para toda la lista). Sin servicio (null) la columna sale con «—». */
  confianza?: Map<string, ConfianzaItem> | null
}) {
  const router = useRouter()
  const rowLink = useRowLink()
  const onPage = ficheros.filter((fichero) => selected.includes(fichero.file_id)).length
  const allSelected = ficheros.length > 0 && onPage === ficheros.length
  const selectAllRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (selectAllRef.current) selectAllRef.current.indeterminate = onPage > 0 && !allSelected
  }, [onPage, allSelected])

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[1040px] text-left">
        <thead>
          <tr className="border-b border-line bg-surface text-[11px] font-bold uppercase tracking-[0.1em] text-muted">
            <th className="w-12 px-5 py-4">
              <input
                ref={selectAllRef}
                type="checkbox"
                aria-label="Seleccionar todos los ficheros de esta página"
                checked={allSelected}
                onChange={onToggleAll}
                className="size-4 rounded border-line"
              />
            </th>
            <th className="px-3 py-4">file_id</th>
            <th className="px-3 py-4">Proveedor</th>
            <th className="px-3 py-4">Total</th>
            <th className="px-3 py-4">Resultado</th>
            <th className="px-3 py-4">Confianza</th>
            <th className="px-3 py-4">Motivo principal</th>
            <th className="px-3 py-4">Lote</th>
            <th className="px-5 py-4 text-right">Abrir</th>
          </tr>
        </thead>
        <tbody>
          {ficheros.map((fichero) => {
            const h = fichero.hechos
            const proveedor = h?.razon_social ?? '—'
            const conf = confianza?.get(fichero.file_id)
            return (
              <tr
                key={fichero.file_id}
                {...rowLink(ficheroHref(fichero.file_id))}
                aria-label={`Abrir ${fichero.file_id}`}
                className={`cursor-pointer border-b border-line-soft text-[14px] transition-colors hover:bg-accent-soft ${selected.includes(fichero.file_id) ? 'bg-accent-soft' : ''}`}
              >
                <td className="px-5 py-4">
                  <input
                    type="checkbox"
                    aria-label={`Seleccionar ${fichero.file_id}`}
                    checked={selected.includes(fichero.file_id)}
                    onChange={() => onToggle(fichero.file_id)}
                    onClick={(event) => event.stopPropagation()}
                    onKeyDown={(event) => event.stopPropagation()}
                    className="size-4 rounded border-line"
                  />
                </td>
                <td className="max-w-[240px] px-3 py-4">
                  <span className="block truncate font-mono text-[13px] font-bold text-ink" title={fichero.file_id}>
                    {fichero.file_id}
                  </span>
                  {h?.num_factura && <span className="mt-0.5 block text-[12px] text-muted">{h.num_factura}</span>}
                </td>
                <td className="px-3 py-4">
                  <div className="flex items-center gap-3">
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-line bg-raised text-[11px] font-bold text-ink-soft">
                      {h?.razon_social ? initials(proveedor) : '?'}
                    </span>
                    <div>
                      <p className="font-semibold text-ink">{proveedor}</p>
                      {h?.nif_emisor && <p className="mt-0.5 font-mono text-[12px] text-muted">{h.nif_emisor}</p>}
                    </div>
                  </div>
                </td>
                <td className="px-3 py-4 font-semibold whitespace-nowrap text-ink">{formatAmount(h?.total ?? null, h?.moneda)}</td>
                <td className="px-3 py-4">
                  <ResultadoBadge estado={fichero.estado} withIcon={false} />
                </td>
                <td className="px-3 py-4">
                  <ConfianzaChip banda={conf?.banda} razon={conf?.razon_principal} />
                </td>
                <td className="max-w-[320px] px-3 py-4">
                  <p className="line-clamp-2 text-[13px] leading-5 text-ink-soft" title={motivoPrincipal(fichero)}>
                    {motivoPrincipal(fichero)}
                  </p>
                </td>
                <td className="px-3 py-4 text-ink-soft">{fichero.lote}</td>
                <td className="px-5 py-4 text-right">
                  <button
                    onClick={(event) => {
                      event.stopPropagation()
                      router.push(ficheroHref(fichero.file_id))
                    }}
                    aria-label={`Abrir ${fichero.file_id}`}
                    tabIndex={-1}
                    className="inline-flex size-9 items-center justify-center rounded-xl border border-line bg-surface text-[20px] text-accent-dark shadow-[0_2px_5px_rgba(43,55,51,0.05)] transition hover:translate-x-0.5 hover:border-accent hover:bg-accent-soft hover:text-accent-dark"
                  >
                    ›
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
