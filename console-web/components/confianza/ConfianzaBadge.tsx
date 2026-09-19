import type { BandaConfianza } from '@/lib/types'

/*
 * Confianza en la CLASIFICACIÓN (K3), no probabilidad de pago ni `InvoiceFacts.confianza` (lectura).
 * Chip con el número y la banda; la banda va en texto además de en color.
 */
const TONO: Record<BandaConfianza, string> = {
  alta: 'border-[#dcefe6] bg-[#eff8f3] text-[#176d59]',
  media: 'border-[#eee8bd] bg-[#fffbe8] text-[#8a7400]',
  baja: 'border-[#f1dada] bg-[#fff0f0] text-[#bd3434]',
}

export function ConfianzaBadge({
  puntuacion,
  banda,
  title,
}: {
  puntuacion: number
  banda: BandaConfianza
  title?: string
}) {
  return (
    <span
      title={title ? `${title} · confianza en la clasificación, no probabilidad de pago` : undefined}
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[12px] font-semibold tabular-nums whitespace-nowrap ${TONO[banda]}`}
    >
      {Math.round(puntuacion)}
      <span className="text-[11px] font-medium opacity-80">{banda}</span>
    </span>
  )
}
