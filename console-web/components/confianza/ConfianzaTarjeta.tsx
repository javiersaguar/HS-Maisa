import Link from 'next/link'
import type { ConfianzaFicha } from '@/lib/types'
import { frase } from '@/lib/format'
import { ficheroHref } from '@/lib/routes'
import { ConfianzaChip } from './ConfianzaChip'

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

const OPINION: Record<string, string> = { de_acuerdo: 'de acuerdo', desacuerdo: 'en desacuerdo', no_se: 'no lo sabe' }

const puntos = (valor: number) => (Number.isInteger(valor) ? String(valor) : valor.toFixed(1).replace('.', ','))

/**
 * «¿Cuánto nos fiamos?» (K3) para una ficha de `/confianza/fichero`. Quien la monta decide si hay ficha:
 * sin ella (404, sin decisión vigente, K3 caído) no se pinta.
 */
export function ConfianzaTarjeta({ ficha }: { ficha: ConfianzaFicha }) {
  return (
    <section className="mt-4 rounded-xl border border-[#e4e5df] bg-white p-4 animate-in fade-in duration-300">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-[13px] font-bold uppercase tracking-wide">¿Cuánto nos fiamos?</h3>
        <ConfianzaChip banda={ficha.banda} />
      </div>
      <p className="mt-1 text-[12px] text-[#8a958e]">Confianza en la clasificación, no probabilidad de pago.</p>
      <p className="mt-3 text-[13px] font-semibold text-[#203b31]">{frase(ficha.causa)}.</p>
      <ul className="mt-2 flex list-disc flex-col gap-1 pl-5 text-[13px] leading-5 text-[#52605a]">
        {ficha.razones.slice(0, 3).map((razon) => (
          <li key={razon}>{frase(razon)}</li>
        ))}
      </ul>

      <dl className="mt-3 divide-y divide-[#edf0ec] border-t border-[#edf0ec] text-[12px]">
        {FUENTES.filter(([clave]) => ficha.fuentes[clave]).map(([clave, label]) => {
          const fuente = ficha.fuentes[clave]
          const vacia = !fuente.dudas.length && !fuente.a_favor.length && !fuente.opinion
          return (
            <div key={clave} className="grid grid-cols-[110px_minmax(0,1fr)_44px] items-start gap-2 py-1.5">
              <dt className="font-semibold text-[#52605a]">{label}</dt>
              <dd className="flex flex-col gap-0.5 leading-5 text-[#68736d]">
                {fuente.dudas.map((duda) =>
                  duda.aplicado > 0 ? (
                    <span key={duda.id} title={duda.por_que}>
                      {frase(duda.texto)} <span className="font-semibold text-[#bd3434] tabular-nums">−{puntos(duda.aplicado)}</span>
                    </span>
                  ) : (
                    <span key={duda.id} className="text-[#a9b1ac]">
                      <span className="line-through decoration-[#c9d0cb]">{frase(duda.texto)}</span>{' '}
                      <span className="tabular-nums">(0 de {puntos(duda.puntos)})</span>
                      <span className="block text-[11px] italic">{duda.por_que}</span>
                    </span>
                  ),
                )}
                {fuente.a_favor.map((texto) => (
                  <span key={texto} className="text-[#176d59]">
                    ✓ {frase(texto)}
                  </span>
                ))}
                {fuente.opinion && (
                  <span>
                    Segunda opinión {OPINION[fuente.opinion.opinion] ?? fuente.opinion.opinion}: {fuente.opinion.frase}
                  </span>
                )}
                {vacia && <span className="text-[#a9b1ac]">—</span>}
              </dd>
              <dd
                className={`text-right font-semibold tabular-nums ${fuente.penalizacion > 0 ? 'text-[#bd3434]' : 'text-[#9aa39e]'}`}
              >
                {fuente.penalizacion > 0 ? `−${puntos(fuente.penalizacion)}` : '0'}
              </dd>
            </div>
          )
        })}
      </dl>

      {ficha.mismo_pdf_que.length > 0 && (
        <p className="mt-3 text-[12px] text-[#68736d]">
          Mismo PDF que{' '}
          {ficha.mismo_pdf_que.map((otro, index) => (
            <span key={otro}>
              {index > 0 && ', '}
              <Link href={ficheroHref(otro)} className="font-mono font-semibold text-[#176d59] underline">
                {otro}
              </Link>
            </span>
          ))}
          .
        </p>
      )}
    </section>
  )
}
