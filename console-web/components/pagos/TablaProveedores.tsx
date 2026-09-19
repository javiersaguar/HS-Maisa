'use client'

import type { ProveedorPago } from '@/lib/types'
import { formatDate, formatImporte, formatNumber, initials } from '@/lib/format'
import { Card } from '@/components/ui/Card'
import { ErrorState, LoadingState } from '@/components/ui/states'
import type { ApiError } from '@/lib/api/client'
import { IbanSinControl } from './ListaPagos'

/** Por proveedor, de mayor a menor importe (orden de la API). Pulsar una fila filtra la lista de pagos. */
export function TablaProveedores({
  proveedores,
  error,
  loading,
  onRetry,
  activo,
  onSelect,
}: {
  proveedores: ProveedorPago[] | null
  error: ApiError | null
  loading: boolean
  onRetry: () => void
  activo: string | null
  onSelect: (proveedorId: string | null) => void
}) {
  return (
    <Card className="mt-6 overflow-hidden rounded-2xl border-[#e1e7e2] shadow-[0_8px_28px_rgba(20,55,45,0.045)]">
      <div className="flex items-center justify-between gap-3 px-5 pt-5">
        <div>
          <h2 className="text-[22px] font-semibold tracking-[-0.025em]">Por proveedor</h2>
          <p className="mt-1 text-[13px] text-[#8a958e]">Pulsa un proveedor para ver sólo sus pagos.</p>
        </div>
        {activo && (
          <button onClick={() => onSelect(null)} className="text-[13px] font-semibold text-[#315d53] underline">
            Ver todos
          </button>
        )}
      </div>
      {error && !proveedores ? (
        <ErrorState error={error} onRetry={onRetry} retrying={loading} />
      ) : !proveedores ? (
        <LoadingState label="Cargando proveedores" rows={4} />
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-[14px]">
            <thead>
              <tr className="border-y border-[#e8ece9] bg-[#fbfcfb] text-[11px] font-bold uppercase tracking-[0.1em] text-[#78867e]">
                <th className="px-5 py-3">Proveedor</th>
                <th className="px-3 py-3 text-right">Facturas</th>
                <th className="px-3 py-3 text-right">Importe</th>
                <th className="px-3 py-3 text-right">Vencido</th>
                <th className="px-3 py-3">Ejecución</th>
                <th className="px-5 py-3">IBAN</th>
              </tr>
            </thead>
            <tbody>
              {proveedores.map((p) => {
                const selected = activo === p.proveedor_id
                return (
                  <tr
                    key={p.proveedor_id}
                    tabIndex={0}
                    aria-selected={selected}
                    onClick={() => onSelect(selected ? null : p.proveedor_id)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        onSelect(selected ? null : p.proveedor_id)
                      }
                    }}
                    className={`cursor-pointer border-b border-[#edf0ec] outline-none transition-colors last:border-b-0 hover:bg-[#f5fbf8] focus-visible:bg-[#f5fbf8] ${selected ? 'bg-[#e2f8ee]' : ''}`}
                  >
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <span className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-[#e0e6e1] bg-[#f7f9f7] text-[11px] font-bold text-[#60736a]">
                          {initials(p.beneficiario)}
                        </span>
                        <div>
                          <p className="font-semibold text-[#203b31]">{p.beneficiario}</p>
                          <p className="font-mono text-[12px] text-[#94a099]">{p.proveedor_id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums text-[#52605a]">{formatNumber(p.numero)}</td>
                    <td className="px-3 py-3 text-right font-semibold tabular-nums whitespace-nowrap text-[#203b31]">
                      {formatImporte(p.importe_eur)}
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums whitespace-nowrap text-[#bd3434]">
                      {p.vencidos_numero > 0 ? (
                        <>
                          {formatImporte(p.vencidos_importe_eur)}
                          <span className="ml-1 text-[12px] text-[#c98b8b]">({formatNumber(p.vencidos_numero)})</span>
                        </>
                      ) : (
                        <span className="text-[#9aa39e]">—</span>
                      )}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap text-[13px] text-[#68736d]">
                      {p.primera_ejecucion === p.ultima_ejecucion
                        ? formatDate(p.primera_ejecucion)
                        : `${formatDate(p.primera_ejecucion)} → ${formatDate(p.ultima_ejecucion)}`}
                    </td>
                    <td className="px-5 py-3">{p.iban_control_ok ? <span className="text-[13px] text-[#176d59]">Correcto</span> : <IbanSinControl />}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}
