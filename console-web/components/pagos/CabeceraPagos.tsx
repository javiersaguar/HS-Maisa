'use client'

import { ShieldAlert } from 'lucide-react'
import type { BonusResumen } from '@/lib/types'
import { formatDate, formatImporte, formatNumber } from '@/lib/format'
import { Skeleton } from '@/components/ui/states'

/**
 * Lo único obligatorio de la pantalla: sin este aviso, la demo promete algo falso. No se pliega, no se
 * cierra y se pinta antes de que llegue ningún dato.
 */
export function AvisoBorrador() {
  return (
    <div
      role="note"
      className="mt-5 flex items-start gap-3 rounded-xl border border-[#f1dada] bg-[#fff5f5] px-4 py-3 text-[14px] leading-5 text-[#8f2a2a]"
    >
      <ShieldAlert className="mt-0.5 size-4 shrink-0" />
      <p>
        <b className="font-semibold">Borrador:</b> los IBAN de esta Caja son sintéticos y un banco los rechazaría. No se
        ha ejecutado ningún pago.
      </p>
    </div>
  )
}

const pill = 'rounded-full border px-3 py-1 tabular-nums'

export function CabeceraPagos({ resumen }: { resumen: BonusResumen | null }) {
  return (
    <header>
      <div className="flex flex-wrap items-center gap-x-7 gap-y-3">
        <h1 className="text-[32px] font-semibold tracking-[-0.04em]">Pagos</h1>
        {resumen ? (
          <div className="flex flex-wrap items-center gap-2 text-[13px] font-semibold animate-in fade-in duration-300">
            <span className={`${pill} border-[#dcefe6] bg-[#eff8f3] text-[#176d59]`}>
              {formatNumber(resumen.calendario_numero)} facturas a pagar · {formatImporte(resumen.calendario_total_eur)}
            </span>
            <span className={`${pill} border-[#f1dada] bg-[#fff0f0] text-[#bd3434]`}>
              {formatImporte(resumen.vencido_importe_eur)} vencidos · {formatNumber(resumen.vencidos)} facturas
            </span>
            <span className={`${pill} border-[#e1e7e2] bg-white text-[#65736b]`}>
              {formatNumber(resumen.vencen_semana_corte)} vencen esta semana
            </span>
            <span className="text-[12px] font-medium text-[#8a958e]">
              Corte {formatDate(resumen.fecha_corte)} · {formatNumber(resumen.proveedores)} proveedores
            </span>
          </div>
        ) : (
          <Skeleton className="h-6 w-96" />
        )}
      </div>
      <p className="mt-2 max-w-[760px] text-[14px] leading-5 text-[#68736d]">
        Cuándo toca pagar cada factura que la norma ha dado por buena. Se calcula en cada lectura con las decisiones
        PAGAR vigentes; no cambia ninguna decisión.
      </p>
      <AvisoBorrador />
    </header>
  )
}
