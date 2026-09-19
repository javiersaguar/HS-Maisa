import Link from 'next/link'
import type { BandaConfianza, ConfianzaDuda, ConfianzaFicha } from '@/lib/types'
import { AVISO_LABELS, frase } from '@/lib/format'
import { ficheroHref } from '@/lib/routes'
import { ConfianzaChip } from './ConfianzaChip'

/*
 * «¿Cuánto nos fiamos?» (K3) para una ficha de `/confianza/fichero`, contada para una persona y sin puntos:
 * la puntuación agrupa arquetipos y no mide un intervalo, así que aquí sólo se enseña la banda y, en palabras,
 * qué hace dudar, qué la respalda y qué se anotó sin que cuente. Los pesos siguen en la API y en ADR-0014.
 */

/** De dónde sale cada frase, en palabras de Alberto. Orden de `fuentes` en docs/api/confianza.md. */
const FUENTE: Record<string, string> = {
  pdf: 'Lectura del PDF',
  coherencia: 'Importes',
  maestro: 'Maestro de proveedores',
  erp: 'ERP',
  decision: 'Decisión',
  politica: 'Pregunta abierta',
  revisor: 'Segunda opinión',
}
const ORDEN = Object.keys(FUENTE)

const CALLOUT: Record<BandaConfianza, string> = {
  alta: 'border-accent-line bg-accent-soft text-accent-dark',
  media: 'border-warn-line bg-warn-soft text-warn',
  baja: 'border-bad-line bg-bad-soft text-bad',
}

const OPINION: Record<string, string> = {
  de_acuerdo: 'está de acuerdo con la clasificación',
  desacuerdo: 'no está de acuerdo con la clasificación',
  no_se: 'no lo tiene claro',
}

/** Cuánto pesa una duda, en palabras. Los cortes siguen los pesos de `confianza/modelo.py` (5-55). */
function peso(aplicado: number): { texto: string; clase: string } {
  if (aplicado >= 20) return { texto: 'pesa mucho', clase: 'bg-bad-soft text-bad' }
  if (aplicado >= 10) return { texto: 'pesa bastante', clase: 'bg-warn-soft text-warn' }
  return { texto: 'pesa poco', clase: 'bg-raised text-ink-soft' }
}

/** `por_que` es la frase para personas; se le quitan referencias internas (ADR, pesos) y la pregunta va aparte. */
function explicar(duda: ConfianzaDuda): { texto: string; pregunta: string | null } {
  const base = duda.por_que || duda.texto
  const pregunta = base.match(/\((Q\d+)\)/)?.[1] ?? null
  const texto = base
    .replace(/\s*\((Q\d+)\)/g, '')
    .replace(/\s*\([^()]*(ADR|por aviso)[^()]*\)/g, '')
    .trim()
  return { texto: frase(texto.endsWith('.') ? texto : `${texto}.`), pregunta }
}

/** «se escala por: anomalía…: texto_instruccion, discrepancia_extractores · el documento dice: "…"» → frase. */
function respaldo(texto: string): string {
  const [principal] = texto.split(' · el documento dice:')
  const legible = principal.replace(/\b[a-z]+(?:_[a-z]+)+\b/g, (codigo) =>
    codigo in AVISO_LABELS ? AVISO_LABELS[codigo as keyof typeof AVISO_LABELS].toLowerCase() : codigo.replace(/_/g, ' '),
  )
  return frase(legible.endsWith('.') ? legible : `${legible}.`)
}

function Fuente({ clave }: { clave: string }) {
  return <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">{FUENTE[clave] ?? clave}</span>
}

export function ConfianzaTarjeta({ ficha }: { ficha: ConfianzaFicha }) {
  const fuentes = ORDEN.filter((clave) => ficha.fuentes[clave]).map((clave) => [clave, ficha.fuentes[clave]] as const)

  const dudas = fuentes
    .flatMap(([clave, fuente]) => fuente.dudas.map((duda) => ({ clave, duda })))
    .sort((a, b) => b.duda.aplicado - a.duda.aplicado)
  const cuentan = dudas.filter(({ duda }) => duda.aplicado > 0)
  const anotadas = dudas.filter(({ duda }) => duda.aplicado <= 0)
  const aFavor = fuentes.flatMap(([clave, fuente]) => fuente.a_favor.map((texto) => ({ clave, texto })))
  const opinion = ficha.fuentes.revisor?.opinion

  return (
    <section className="mt-4 rounded-xl border border-line bg-surface p-4 animate-in fade-in duration-300">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-[13px] font-bold uppercase tracking-wide">¿Cuánto nos fiamos?</h3>
        <ConfianzaChip banda={ficha.banda} />
      </div>
      <p className="mt-1 text-[12px] text-muted">Confianza en la clasificación, no probabilidad de pago.</p>

      <p className={`mt-3 rounded-lg border px-3 py-2 text-[13px] font-semibold leading-5 ${CALLOUT[ficha.banda]}`}>
        {frase(ficha.causa)}.
      </p>

      {cuentan.length > 0 && (
        <div className="mt-4">
          <h4 className="text-[12px] font-bold text-ink">Qué nos hace dudar</h4>
          <ul className="mt-2 flex flex-col gap-2.5">
            {cuentan.map(({ clave, duda }) => {
              const { texto, pregunta } = explicar(duda)
              const { texto: cuanto, clase } = peso(duda.aplicado)
              return (
                <li key={duda.id} className="flex flex-col gap-0.5">
                  <span className="flex flex-wrap items-center gap-2">
                    <Fuente clave={clave} />
                    <span className={`rounded-full px-1.5 py-px text-[11px] font-semibold ${clase}`}>{cuanto}</span>
                    {pregunta && (
                      <span className="rounded-full border border-line px-1.5 py-px text-[11px] font-semibold text-ink-soft">
                        pendiente del mentor · {pregunta}
                      </span>
                    )}
                  </span>
                  <span className="text-[13px] leading-5 text-ink-soft">{texto}</span>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {aFavor.length > 0 && (
        <div className="mt-4">
          <h4 className="text-[12px] font-bold text-ink">Lo que la respalda</h4>
          <ul className="mt-2 flex flex-col gap-2">
            {aFavor.map(({ clave, texto }) => (
              <li key={`${clave}-${texto}`} className="flex gap-2 text-[13px] leading-5 text-ink-soft">
                <span aria-hidden className="mt-px font-bold text-accent-dark">
                  ✓
                </span>
                <span className="flex flex-col gap-0.5">
                  <Fuente clave={clave} />
                  {respaldo(texto)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {opinion && (
        <p className="mt-4 text-[13px] leading-5 text-ink-soft">
          <Fuente clave="revisor" />
          <span className="block">
            Un segundo modelo {OPINION[opinion.opinion] ?? opinion.opinion}: {opinion.frase}
          </span>
        </p>
      )}

      {cuentan.length === 0 && aFavor.length === 0 && !opinion && (
        <ul className="mt-3 flex list-disc flex-col gap-1 pl-5 text-[13px] leading-5 text-ink-soft">
          {ficha.razones.slice(0, 3).map((razon) => (
            <li key={razon}>{frase(razon)}</li>
          ))}
        </ul>
      )}

      {anotadas.length > 0 && (
        <details className="group mt-4 rounded-lg border border-line-soft px-3 py-2 text-[12px] text-ink-soft">
          <summary className="cursor-pointer font-semibold text-ink-soft">
            También se anotó, pero no cambia la confianza ({anotadas.length})
          </summary>
          <ul className="mt-2 flex flex-col gap-1.5">
            {anotadas.map(({ clave, duda }) => (
              <li key={duda.id} className="leading-5">
                {explicar(duda).texto}{' '}
                <span className="text-muted">
                  {[duda.factor === 0 ? 'No se cuenta dos veces: ya es el motivo por el que se escala' : null, FUENTE[clave] ?? clave]
                    .filter(Boolean)
                    .join(' · ')}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}

      {ficha.mismo_pdf_que.length > 0 && (
        <p className="mt-3 text-[12px] text-ink-soft">
          Es el mismo PDF que{' '}
          {ficha.mismo_pdf_que.map((otro, index) => (
            <span key={otro}>
              {index > 0 && ', '}
              <Link href={ficheroHref(otro)} className="font-mono font-semibold text-accent-dark underline">
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
