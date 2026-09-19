'use client'

import type { Fichero } from '@/lib/types'
import { formatAmount, formatRelative, motivoPrincipal } from '@/lib/format'
import { useRowLink } from '@/hooks/useRowLink'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/states'
import { ResultadoBadge } from '@/components/invoices/badges'
import { ficheroHref } from '@/lib/routes'

export function RecentDecisions({ ficheros }: { ficheros: Fichero[] }) {
  const rowLink = useRowLink()
  return (
    <Card className="overflow-hidden">
      <div className="border-b border-[#e5e8e3] px-5 py-4">
        <h2 className="text-[16px] font-semibold tracking-[-0.01em]">Últimas decisiones</h2>
        <p className="mt-0.5 text-[13px] text-[#7f8a83]">Lo último que ha decidido la norma, con su motivo principal</p>
      </div>
      {ficheros.length === 0 ? (
        <EmptyState title="Sin decisiones todavía" description="Aparecen cuando albertitos run procesa la Caja." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left">
            <thead>
              <tr className="border-b border-[#e5e8e3] text-[14px] uppercase tracking-wide text-[#818b85]">
                <th className="px-5 py-3 font-medium">file_id</th>
                <th className="px-5 py-3 font-medium">Proveedor</th>
                <th className="px-5 py-3 font-medium">Total</th>
                <th className="px-5 py-3 font-medium">Resultado</th>
                <th className="px-5 py-3 font-medium">Motivo principal</th>
                <th className="px-5 py-3 font-medium">Decidido</th>
              </tr>
            </thead>
            <tbody>
              {ficheros.map((fichero) => (
                <tr
                  key={fichero.file_id}
                  {...rowLink(ficheroHref(fichero.file_id))}
                  aria-label={`Abrir ${fichero.file_id}`}
                  className="cursor-pointer border-b border-[#edf0ec] text-[13px] transition last:border-0 hover:bg-[#fafcf9]"
                >
                  <td className="max-w-[220px] truncate px-5 py-3.5 font-mono text-[13px] text-[#173c35]" title={fichero.file_id}>
                    {fichero.file_id}
                  </td>
                  <td className="px-5 py-3.5">{fichero.hechos?.razon_social ?? '—'}</td>
                  <td className="px-5 py-3.5 whitespace-nowrap">{formatAmount(fichero.hechos?.total ?? null)}</td>
                  <td className="px-5 py-3.5">
                    <ResultadoBadge estado={fichero.estado} withIcon={false} />
                  </td>
                  <td className="max-w-[340px] px-5 py-3.5 text-[#68736d]">
                    <p className="truncate" title={motivoPrincipal(fichero)}>
                      {motivoPrincipal(fichero)}
                    </p>
                  </td>
                  <td className="px-5 py-3.5 whitespace-nowrap text-[#8d9891]">
                    {formatRelative(fichero.decision?.decidido_en ?? fichero.ingerido_en)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}
