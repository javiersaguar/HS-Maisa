'use client'

import { useCallback, useState } from 'react'
import { usePanel } from '@/hooks/usePanel'
import { BRAND } from '@/lib/config'
import { formatNumber } from '@/lib/format'
import type { EstadoFichero } from '@/lib/types'
import { Analisis } from '@/components/dashboard/Analisis'
import { InvoiceDropzone } from '@/components/dashboard/InvoiceDropzone'
import { Card } from '@/components/ui/Card'
import { estiloResultado } from '@/components/ui/Resultado'
import { Toast } from '@/components/ui/Toast'

const ORDEN: EstadoFichero[] = ['PAGAR', 'ESCALAR', 'NO_PAGAR', 'PENDIENTE']

/**
 * Recuento de las decisiones vigentes. Sin pastillas ni medallones: sólo la cifra, su palabra y una
 * regla de color fina, para que el peso visual se lo lleve la bandeja.
 */
function Recuento({ porEstado, total }: { porEstado: Record<EstadoFichero, number>; total: number }) {
  return (
    <div className="flex flex-wrap items-stretch justify-center gap-x-10 gap-y-4">
      {ORDEN.map((estado) => {
        const e = estiloResultado(estado)
        return (
          <div key={estado} className="flex items-stretch gap-3">
            <span aria-hidden className={`w-[3px] shrink-0 rounded-sm ${e.barra}`} />
            <div className="text-left">
              <p className={`text-[22px] font-semibold leading-none tracking-[-0.04em] tabular-nums ${e.texto}`}>
                {formatNumber(porEstado[estado])}
              </p>
              <p className="mt-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#9aa39e]">{estado}</p>
            </div>
          </div>
        )
      })}
      <div className="flex items-stretch gap-3">
        <span aria-hidden className="w-[3px] shrink-0 rounded-sm bg-[#dfe4de]" />
        <div className="text-left">
          <p className="text-[22px] font-semibold leading-none tracking-[-0.04em] text-[#17211e] tabular-nums">
            {formatNumber(total)}
          </p>
          <p className="mt-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#9aa39e]">Facturas</p>
        </div>
      </div>
    </div>
  )
}

export default function PortadaPage() {
  const { data, refresh } = usePanel({ live: true })
  const [toast, setToast] = useState<{ message: string; tone: 'success' | 'error' } | null>(null)
  const [seleccionado, setSeleccionado] = useState<string | null>(null)

  const dismissToast = useCallback(() => setToast(null), [])
  const seleccionar = useCallback((fileId: string) => setSeleccionado(fileId), [])
  const facturasDecididas = useCallback(
    (message: string, tone: 'success' | 'error') => {
      setToast({ message, tone })
      refresh()
    },
    [refresh],
  )

  return (
    <div className="mx-auto flex h-full max-w-[1460px] flex-col gap-6 px-6 pb-6 pt-9">
      <title>{`${BRAND} · Cuentas a pagar`}</title>

      <header className="shrink-0 text-center">
        <h1 className="text-[44px] font-semibold leading-none tracking-[-0.045em] text-[#17211e]">{BRAND}</h1>
        <p className="mx-auto mt-3 max-w-[58ch] text-[15px] leading-relaxed text-[#68736d]">
          Suelta una factura y la norma dice qué hacer con ella — y por qué.
        </p>
        {data && (
          <div className="mt-6 border-t border-[#e5e8e3] pt-5">
            <Recuento porEstado={data.porEstado} total={data.ficheros} />
          </div>
        )}
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-5 lg:grid-cols-[minmax(360px,0.8fr)_1.2fr]">
        <InvoiceDropzone onDone={facturasDecididas} onSelect={seleccionar} seleccionado={seleccionado} />
        <Card className="flex min-h-0 flex-col overflow-hidden">
          <Analisis fileId={seleccionado} />
        </Card>
      </div>

      {toast && <Toast message={toast.message} tone={toast.tone} onDismiss={dismissToast} />}
    </div>
  )
}
