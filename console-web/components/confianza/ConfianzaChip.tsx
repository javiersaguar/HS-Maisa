import type { BandaConfianza } from '@/lib/types'

/*
 * Confianza en la CLASIFICACIÓN (K3), no probabilidad de pago ni `InvoiceFacts.confianza` (lectura).
 * Sólo la banda, en texto: el color no es la única señal. La puntuación no se enseña aquí porque agrupa
 * arquetipos, no mide un intervalo; el desglose con puntos está en ConfianzaTarjeta. Paleta de StatusBadge.
 */
const TONO: Record<BandaConfianza, string> = {
  alta: 'bg-accent-soft text-accent-dark',
  media: 'bg-warn-soft text-warn',
  baja: 'bg-bad-soft text-bad',
}

export function ConfianzaChip({
  banda,
  razon,
}: {
  banda?: BandaConfianza | null
  /** Se enseña al pasar el ratón (`razon_principal`). */
  razon?: string | null
}) {
  if (!banda || !TONO[banda]) return <span className="text-muted">—</span>
  return (
    <span
      title={razon ? `Confianza ${banda}: ${razon}` : `Confianza ${banda}`}
      aria-label={`Confianza ${banda}${razon ? `: ${razon}` : ''}`}
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[12px] font-semibold whitespace-nowrap ${TONO[banda]}`}
    >
      {banda}
    </span>
  )
}
