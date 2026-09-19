'use client'

import Link from 'next/link'
import { ResultadoBadge } from '@/components/invoices/badges'
import { useFichero } from '@/hooks/useFicheros'
import { formatAmount, motivoPrincipal, resumenReglas } from '@/lib/format'
import { ficheroHref } from '@/lib/routes'
import { USE_MOCK } from '@/lib/config'

export function FichaResolucion({ fileId }: { fileId: string }) {
  const { data, error, loading } = useFichero(fileId)
  const enlace = <Link href={ficheroHref(fileId)} className="font-semibold text-[#176d59] underline underline-offset-2">Ver la traza</Link>
  if (loading) return <p className="text-xs text-[#68736d]">Consultando la decisión guardada…</p>
  if (error || !data) return <div className="rounded-xl border border-[#e1e5df] p-3 text-xs"><p>No se pudo leer la decisión guardada.</p>{enlace}</div>
  const resultado = data.decision?.resultado ?? 'PENDIENTE'

  return (
    <section aria-label="Decisión guardada de la primera factura citada" className="chat-cita space-y-2 rounded-xl border border-[#dcefe6] bg-[#f7faf8] p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[#68736d]">{USE_MOCK ? 'Datos de ejemplo · no es la BD' : 'Decisión guardada · base de datos'}</p>
        <ResultadoBadge estado={resultado} withIcon={false} />
      </div>
      <p className="break-all text-xs font-medium">{fileId}</p>
      <p className="text-xs">{data.hechos?.razon_social ?? 'Proveedor no disponible'} · <strong>{formatAmount(data.hechos?.total ?? null, data.hechos?.moneda)}</strong></p>
      <p className="text-xs leading-relaxed">{motivoPrincipal(data)}</p>
      {data.decision && resumenReglas(data.decision) ? (
        <p className="text-[11px] text-[#68736d]">{resumenReglas(data.decision)}</p>
      ) : null}
      {enlace}
    </section>
  )
}

