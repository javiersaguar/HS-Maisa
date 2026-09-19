'use client'

import { USE_MOCK } from '@/lib/config'
import { ORIGEN_DATOS } from '@/lib/api/salud'
import { formatNumber, formatRelative } from '@/lib/format'
import { useSalud } from '@/hooks/useSalud'

/**
 * De dónde salen los datos, como franja fina en lo alto de la pantalla. Se enseña siempre: en la
 * defensa nadie debe confundir el mock con la Caja. Sin caja de color ni esquinas redondeadas —
 * una línea de texto y, como mucho, el color del texto.
 */
export function OrigenBanner() {
  const { data, error } = useSalud({ live: !USE_MOCK })

  if (USE_MOCK) {
    return (
      <div className="flex h-7 shrink-0 items-center gap-2 border-b border-line px-6 text-[12px] text-warn">
        <span className="font-medium">Datos de ejemplo</span>
        <span className="text-faint">·</span>
        <span>No es la Caja de Alberto</span>
      </div>
    )
  }

  const bd = data?.bd ?? null
  const texto = error
    ? 'El puente no responde'
    : !data
      ? 'Comprobando la Caja…'
      : bd
        ? bd.pendientes
          ? `${formatNumber(bd.ficheros)} facturas · ${formatNumber(bd.pendientes)} sin decidir`
          : `${formatNumber(bd.ficheros)} facturas`
        : 'Falta ingest de la Caja'
  const titulo = error ? 'Sin conexión' : !data ? 'Conectando…' : bd ? 'Caja de Alberto' : 'Aún no hay Caja'
  const tono = error || (data && !bd) ? 'text-bad' : 'text-muted'
  const title = bd ? `${ORIGEN_DATOS} · último evento ${formatRelative(bd.ultimoEventoEn)}` : ORIGEN_DATOS

  return (
    <div title={title} className={`flex h-7 shrink-0 items-center gap-2 border-b border-line px-6 text-[12px] ${tono}`}>
      <span className="font-medium">{titulo}</span>
      <span className="text-faint">·</span>
      <span className="cifra">{texto}</span>
    </div>
  )
}
