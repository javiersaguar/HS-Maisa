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
    const base = highlight || active ? 'border-accent bg-accent-soft' : 'border-line bg-surface'
    return `${base} ${active ? 'ring-2 ring-accent-dark ring-offset-2 scale-[1.02]' : ''} transition duration-200`
  }

  const field = (campo: CampoHecho, label: string, mono = false) => (
    <div key={campo} className={`rounded border px-3 py-2 ${box(campo)}`} data-field={campo}>
      <p className="text-[8px] font-bold uppercase text-accent-dark">{label}</p>
      <p className={`mt-2 text-[13px] font-semibold ${mono ? 'font-mono' : ''}`}>{value(campo)}</p>
    </div>
  )

  return (
    <Card className="flex min-h-[690px] flex-col overflow-hidden border-line shadow-[0_8px_30px_rgba(43,55,51,0.05)]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-surface px-4 py-3">
        <div className="flex items-center gap-1 rounded-lg border border-line bg-surface p-1">
          <button
            onClick={() => onZoom(Math.max(60, zoom - 10))}
            disabled={zoom <= 60}
            aria-label="Alejar"
            className="size-7 min-h-0 rounded text-sm transition hover:bg-raised disabled:opacity-30"
          >
            −
          </button>
          <button
            onClick={() => onZoom(100)}
            title="Restablecer zoom"
            aria-label={`Zoom ${zoom} %. Volver a 100 %`}
            className="min-h-0 min-w-12 rounded text-center text-[13px] font-semibold tabular-nums transition hover:bg-raised"
          >
            {zoom}%
          </button>
          <button
            onClick={() => onZoom(Math.min(140, zoom + 10))}
            disabled={zoom >= 140}
            aria-label="Acercar"
            className="size-7 min-h-0 rounded text-sm transition hover:bg-raised disabled:opacity-30"
          >
            +
          </button>
        </div>
        <span className="min-w-0 truncate text-[12px] text-muted" title={fichero.file_id}>
          {fichero.file_id}
          {fichero.paginas
            ? ` · ${fichero.paginas === 1 ? '1 página' : `${fichero.paginas} páginas`}`
            : ''}
          {fichero.tiene_texto === false ? ', escaneada' : fichero.tiene_texto ? ', con texto' : ''}
        </span>
        <button
          onClick={onToggleHighlight}
          aria-pressed={highlight}
          className={`text-[13px] font-medium transition hover:text-accent-dark ${highlight ? 'text-accent-dark' : 'text-muted'}`}
        >
          {highlight ? 'Ocultar hechos' : 'Señalar hechos'}
        </button>
      </div>
      <div className="flex-1 overflow-auto bg-raised p-5 sm:p-8">
        <div
          ref={pageRef}
          className="relative mx-auto flex min-h-[610px] max-w-[820px] flex-col overflow-hidden rounded-sm border border-line bg-surface p-7 shadow-[0_4px_14px_rgba(43,55,51,0.08)] transition-transform duration-200 ease-out"
          style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top center' }}
        >
          {!hechos && (
            <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-10 bg-surface/60">
              <div className="animate-scan absolute inset-x-0 h-10 -translate-y-1/2 bg-linear-to-b from-transparent via-accent/30 to-transparent" />
              <span className="absolute right-3 top-3 rounded-full bg-warn-soft px-2.5 py-1 text-[11px] font-semibold text-warn">
                Extracción pendiente
              </span>
            </div>
          )}
          <div className="flex items-start justify-between">
            <div className={`rounded-lg border p-3 ${box('razon_social')}`} data-field="razon_social">
              <p className="text-[8px] font-bold uppercase tracking-wide text-accent-dark">Emisor</p>
              <p className="mt-2 text-[14px] font-semibold">{value('razon_social')}</p>
              <p className={`mt-2 inline-block rounded border px-1.5 py-0.5 font-mono text-[11px] ${box('nif_emisor')}`} data-field="nif_emisor">
                NIF {value('nif_emisor')}
              </p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <span className="text-[18px] font-bold tracking-[0.2em] text-muted/60">FACTURA</span>
              <span className="h-2 w-14 rounded bg-raised" />
            </div>
          </div>
          <div className="mt-5 flex flex-wrap gap-4">
            {field('num_factura', 'Nº factura', true)}
            {field('fecha', 'Fecha')}
            {field('pedido', 'Pedido', true)}
          </div>
          <div className="mt-3 h-px bg-line" />
          <div className="mt-3 flex flex-col gap-2 text-[12px] text-ink-soft">
            {hechos?.lineas.length
              ? hechos.lineas.map((linea, index) => (
                  <div key={index} className="flex justify-between gap-4">
                    <span>{linea.concepto}</span>
                    <span className="tabular-nums">{formatAmount(linea.importe)}</span>
                  </div>
                ))
              : [1, 2, 3].map((line) => (
                  <div key={line} className="flex justify-between">
                    <span className="h-2 w-44 rounded bg-raised" />
                    <span className="h-2 w-10 rounded bg-raised" />
                  </div>
                ))}
          </div>

          {hechos?.texto_sospechoso && (
            <div className="mt-5 rounded border border-dashed border-warn-line bg-warn-soft px-3 py-2">
              <p className="text-[8px] font-bold uppercase tracking-wide text-warn">
                Texto en el documento · evidencia, no una orden
              </p>
              <p className="mt-1 text-[12px] italic leading-5 text-warn">“{hechos.texto_sospechoso}”</p>
            </div>
          )}

          <div className="mt-auto flex flex-col gap-2 border-t border-line pt-3">
            <div className="flex flex-wrap justify-end gap-3">
              {field('base', 'Base imponible')}
              {field('iva', 'IVA')}
            </div>
            <div className={`flex justify-between rounded border px-3 py-3 text-[14px] font-bold ${box('total')}`} data-field="total">
              <span className="text-accent-dark">TOTAL</span>
              <span>{value('total')}</span>
            </div>
            <p className={`self-start rounded border px-2 py-1 font-mono text-[11px] ${box('iban')}`} data-field="iban">
              IBAN {value('iban')}
            </p>
          </div>
        </div>
      </div>
    </Card>
  )
}
