import type { EstadoFichero } from '@/lib/types'

/**
 * Resultado vigente de la norma, sin pastillas redondeadas: una barra de color a la izquierda y la
 * palabra. Se usa en la bandeja (compacto) y en el panel de análisis (grande) para que la misma
 * decisión se lea igual en los dos sitios.
 */
const ESTILOS: Record<EstadoFichero, { barra: string; texto: string; fondo: string; verbo: string }> = {
  PAGAR: { barra: 'bg-[#0f8a63]', texto: 'text-[#0b6b4d]', fondo: 'bg-[#f2faf6]', verbo: 'Se paga' },
  ESCALAR: { barra: 'bg-[#c79a15]', texto: 'text-[#856400]', fondo: 'bg-[#fffaec]', verbo: 'Lo revisa una persona' },
  NO_PAGAR: { barra: 'bg-[#c0453f]', texto: 'text-[#a3302b]', fondo: 'bg-[#fdf3f2]', verbo: 'No se paga' },
  PENDIENTE: { barra: 'bg-[#a4ada7]', texto: 'text-[#5d665f]', fondo: 'bg-[#f5f7f4]', verbo: 'Sin decisión todavía' },
}

export function estiloResultado(estado: EstadoFichero) {
  return ESTILOS[estado]
}

/** Cabecera del análisis: la palabra grande con su barra y la frase de qué implica. */
export function ResultadoTitular({ estado }: { estado: EstadoFichero }) {
  const e = ESTILOS[estado]
  return (
    <div className={`flex items-stretch gap-4 rounded-lg ${e.fondo} p-4`}>
      <span aria-hidden className={`w-1 shrink-0 rounded-sm ${e.barra}`} />
      <div className="min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#8b9790]">Decisión de la norma</p>
        <p className={`mt-1 text-[30px] font-semibold leading-none tracking-[-0.03em] ${e.texto}`}>{estado}</p>
        <p className="mt-1.5 text-[14px] text-[#59635e]">{e.verbo}</p>
      </div>
    </div>
  )
}

/** Marca compacta para una fila de la bandeja. Barra vertical + palabra, nunca una pastilla. */
export function ResultadoMarca({ estado }: { estado: EstadoFichero | null }) {
  if (!estado) return <span className="text-[12px] text-[#a1aaa5]">leyendo…</span>
  const e = ESTILOS[estado]
  return (
    <span className="flex items-center gap-2">
      <span aria-hidden className={`h-3.5 w-[3px] rounded-sm ${e.barra}`} />
      <span className={`text-[12px] font-semibold tracking-[0.02em] ${e.texto}`}>{estado}</span>
    </span>
  )
}
