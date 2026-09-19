'use client'

import { useEffect, useRef } from 'react'
import { ChevronRight } from 'lucide-react'
import type { Fichero } from '@/lib/types'
import { formatAmount, motivoPrincipal } from '@/lib/format'
import { ficheroHref } from '@/lib/routes'
import { useRowLink } from '@/hooks/useRowLink'
import { ResultadoBadge } from './badges'

const TH = 'h-9 px-3 text-[12px] font-medium text-muted'

/** Cola de ficheros: densa, líneas finas y cabecera fija. Sin tarjeta y sin avatares. */
export function InvoiceTable({
  ficheros,
  selected,
  onToggle,
  onToggleAll,
}: {
  ficheros: Fichero[]
  selected: string[]
  onToggle: (fileId: string) => void
  onToggleAll: () => void
}) {
  const rowLink = useRowLink()
  const onPage = ficheros.filter((fichero) => selected.includes(fichero.file_id)).length
  const allSelected = ficheros.length > 0 && onPage === ficheros.length
  const selectAllRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (selectAllRef.current) selectAllRef.current.indeterminate = onPage > 0 && !allSelected
  }, [onPage, allSelected])

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[980px] border-collapse text-left">
        <thead className="sticky top-0 z-10 bg-surface">
          <tr className="border-b border-line">
            <th className={`${TH} w-9`}>
              <input
                ref={selectAllRef}
                type="checkbox"
                aria-label="Seleccionar todos los ficheros de esta página"
                checked={allSelected}
                onChange={onToggleAll}
              />
            </th>
            <th className={TH}>file_id</th>
            <th className={TH}>Proveedor</th>
            <th className={`${TH} text-right`}>Total</th>
            <th className={TH}>Resultado</th>
            <th className={TH}>Motivo principal</th>
            <th className={`${TH} text-right`}>Lote</th>
            <th className={`${TH} w-8`} />
          </tr>
        </thead>
        <tbody>
          {ficheros.map((fichero) => {
            const h = fichero.hechos
            const marcado = selected.includes(fichero.file_id)
            return (
              <tr
                key={fichero.file_id}
                {...rowLink(ficheroHref(fichero.file_id))}
                aria-label={`Abrir ${fichero.file_id}`}
                className={`group h-10 cursor-pointer border-b border-line-soft text-[13px] transition-colors hover:bg-raised ${
                  marcado ? 'bg-raised' : ''
                }`}
              >
                <td className="px-3">
                  <input
                    type="checkbox"
                    aria-label={`Seleccionar ${fichero.file_id}`}
                    checked={marcado}
                    onChange={() => onToggle(fichero.file_id)}
                    onClick={(event) => event.stopPropagation()}
                    onKeyDown={(event) => event.stopPropagation()}
                  />
                </td>
                <td className="max-w-[260px] px-3">
                  <span className="block truncate ident text-[12px] text-ink" title={fichero.file_id}>
                    {fichero.file_id}
                  </span>
                </td>
                <td className="max-w-[220px] px-3">
                  <span className="block truncate text-ink-soft" title={h?.razon_social ?? undefined}>
                    {h?.razon_social ?? '—'}
                  </span>
                  {h?.nif_emisor && <span className="block ident text-[11px] text-faint">{h.nif_emisor}</span>}
                </td>
                <td className="whitespace-nowrap px-3 text-right text-ink cifra">{formatAmount(h?.total ?? null)}</td>
                <td className="px-3">
                  <ResultadoBadge estado={fichero.estado} />
                </td>
                <td className="max-w-[340px] px-3">
                  <span className="block truncate text-muted" title={motivoPrincipal(fichero)}>
                    {motivoPrincipal(fichero)}
                  </span>
                </td>
                <td className="px-3 text-right text-muted cifra">{fichero.lote}</td>
                <td className="px-3 text-right">
                  <ChevronRight
                    aria-hidden
                    className="size-4 text-line opacity-0 transition group-hover:opacity-100 group-hover:text-faint"
                  />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
