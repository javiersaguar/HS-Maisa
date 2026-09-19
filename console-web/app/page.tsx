'use client'

import { useCallback, useState } from 'react'
import { BRAND } from '@/lib/config'
import { Analisis } from '@/components/dashboard/Analisis'
import { InvoiceDropzone } from '@/components/dashboard/InvoiceDropzone'
import { Card } from '@/components/ui/Card'
import { Toast } from '@/components/ui/Toast'

/**
 * Portada: dos tarjetas. A la izquierda se sueltan facturas y se ve cómo avanza el envío; a la derecha,
 * qué decide la norma con la que elijas y por qué.
 *
 * No hay recuentos de la base de datos a propósito: aquí se enseña lo que acabas de subir. El histórico
 * acumulado vive en Ficheros y Etapas, porque cuando llegue otra Caja la portada tiene que hablar de ella.
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
    <div className="mx-auto flex max-w-[1400px] flex-col gap-5 p-6 pt-5 lg:h-full">
      <title>{`Panel · ${BRAND}`}</title>
      <div className="grid grid-cols-1 gap-5 lg:min-h-0 lg:flex-1 lg:grid-cols-[minmax(360px,0.8fr)_1.2fr]">
        <InvoiceDropzone onDone={facturasDecididas} onSelect={seleccionar} seleccionado={seleccionado} />
        <Card className="flex min-h-[420px] flex-col overflow-hidden">
          <Analisis fileId={seleccionado} />
        </Card>
      </div>
      {toast && <Toast message={toast.message} tone={toast.tone} onDismiss={dismissToast} />}
    </div>
  )
}
