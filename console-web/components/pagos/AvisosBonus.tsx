'use client'

import Link from 'next/link'
import { ChevronDown, TriangleAlert } from 'lucide-react'
import type { AvisoBonus } from '@/lib/types'
import type { ApiError } from '@/lib/api/client'
import { formatNumber } from '@/lib/format'
import { ficheroHref } from '@/lib/routes'
import { Card } from '@/components/ui/Card'

/** Avisos del calendario, plegados: código, fichero y el detalle tal como lo escribe el backend. */
export function AvisosBonus({ avisos, error }: { avisos: { total: number; avisos: AvisoBonus[] } | null; error: ApiError | null }) {
  if (error && !avisos) {
    return (
      <Card className="mt-6 rounded-2xl px-5 py-4 text-[13px] text-[#8f2a2a]">No se pudieron leer los avisos: {error.message}</Card>
    )
  }
  if (!avisos) return null
  const porCodigo = avisos.avisos.reduce<Record<string, number>>((acc, aviso) => {
    acc[aviso.codigo] = (acc[aviso.codigo] ?? 0) + 1
    return acc
  }, {})
  return (
    <Card className="mt-6 overflow-hidden rounded-2xl border-[#e1e7e2] shadow-[0_8px_28px_rgba(20,55,45,0.045)]">
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-5 py-4 [&::-webkit-details-marker]:hidden">
          <span className="flex items-center gap-3">
            <TriangleAlert className="size-4 text-[#a08400]" />
            <span className="text-[16px] font-semibold">Avisos del calendario</span>
            <span className="rounded-full border border-[#eee8bd] bg-[#fffbe8] px-2.5 py-0.5 text-[12px] font-semibold text-[#8a7400] tabular-nums">
              {formatNumber(avisos.total)}
            </span>
            <span className="hidden text-[12px] text-[#8a958e] sm:inline">
              {Object.entries(porCodigo)
                .map(([codigo, n]) => `${codigo} × ${n}`)
                .join(' · ')}
            </span>
          </span>
          <ChevronDown className="size-4 text-[#789087] transition-transform group-open:rotate-180" />
        </summary>
        {avisos.avisos.length === 0 ? (
          <p className="border-t border-[#edf0ec] px-5 py-4 text-[13px] text-[#8a958e]">Sin avisos.</p>
        ) : (
          <ul className="border-t border-[#edf0ec]">
            {avisos.avisos.map((aviso) => (
              <li key={`${aviso.codigo}-${aviso.file_id}`} className="border-b border-[#edf0ec] px-5 py-3 last:border-b-0">
                <div className="flex flex-wrap items-center gap-2 text-[13px]">
                  <span className="rounded-md bg-[#f1f5f1] px-1.5 py-0.5 font-mono text-[11px] font-semibold text-[#52605a]">
                    {aviso.codigo}
                  </span>
                  <Link href={ficheroHref(aviso.file_id)} className="font-mono font-semibold text-[#176d59] hover:underline">
                    {aviso.file_id}
                  </Link>
                </div>
                <p className="mt-1 text-[13px] leading-5 text-[#68736d]">{aviso.detalle}</p>
              </li>
            ))}
          </ul>
        )}
      </details>
    </Card>
  )
}
