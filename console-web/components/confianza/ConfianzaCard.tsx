'use client'

import { useConfianzaFicha } from '@/hooks/useConfianza'
import { frase } from '@/lib/format'
import { ConfianzaBadge } from './ConfianzaBadge'

/** Nombres de `fuentes` (docs/api/confianza.md) en el orden en que se leen. */
const FUENTES: Array<[string, string]> = [
  ['pdf', 'PDF'],
  ['coherencia', 'Importes'],
  ['maestro', 'Maestro'],
  ['erp', 'ERP'],
  ['decision', 'Decisión'],
  ['politica', 'Políticas abiertas'],
  ['revisor', 'Revisor'],
]

const puntos = (valor: number) => (Number.isInteger(valor) ? String(valor) : valor.toFixed(1).replace('.', ','))

/**
 * «¿Cuánto nos fiamos?» (K3). Sólo aparece si `/confianza/fichero` responde; si no, no ocupa sitio.
 */
export function ConfianzaCard({ fileId }: { fileId: string }) {
  const { data: ficha } = useConfianzaFicha(fileId)
  if (!ficha) return null

  return (
    <section className="mt-4 rounded-xl border border-[#e4e5df] bg-white p-4 animate-in fade-in duration-300">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-[13px] font-bold uppercase tracking-wide">¿Cuánto nos fiamos?</h3>
        <ConfianzaBadge puntuacion={ficha.puntuacion} banda={ficha.banda} />
      </div>
      <p className="mt-1 text-[12px] text-[#8a958e]">Confianza en la clasificación, no probabilidad de pago.</p>
      <p className="mt-3 text-[13px] font-semibold text-[#203b31]">{frase(ficha.causa)}.</p>
      <ul className="mt-2 flex list-disc flex-col gap-1 pl-5 text-[13px] leading-5 text-[#52605a]">
        {ficha.razones.map((razon) => (
          <li key={razon}>{frase(razon)}</li>
        ))}
      </ul>
      <dl className="mt-3 divide-y divide-[#edf0ec] border-t border-[#edf0ec] text-[12px]">
        {FUENTES.filter(([clave]) => ficha.fuentes[clave]).map(([clave, label]) => {
          const fuente = ficha.fuentes[clave]
          const frases = [...fuente.dudas.filter((duda) => duda.aplicado > 0).map((duda) => duda.texto), ...fuente.a_favor]
          return (
            <div key={clave} className="grid grid-cols-[110px_minmax(0,1fr)_44px] items-start gap-2 py-1.5">
              <dt className="font-semibold text-[#52605a]">{label}</dt>
              <dd className="leading-5 text-[#68736d]">{frases.length ? frases.map(frase).join(' · ') : '—'}</dd>
              <dd
                className={`text-right font-semibold tabular-nums ${fuente.penalizacion > 0 ? 'text-[#bd3434]' : 'text-[#9aa39e]'}`}
              >
                {fuente.penalizacion > 0 ? `−${puntos(fuente.penalizacion)}` : '0'}
              </dd>
            </div>
          )
        })}
      </dl>
    </section>
  )
}
