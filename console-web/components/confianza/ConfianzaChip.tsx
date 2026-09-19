import type { BandaConfianza } from '@/lib/types'

/*
 * Confianza en la CLASIFICACIÓN (K3), no probabilidad de pago ni `InvoiceFacts.confianza` (lectura).
 * Número + banda en texto: el color no es la única señal. Paleta de StatusBadge.
 */
const TONO: Record<BandaConfianza, string> = {
  alta: 'bg-[#edf9f4] text-[#087b5b]',
  media: 'bg-[#fff9e6] text-[#a87000]',
  baja: 'bg-[#fff0f0] text-[#bd3434]',
}

export function ConfianzaChip({
  puntuacion,
  banda,
  razon,
}: {
  puntuacion?: number | null
  banda?: BandaConfianza | null
  /** Se enseña al pasar el ratón (`razon_principal`). */
  razon?: string | null
}) {
  if (puntuacion === null || puntuacion === undefined || !banda || !TONO[banda]) {
    return <span className="text-[#9aa39e]">—</span>
  }
  return (
    <span
      title={razon ?? undefined}
      aria-label={`Confianza ${Math.round(puntuacion)}, ${banda}${razon ? `: ${razon}` : ''}`}
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[12px] font-semibold tabular-nums whitespace-nowrap ${TONO[banda]}`}
    >
      {Math.round(puntuacion)}
      <span className="text-[11px] font-medium opacity-80">{banda}</span>
    </span>
  )
}
