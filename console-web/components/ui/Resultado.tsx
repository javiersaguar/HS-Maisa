import type { EstadoFichero } from '@/lib/types'

/**
 * Resultado vigente de la norma. El color vive sólo en el punto y en el texto: ni fondos teñidos,
 * ni pastillas, ni medallones. Se usa igual en la bandeja y en el panel de análisis.
 */
const ESTILOS: Record<EstadoFichero, { punto: string; texto: string; verbo: string }> = {
  PAGAR: { punto: 'bg-ok', texto: 'text-ok', verbo: 'Se paga' },
  ESCALAR: { punto: 'bg-warn', texto: 'text-warn', verbo: 'Lo revisa una persona' },
  NO_PAGAR: { punto: 'bg-bad', texto: 'text-bad', verbo: 'No se paga' },
  PENDIENTE: { punto: 'bg-faint', texto: 'text-muted', verbo: 'Sin decisión todavía' },
}

export function estiloResultado(estado: EstadoFichero) {
  return ESTILOS[estado]
}

export const ORDEN_RESULTADOS: EstadoFichero[] = ['PAGAR', 'ESCALAR', 'NO_PAGAR', 'PENDIENTE']

/** Cabecera del análisis: la palabra y la frase de qué implica. */
export function ResultadoTitular({ estado }: { estado: EstadoFichero }) {
  const e = ESTILOS[estado]
  return (
    <div>
      <p className="text-[12px] text-muted">Decisión de la norma</p>
      <p className={`mt-1.5 flex items-center gap-2.5 text-[24px] font-semibold tracking-[-0.02em] ${e.texto}`}>
        <span aria-hidden className={`size-2.5 shrink-0 rounded-full ${e.punto}`} />
        {estado}
      </p>
      <p className="mt-1 text-[13px] text-muted">{e.verbo}</p>
    </div>
  )
}

/** Marca compacta para una fila de la bandeja: punto de color y palabra. */
export function ResultadoMarca({ estado }: { estado: EstadoFichero | null }) {
  if (!estado) return <span className="text-[12px] text-faint">leyendo…</span>
  const e = ESTILOS[estado]
  return (
    <span className={`flex items-center gap-2 text-[12px] font-medium ${e.texto}`}>
      <span aria-hidden className={`size-2 shrink-0 rounded-full ${e.punto}`} />
      {estado}
    </span>
  )
}

/**
 * Recuento de un conjunto de facturas. Sólo aparecen los resultados que existen: un lote de tres
 * facturas no debe enseñar tres ceros.
 */
export function RecuentoResultados({
  porEstado,
  sinLeer = 0,
}: {
  porEstado: Partial<Record<EstadoFichero, number>>
  sinLeer?: number
}) {
  const visibles = ORDEN_RESULTADOS.filter((estado) => (porEstado[estado] ?? 0) > 0)
  if (visibles.length === 0 && sinLeer === 0) return null
  return (
    <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-muted cifra">
      {visibles.map((estado, i) => {
        const e = ESTILOS[estado]
        return (
          <span key={estado} className="flex items-center gap-2">
            {i > 0 && <span className="text-line">·</span>}
            <span aria-hidden className={`size-2 shrink-0 rounded-full ${e.punto}`} />
            <span className={e.texto}>
              {porEstado[estado]} {estado}
            </span>
          </span>
        )
      })}
      {sinLeer > 0 && (
        <span className="flex items-center gap-2">
          {visibles.length > 0 && <span className="text-line">·</span>}
          {sinLeer} leyendo
        </span>
      )}
    </p>
  )
}
