'use client'

import type { InvoiceFacts } from '@/lib/types'
import { describirExtraccion, formatAmount, formatDate } from '@/lib/format'

/** Campos de `InvoiceFacts` que se pueden señalar en el documento. */
export type CampoHecho =
  | 'razon_social'
  | 'nif_emisor'
  | 'num_factura'
  | 'fecha'
  | 'pedido'
  | 'iban'
  | 'base'
  | 'iva'
  | 'total'

export function campoValor(hechos: InvoiceFacts, campo: CampoHecho): string | null {
  switch (campo) {
    case 'fecha':
      return hechos.fecha ? formatDate(hechos.fecha) : null
    case 'base':
    case 'total':
      return hechos[campo] === null ? null : formatAmount(hechos[campo])
    case 'iva':
      return hechos.iva === null
        ? null
        : `${formatAmount(hechos.iva)}${hechos.iva_pct !== null ? ` (${String(hechos.iva_pct).replace('.', ',')} %)` : ''}`
    default:
      return hechos[campo]
  }
}

const CAMPOS: Array<{ key: CampoHecho; label: string; mono?: boolean }> = [
  { key: 'razon_social', label: 'Razón social' },
  { key: 'nif_emisor', label: 'NIF emisor', mono: true },
  { key: 'num_factura', label: 'Nº factura', mono: true },
  { key: 'fecha', label: 'Fecha' },
  { key: 'pedido', label: 'Pedido', mono: true },
  { key: 'iban', label: 'IBAN', mono: true },
  { key: 'base', label: 'Base' },
  { key: 'iva', label: 'IVA' },
  { key: 'total', label: 'Total' },
]

/**
 * Hechos que el extractor leyó del PDF. Pulsar una fila la señala en el documento.
 * Sólo lectura: corregir un hecho es volver a extraer en el backend, no editar aquí.
 */
export function ExtractedFields({
  hechos,
  activeField,
  onSelect,
}: {
  hechos: InvoiceFacts | null
  activeField: CampoHecho | null
  onSelect: (key: CampoHecho) => void
}) {
  if (!hechos) {
    return <p className="mt-2 text-[13px] text-[#9aa39e]">La extracción no terminó: este fichero no tiene hechos todavía.</p>
  }

  return (
    <>
      <div className="mt-2 overflow-hidden rounded-lg border border-[#dfe4de] text-[13px]">
        {CAMPOS.map((campo) => {
          const value = campoValor(hechos, campo.key)
          return (
            <button
              key={campo.key}
              onClick={() => onSelect(campo.key)}
              aria-pressed={activeField === campo.key}
              className={`flex w-full justify-between gap-3 border-b border-l-2 border-b-[#edf0ec] px-3 py-2 text-left transition-colors last:border-b-0 hover:bg-[#eff8f3] ${activeField === campo.key ? 'border-l-[#35b889] bg-[#eff8f3]' : 'border-l-transparent bg-[#fafbf9]'}`}
            >
              <span className="shrink-0 text-[#7d8580]">{campo.label}</span>
              <b className={`min-w-0 truncate text-right ${campo.mono ? 'font-mono text-[12px]' : ''} ${value ? '' : 'font-normal text-[#b0b8b3]'}`}>
                {value ?? 'no legible'}
              </b>
            </button>
          )
        })}
      </div>
      <p className="mt-3 text-[13px] leading-5 text-[#52605a]">{describirExtraccion(hechos)}</p>
      <p className="mt-2 text-[12px] text-[#9aa39e]">Pulsa un campo para verlo señalado en el documento.</p>
    </>
  )
}
