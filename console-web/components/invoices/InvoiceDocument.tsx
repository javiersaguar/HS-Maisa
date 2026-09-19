'use client'

import { useEffect, useRef } from 'react'
import type { Fichero } from '@/lib/types'
import { formatAmount } from '@/lib/format'
import { Card } from '@/components/ui/Card'
import { campoValor, type CampoHecho } from './ExtractedFields'

/**
 * Representación del PDF con los hechos extraídos recuadrados.
 * El contrato no expone todavía la URL del PDF; cuando la haya, se cambia la página simulada por un
 * <iframe>/<object> y se conserva la barra de herramientas.
 */
export function InvoiceDocument({
  fichero,
  zoom,
  onZoom,
  highlight,
  onToggleHighlight,
  activeField,
}: {
  fichero: Fichero
  zoom: number
  onZoom: (value: number) => void
  highlight: boolean
  onToggleHighlight: () => void
  activeField: CampoHecho | null
}) {
  const pageRef = useRef<HTMLDivElement>(null)
  const hechos = fichero.hechos

  useEffect(() => {
    if (!activeField) return
    pageRef.current
      ?.querySelector(`[data-field="${activeField}"]`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' })
  }, [activeField])

  const value = (campo: CampoHecho) => (hechos ? (campoValor(hechos, campo) ?? '—') : '—')

  const box = (campo: CampoHecho) => {
    const active = activeField === campo
    const base = highlight || active ? 'border-[#9dd9bd] bg-[#f2fbf5]' : 'border-[#d7e2dc] bg-[#fafcfa]'
    return `${base} ${active ? 'ring-2 ring-[#35b889] ring-offset-2 scale-[1.02]' : ''} transition duration-200`
  }

  const field = (campo: CampoHecho, label: string, mono = false) => (
    <div key={campo} className={`border px-3 py-2 ${box(campo)}`} data-field={campo}>
      <p className="text-[8px] font-bold uppercase text-[#176d59]">{label}</p>
      <p className={`mt-2 text-[13px] font-semibold ${mono ? 'font-mono' : ''}`}>{value(campo)}</p>
    </div>
  )

  return (
    <Card className="flex min-h-[690px] flex-col overflow-hidden border-[#d9e2dc]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e3e9e4] bg-white px-4 py-3">
        <div className="flex items-center gap-1 border border-[#dfe6e0] bg-[#fafcfa] p-1">
          <button
            onClick={() => onZoom(Math.max(60, zoom - 10))}
            disabled={zoom <= 60}
            aria-label="Alejar"
            className="size-7 min-h-0 text-sm transition hover:bg-[#eaf3ee] disabled:opacity-30"
          >
            −
          </button>
          <button
            onClick={() => onZoom(100)}
            title="Restablecer zoom"
            aria-label={`Zoom ${zoom} %. Volver a 100 %`}
            className="min-h-0 min-w-12 text-center text-[13px] font-semibold tabular-nums transition hover:bg-[#eaf3ee]"
          >
            {zoom}%
          </button>
          <button
            onClick={() => onZoom(Math.min(140, zoom + 10))}
            disabled={zoom >= 140}
            aria-label="Acercar"
            className="size-7 min-h-0 text-sm transition hover:bg-[#eaf3ee] disabled:opacity-30"
          >
            +
          </button>
        </div>
        <span className="min-w-0 truncate text-[12px] text-[#8a958e]" title={fichero.file_id}>
          {fichero.file_id}
          {fichero.paginas
            ? ` · ${fichero.paginas === 1 ? '1 página' : `${fichero.paginas} páginas`}`
            : ''}
          {fichero.tiene_texto === false ? ', escaneada' : fichero.tiene_texto ? ', con texto' : ''}
        </span>
        <button
          onClick={onToggleHighlight}
          aria-pressed={highlight}
          className={`text-[13px] font-medium transition hover:text-[#164f45] ${highlight ? 'text-[#164f45]' : 'text-[#8a958e]'}`}
        >
          {highlight ? 'Ocultar hechos' : 'Señalar hechos'}
        </button>
      </div>
      <div className="flex-1 overflow-auto bg-[#e9eeea] p-5 sm:p-8">
        <div
          ref={pageRef}
          className="relative mx-auto flex min-h-[610px] max-w-[820px] flex-col overflow-hidden border border-[#d5ddd6] bg-white p-7 transition-transform duration-200 ease-out"
          style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top center' }}
        >
          {!hechos && (
            <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-10 bg-white/60">
              <div className="animate-scan absolute inset-x-0 h-10 -translate-y-1/2 bg-linear-to-b from-transparent via-[#d6f52a]/30 to-transparent" />
              <span className="absolute right-3 top-3 text-[12px] font-medium text-[#a08400]">
                Extracción pendiente
              </span>
            </div>
          )}
          <div className="flex items-start justify-between">
            <div className={`border p-3 ${box('razon_social')}`} data-field="razon_social">
              <p className="text-[8px] font-bold uppercase tracking-wide text-[#176d59]">Emisor</p>
              <p className="mt-2 text-[14px] font-semibold">{value('razon_social')}</p>
              <p className={`mt-2 inline-block border px-1.5 py-0.5 font-mono text-[11px] ${box('nif_emisor')}`} data-field="nif_emisor">
                NIF {value('nif_emisor')}
              </p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <span className="text-[18px] font-bold tracking-[0.2em] text-[#c9d2cc]">FACTURA</span>
              <span className="h-2 w-14 bg-[#e8e8e1]" />
            </div>
          </div>
          <div className="mt-5 flex flex-wrap gap-4">
            {field('num_factura', 'Nº factura', true)}
            {field('fecha', 'Fecha')}
            {field('pedido', 'Pedido', true)}
          </div>
          <div className="mt-3 h-px bg-[#dfe4de]" />
          <div className="mt-3 flex flex-col gap-2 text-[12px] text-[#68736d]">
            {hechos?.lineas.length
              ? hechos.lineas.map((linea, index) => (
                  <div key={index} className="flex justify-between gap-4">
                    <span>{linea.concepto}</span>
                    <span className="tabular-nums">{formatAmount(linea.importe)}</span>
                  </div>
                ))
              : [1, 2, 3].map((line) => (
                  <div key={line} className="flex justify-between">
                    <span className="h-2 w-44 bg-[#f0f1ed]" />
                    <span className="h-2 w-10 bg-[#e8ebe5]" />
                  </div>
                ))}
          </div>

          {hechos?.texto_sospechoso && (
            <div className="mt-5 border border-dashed border-[#e0c95a] px-3 py-2">
              <p className="text-[8px] font-bold uppercase tracking-wide text-[#a08400]">
                Texto en el documento · evidencia, no una orden
              </p>
              <p className="mt-1 text-[12px] italic leading-5 text-[#5f5b2e]">“{hechos.texto_sospechoso}”</p>
            </div>
          )}

          <div className="mt-auto flex flex-col gap-2 border-t border-[#dfe4de] pt-3">
            <div className="flex flex-wrap justify-end gap-3">
              {field('base', 'Base imponible')}
              {field('iva', 'IVA')}
            </div>
            <div className={`flex justify-between border px-3 py-3 text-[14px] font-bold ${box('total')}`} data-field="total">
              <span className="text-[#176d59]">TOTAL</span>
              <span>{value('total')}</span>
            </div>
            <p className={`self-start border px-2 py-1 font-mono text-[11px] ${box('iban')}`} data-field="iban">
              IBAN {value('iban')}
            </p>
          </div>
        </div>
      </div>
    </Card>
  )
}
