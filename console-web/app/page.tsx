'use client'

import { useCallback, useState } from 'react'
import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'
import { BRAND } from '@/lib/config'
import { Analisis } from '@/components/dashboard/Analisis'
import { InvoiceDropzone } from '@/components/dashboard/InvoiceDropzone'
import { Card } from '@/components/ui/Card'
import { Toast } from '@/components/ui/Toast'

/**
 * Portada: soltar facturas y entender qué decide la norma con cada una.
 *
 * No hay recuentos de la base de datos a propósito. Lo que se enseña aquí es lo que acabas de subir;
 * el histórico acumulado vive en Ficheros, porque cuando llegue otra Caja la portada tiene que hablar
 * de ella y no de lo que había antes.
 */
export default function PortadaPage() {
  const [toast, setToast] = useState<{ message: string; tone: 'success' | 'error' } | null>(null)
  const [seleccionado, setSeleccionado] = useState<string | null>(null)

  const dismissToast = useCallback(() => setToast(null), [])
  const seleccionar = useCallback((fileId: string) => setSeleccionado(fileId), [])
  const facturasDecididas = useCallback((message: string, tone: 'success' | 'error') => {
    setToast({ message, tone })
  }, [])

  return (
    <div className="mx-auto flex h-full max-w-[1400px] flex-col gap-6 px-6 pb-6 pt-8">
      <title>{`${BRAND} · Cuentas a pagar`}</title>

      <header className="shrink-0 text-center">
        <h1 className="titulo text-[38px] leading-none text-ink">{BRAND}</h1>
        <p className="mx-auto mt-3 max-w-[58ch] text-[14px] leading-relaxed text-muted">
          Suelta una factura y la norma dice qué hacer con ella y por qué.
        </p>
        <Link
          href="/invoices"
          className="mt-3 inline-flex items-center gap-1 text-[13px] text-muted transition hover:text-ink"
        >
          Ver todo lo procesado hasta ahora
          <ArrowUpRight className="size-3.5" />
        </Link>
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
