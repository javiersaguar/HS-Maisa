'use client'

import Link from 'next/link'
import { ArrowUpRight, FileSearch } from 'lucide-react'
import { useFichero } from '@/hooks/useFicheros'
import type { Fichero, Motivo } from '@/lib/types'
import {
  describirEvidencia,
  formatAmount,
  formatDate,
  frase,
  loteNombre,
  METODO_LABELS,
  resumenReglas,
  tituloRegla,
} from '@/lib/format'
import { ficheroHref } from '@/lib/routes'
import { ResultadoTitular } from '@/components/ui/Resultado'
import { ErrorCard, LoadingCard } from '@/components/ui/states'

/** Una regla de la norma, con su evidencia en palabras. Es el argumento, no un adorno. */
function Regla({ motivo }: { motivo: Motivo }) {
  const evidencia = describirEvidencia(motivo.evidencia)
  return (
    <li className="flex gap-2.5 border-t border-line-soft py-3 first:border-t-0 first:pt-0">
      <span
        aria-hidden
        className={`mt-[5px] size-2 shrink-0 rounded-full ${motivo.ok ? 'bg-line' : 'bg-warn'}`}
      />
      <div className="min-w-0">
        <p className="text-[12px] text-muted">
          {tituloRegla(motivo.regla_id)}
          {!motivo.ok && <span className="ml-2 text-warn">no se cumple</span>}
        </p>
        <p className="mt-1 text-[13px] leading-relaxed text-ink-soft">{frase(motivo.detalle)}</p>
        {evidencia.length > 0 && (
          <ul className="mt-1.5 space-y-0.5">
            {evidencia.map((linea) => (
              <li key={linea} className="text-[13px] leading-relaxed text-muted">
                {linea}
              </li>
            ))}
          </ul>
        )}
      </div>
    </li>
  )
}

function Dato({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <p className="text-[12px] text-muted">{label}</p>
      <p className="mt-1 truncate text-[13px] text-ink cifra">{children ?? '—'}</p>
    </div>
  )
}

function Contenido({ fichero }: { fichero: Fichero }) {
  const { decision, hechos, fuentes } = fichero
  const motivos = decision?.motivos ?? []
  const fallan = motivos.filter((m) => !m.ok)
  const cumplen = motivos.filter((m) => m.ok)
  const asiento = fuentes?.asientos?.[0] ?? null

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
        <div className="min-w-0">
          <h2 className="truncate ident text-[14px] text-ink">{fichero.file_id}</h2>
          <p className="mt-1 text-[12px] text-muted">
            {loteNombre(fichero.lote)}
            {hechos ? ` · leída por ${METODO_LABELS[hechos.metodo].toLowerCase()}` : ''}
          </p>
        </div>
        <Link
          href={ficheroHref(fichero.file_id)}
          className="flex shrink-0 items-center gap-1 text-[13px] text-accent hover:underline"
        >
          Ficha completa
          <ArrowUpRight className="size-3.5" />
        </Link>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        <ResultadoTitular estado={fichero.estado} />

        {decision ? (
          <>
            <p className="mt-5 text-[14px] leading-relaxed text-ink-soft">{resumenReglas(decision)}</p>

            {fallan.length > 0 && (
              <ul className="mt-4">
                {fallan.map((m) => (
                  <Regla key={m.regla_id} motivo={m} />
                ))}
              </ul>
            )}

            {hechos?.texto_sospechoso && (
              <figure className="mt-5 border-l-2 border-warn py-1 pl-3">
                <figcaption className="text-[12px] font-medium text-warn">
                  El documento intenta decidir por su cuenta
                </figcaption>
                <blockquote className="mt-1.5 text-[13px] leading-relaxed text-ink-soft">
                  «{hechos.texto_sospechoso}»
                </blockquote>
                <p className="mt-1.5 text-[12px] text-muted">
                  Es un dato de la factura, no una orden: la decisión sale de la norma.
                </p>
              </figure>
            )}

            {cumplen.length > 0 && (
              <details className="mt-5 border-t border-line-soft pt-3">
                <summary className="cursor-pointer text-[13px] text-muted hover:text-ink">
                  Lo que sí cumple ({cumplen.length})
                </summary>
                <ul className="mt-3">
                  {cumplen.map((m) => (
                    <Regla key={m.regla_id} motivo={m} />
                  ))}
                </ul>
              </details>
            )}
          </>
        ) : (
          <p className="mt-5 text-[14px] leading-relaxed text-ink-soft">
            No hay decisión vigente. El PDF no se ha podido leer, así que la norma no se ha aplicado: no se inventa un
            resultado.
          </p>
        )}

        {hechos && (
          <section className="mt-6 border-t border-line-soft pt-5">
            <h3 className="text-[12px] text-muted">
              Lo que dice la factura
            </h3>
            <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
              <Dato label="Nº factura">{hechos.num_factura}</Dato>
              <Dato label="Fecha">{formatDate(hechos.fecha)}</Dato>
              <Dato label="Pedido">{hechos.pedido}</Dato>
              <Dato label="Emisor">{hechos.razon_social ?? hechos.nif_emisor}</Dato>
              <Dato label="NIF">{hechos.nif_emisor}</Dato>
              <Dato label="IBAN">{hechos.iban}</Dato>
              <Dato label="Base">{formatAmount(hechos.base)}</Dato>
              <Dato label="IVA">{formatAmount(hechos.iva)}</Dato>
              <Dato label="Total">{formatAmount(hechos.total)}</Dato>
            </div>
          </section>
        )}

        {(fuentes?.proveedor || fuentes?.pedido || asiento) && (
          <section className="mt-6 border-t border-line-soft pt-5">
            <h3 className="text-[12px] text-muted">
              Contra lo que se ha cruzado
            </h3>
            <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
              <Dato label="Proveedor del maestro">{fuentes?.proveedor?.razon_social}</Dato>
              <Dato label="IBAN del maestro">{fuentes?.proveedor?.iban}</Dato>
              <Dato label="Importe del pedido">{formatAmount(fuentes?.pedido?.importe_total ?? null)}</Dato>
              <Dato label="Asiento ERP">{asiento?.asiento_id}</Dato>
              <Dato label="Estado en el ERP">{asiento?.estado}</Dato>
              <Dato label="Importe que espera">{formatAmount(asiento?.importe_esperado ?? null)}</Dato>
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

/** Columna derecha: por qué esa factura sale PAGAR, NO_PAGAR, ESCALAR o PENDIENTE. */
export function Analisis({ fileId }: { fileId: string | null }) {
  const { data, error, initialLoading, refresh, loading } = useFichero(fileId ?? '')

  if (!fileId) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-8 py-16 text-center">
        <FileSearch className="size-7 text-line" />
        <p className="mt-4 max-w-[34ch] text-[14px] text-ink-soft">
          Elige una factura de la bandeja y aquí verás qué decide la norma y con qué argumentos.
        </p>
        <p className="mt-2 max-w-[42ch] text-[13px] leading-relaxed text-faint">
          Se cruzan tres fuentes: el PDF, el maestro de proveedores y el ERP de 2009. La consola no decide nada, sólo
          enseña lo que la norma dejó escrito.
        </p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <ErrorCard error={error} onRetry={refresh} retrying={loading} />
      </div>
    )
  }

  if (initialLoading || !data) {
    return (
      <div className="p-6">
        <LoadingCard label="Leyendo la decisión" rows={5} />
      </div>
    )
  }

  return <Contenido fichero={data} />
}
