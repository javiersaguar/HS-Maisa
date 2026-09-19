import type { Fuentes, InvoiceFacts } from '@/lib/types'
import { ERP_NOMBRE } from '@/lib/config'
import { formatAmount, formatDate } from '@/lib/format'
import type { Tone } from '@/lib/theme'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { EmptyState } from '@/components/ui/states'

function Check({
  label,
  status,
  tone,
  detail,
  index,
}: {
  label: string
  status: string
  tone: Tone
  detail: string | null
  index: number
}) {
  return (
    <div
      className="flex items-center justify-between gap-3 border-b border-[#edf0ec] px-3 py-2.5 last:border-0 animate-in fade-in slide-in-from-left-1 duration-300"
      style={{ animationDelay: `${index * 80}ms`, animationFillMode: 'both' }}
    >
      <div className="min-w-0">
        <p className="font-medium">{label}</p>
        {detail && <p className="mt-1 text-[12px] leading-5 text-[#68736d]">{detail}</p>}
      </div>
      <StatusBadge tone={tone} className="shrink-0">
        {status}
      </StatusBadge>
    </div>
  )
}

const same = (a: string | null | undefined, b: string | null | undefined) => Boolean(a && b && a === b)
const sameAmount = (a: number | null | undefined, b: number | null | undefined) =>
  a !== null && a !== undefined && b !== null && b !== undefined && Math.abs(a - b) <= 0.01

/**
 * Lo que dicen el maestro Excel y el snapshot del ERP 2009 del fichero, al lado de lo que dice el PDF.
 * Sólo muestra datos: la regla que los juzga (R1, R2, R5) está en la pestaña Decisión.
 */
export function ErpMatchPanel({ fuentes, hechos }: { fuentes: Fuentes | null; hechos: InvoiceFacts | null }) {
  if (!fuentes || !hechos) {
    return (
      <EmptyState
        title="Sin cruce todavía"
        description="Este fichero no tiene hechos extraídos, así que no se ha cruzado con el maestro ni con el ERP."
      />
    )
  }

  const { proveedor, pedido, asientos } = fuentes

  return (
    <div className="flex flex-col gap-4 text-[14px]">
      <div className="rounded-xl border border-[#dfe4de] bg-[#fafcfa] p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-semibold">Maestro de proveedores</h3>
          <span className="text-[12px] text-[#8a958e]">
            {fuentes.maestro_version ? 'snapshot actual' : 'sin snapshot todavía'}
          </span>
        </div>
        <p className="mt-2 leading-5 text-[#68736d]">
          {proveedor
            ? `${proveedor.razon_social}${proveedor.ciudad ? `, de ${proveedor.ciudad}` : ''}${proveedor.condiciones_dias ? `. Pago a ${proveedor.condiciones_dias} días` : ''}.`
            : `El NIF ${hechos.nif_emisor ?? 'de la factura (no se pudo leer)'} no está en el maestro.`}
        </p>
        <div className="mt-4 overflow-hidden rounded-lg border border-[#dfe4de] bg-white text-[13px]">
          <Check
            index={0}
            label="NIF"
            tone={same(proveedor?.nif, hechos.nif_emisor) ? 'green' : 'yellow'}
            status={same(proveedor?.nif, hechos.nif_emisor) ? 'Coincide' : 'No coincide'}
            detail={
              same(proveedor?.nif, hechos.nif_emisor)
                ? `El PDF y el maestro tienen el mismo NIF (${hechos.nif_emisor}).`
                : `El PDF trae ${hechos.nif_emisor ?? 'un NIF ilegible'} y el maestro ${proveedor?.nif ?? 'no tiene NIF para este proveedor'}.`
            }
          />
          <Check
            index={1}
            label="IBAN"
            tone={same(proveedor?.iban, hechos.iban) ? 'green' : 'yellow'}
            status={same(proveedor?.iban, hechos.iban) ? 'Coincide' : 'No coincide'}
            detail={
              same(proveedor?.iban, hechos.iban)
                ? `El IBAN de la factura coincide con el del maestro.`
                : `La factura trae ${hechos.iban ?? 'un IBAN ilegible'} y el maestro tiene ${proveedor?.iban ?? 'otro (o ninguno)'}.`
            }
          />
          <Check
            index={2}
            label={hechos.pedido ? `Pedido ${hechos.pedido}` : 'Pedido'}
            tone={pedido ? (sameAmount(pedido.importe_total, hechos.total) && same(pedido.nif, hechos.nif_emisor) ? 'green' : 'yellow') : 'yellow'}
            status={pedido ? (sameAmount(pedido.importe_total, hechos.total) ? 'Importe coincide' : 'Importe distinto') : 'No existe'}
            detail={
              pedido
                ? `Es de ${pedido.proveedor_id}, por ${formatAmount(pedido.importe_total)}, en estado ${pedido.estado.toLowerCase()}${pedido.fecha_pedido ? `, con fecha ${formatDate(pedido.fecha_pedido)}` : ''}.`
                : hechos.pedido
                  ? `El pedido ${hechos.pedido} no está en el maestro.`
                  : 'La factura no referencia ningún pedido.'
            }
          />
        </div>
      </div>

      <div className="rounded-xl border border-[#dfe4de] bg-[#fafcfa] p-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-semibold">Asiento en el {ERP_NOMBRE}</h3>
          <span className="text-[12px] text-[#8a958e]">
            {fuentes.erp_version ? `versión ${fuentes.erp_version}` : 'sin snapshot todavía'}
          </span>
        </div>
        {asientos.length === 0 ? (
          <p className="mt-2 leading-5 text-[#68736d]">
            {hechos.pedido ? `El pedido ${hechos.pedido} no tiene asiento en el ERP.` : 'Sin pedido no se puede cruzar con el ERP.'}
          </p>
        ) : (
          <div className="mt-4 overflow-hidden rounded-lg border border-[#dfe4de] bg-white text-[13px]">
            {asientos.map((asiento, index) => (
              <Check
                key={asiento.asiento_id}
                index={index}
                label={`Asiento ${asiento.asiento_id}`}
                tone={asiento.estado === 'PAGADA' ? 'red' : sameAmount(asiento.importe_esperado, hechos.total) ? 'green' : 'yellow'}
                status={asiento.estado === 'PAGADA' ? 'Ya pagada' : asiento.estado === 'PENDIENTE' ? 'Pendiente' : asiento.estado}
                detail={`El ERP espera ${formatAmount(asiento.importe_esperado)} para el NIF ${asiento.nif}, registrado el ${formatDate(asiento.fecha_registro)}.`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
