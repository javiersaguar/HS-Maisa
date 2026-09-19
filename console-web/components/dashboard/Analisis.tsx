'use client'

import Link from 'next/link'
import { ArrowUpRight, ChevronLeft, ChevronRight, FileSearch } from 'lucide-react'
import { useConfianzaFichero } from '@/hooks/useConfianza'
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
import { ConfianzaChip } from '@/components/confianza/ConfianzaChip'
import { ResultadoTitular } from '@/components/ui/Resultado'
import { ErrorState, LoadingState } from '@/components/ui/states'

/** Una regla de la norma, con su evidencia en palabras. Es el argumento, no un adorno. */
function Regla({ motivo }: { motivo: Motivo }) {
  const evidencia = describirEvidencia(motivo.evidencia)
  // Mismo código que la ficha: salvia si cumple, rojo si al fallar impide pagar, ámbar si sólo escala.
  const punto = motivo.ok ? 'bg-accent' : motivo.evidencia.no_pagar ? 'bg-bad' : 'bg-warn'
  const aviso = motivo.evidencia.no_pagar ? 'text-bad' : 'text-warn'
  return (
    <li className="flex gap-2.5 border-t border-line-soft py-3 first:border-t-0 first:pt-0">
      <span aria-hidden className={`mt-[6px] size-2 shrink-0 rounded-full ${punto}`} />
      <div className="min-w-0">
        <p className="text-[13px] font-medium text-ink">
          {tituloRegla(motivo.regla_id)}
          {!motivo.ok && (
            <span className={`ml-2 text-[12px] font-normal ${aviso}`}>
              {motivo.evidencia.no_pagar ? 'no se cumple · impide pagar' : 'no se cumple'}
            </span>
          )}
        </p>
        <p className="mt-1 text-[14px] leading-relaxed text-ink-soft">{frase(motivo.detalle)}</p>
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
      <dt className="text-[12px] text-muted">{label}</dt>
      <dd className="mt-0.5 truncate text-[14px] text-ink tabular-nums" title={typeof children === 'string' ? children : undefined}>
        {children ?? '—'}
      </dd>
    </div>
  )
}

function Seccion({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="mt-6 border-t border-line-soft pt-5">
      <h3 className="text-[13px] font-semibold text-ink">{titulo}</h3>
      {children}
    </section>
  )
}

function Contenido({ fichero }: { fichero: Fichero }) {
  const { decision, hechos, fuentes } = fichero
  const { data: confianza } = useConfianzaFichero(decision ? fichero.file_id : null)
  const motivos = decision?.motivos ?? []
  const fallan = motivos.filter((m) => !m.ok)
  const cumplen = motivos.filter((m) => m.ok)
  const asiento = fuentes?.asientos?.[0] ?? null

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
        <div className="min-w-0">
          <h2 className="truncate font-mono text-[14px] font-medium text-ink" title={fichero.file_id}>
            {fichero.file_id}
          </h2>
          <p className="mt-1 text-[12px] text-muted">
            {loteNombre(fichero.lote)}
            {hechos ? ` · leída por ${METODO_LABELS[hechos.metodo].toLowerCase()}` : ''}
          </p>
        </div>
        <Link
          href={ficheroHref(fichero.file_id)}
          className="flex shrink-0 items-center gap-1 rounded-lg border border-line px-2.5 py-1.5 text-[13px] font-medium text-accent-dark transition hover:border-accent hover:bg-accent-soft"
        >
          Ficha completa
          <ArrowUpRight className="size-3.5" />
        </Link>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 pt-5 pb-20">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <ResultadoTitular estado={fichero.estado} />
          {confianza && (
            <p className="flex items-center gap-2 text-[12px] text-muted">
              Confianza
              <ConfianzaChip banda={confianza.banda} razon={confianza.razones[0]} />
            </p>
          )}
        </div>

        {decision ? (
          <>
            {resumenReglas(decision) ? (
              <p className="mt-5 rounded-lg bg-canvas px-4 py-3 text-[14px] leading-relaxed text-ink-soft">
                {resumenReglas(decision)}
              </p>
            ) : null}

            {fallan.length > 0 && (
              <Seccion titulo={fallan.length === 1 ? 'Qué ha fallado' : `Qué ha fallado (${fallan.length})`}>
                <ul className="mt-3">
                  {fallan.map((m) => (
                    <Regla key={m.regla_id} motivo={m} />
                  ))}
                </ul>
              </Seccion>
            )}

            {hechos?.texto_sospechoso && (
              <figure className="mt-5 rounded-lg border border-warn-line bg-warn-soft px-4 py-3">
                <figcaption className="text-[13px] font-semibold text-warn">
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
          </>
        ) : (
          <p className="mt-5 rounded-lg bg-canvas px-4 py-3 text-[14px] leading-relaxed text-ink-soft">
            No hay decisión vigente. El PDF no se ha podido leer, así que la norma no se ha aplicado: no se inventa un
            resultado.
          </p>
        )}

        {hechos && (
          <Seccion titulo="Lo que dice la factura">
            <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
              <Dato label="Nº factura">{hechos.num_factura}</Dato>
              <Dato label="Fecha">{formatDate(hechos.fecha)}</Dato>
              <Dato label="Pedido">{hechos.pedido}</Dato>
              <Dato label="Emisor">{hechos.razon_social ?? hechos.nif_emisor}</Dato>
              <Dato label="NIF">{hechos.nif_emisor}</Dato>
              <Dato label="IBAN">{hechos.iban}</Dato>
              <Dato label="Base">{formatAmount(hechos.base, hechos.moneda)}</Dato>
              <Dato label="IVA">{formatAmount(hechos.iva, hechos.moneda)}</Dato>
              <Dato label="Total">{formatAmount(hechos.total, hechos.moneda)}</Dato>
            </dl>
          </Seccion>
        )}

        {(fuentes?.proveedor || fuentes?.pedido || asiento) && (
          <Seccion titulo="Contra lo que se ha cruzado">
            <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
              <Dato label="Proveedor del maestro">{fuentes?.proveedor?.razon_social}</Dato>
              <Dato label="IBAN del maestro">{fuentes?.proveedor?.iban}</Dato>
              <Dato label="Importe del pedido">{formatAmount(fuentes?.pedido?.importe_total ?? null)}</Dato>
              <Dato label="Asiento ERP">{asiento?.asiento_id}</Dato>
              <Dato label="Estado en el ERP">{asiento?.estado}</Dato>
              <Dato label="Importe que espera">{formatAmount(asiento?.importe_esperado ?? null)}</Dato>
            </dl>
          </Seccion>
        )}

        {cumplen.length > 0 && (
          <details className="group mt-6 border-t border-line-soft pt-4">
            <summary className="cursor-pointer text-[13px] font-medium text-muted transition hover:text-ink">
              Lo que sí cumple ({cumplen.length})
            </summary>
            <ul className="mt-3">
              {cumplen.map((m) => (
                <Regla key={m.regla_id} motivo={m} />
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  )
}

/** Con más de un PDF la tarjeta es un carrusel: flechas, «n de N» y un punto por factura. */
function Carrusel({
  fileId,
  fileIds,
  onSelect,
}: {
  fileId: string
  fileIds: string[]
  onSelect: (fileId: string) => void
}) {
  const indice = fileIds.indexOf(fileId)
  const ir = (delta: number) => {
    const base = indice < 0 ? 0 : indice
    onSelect(fileIds[(base + delta + fileIds.length) % fileIds.length])
  }
  const flecha =
    'flex size-7 min-h-0 items-center justify-center rounded-full border border-line bg-surface text-ink-soft transition hover:border-accent hover:bg-accent-soft hover:text-accent-dark'

  return (
    <div
      role="group"
      aria-roledescription="carrusel"
      aria-label="Facturas subidas"
      onKeyDown={(event) => {
        if (event.key === 'ArrowLeft') ir(-1)
        if (event.key === 'ArrowRight') ir(1)
      }}
      className="flex shrink-0 items-center gap-3 border-b border-line bg-canvas px-5 py-2"
    >
      <button type="button" onClick={() => ir(-1)} aria-label="Factura anterior" className={flecha}>
        <ChevronLeft className="size-4" />
      </button>
      <div className="flex min-w-0 flex-1 flex-wrap items-center justify-center gap-1.5">
        {fileIds.map((id, i) => (
          <button
            key={id}
            type="button"
            onClick={() => onSelect(id)}
            aria-label={`Factura ${i + 1}: ${id}`}
            aria-current={id === fileId ? 'true' : undefined}
            title={id}
            className={`h-1.5 min-h-0 rounded-full transition-all ${id === fileId ? 'w-5 bg-accent-dark' : 'w-1.5 bg-line hover:bg-muted'}`}
          />
        ))}
      </div>
      <span className="shrink-0 text-[12px] text-muted tabular-nums">
        {indice < 0 ? '—' : indice + 1} de {fileIds.length}
      </span>
      <button type="button" onClick={() => ir(1)} aria-label="Factura siguiente" className={flecha}>
        <ChevronRight className="size-4" />
      </button>
    </div>
  )
}

/** Tarjeta derecha de la portada: por qué esa factura sale PAGAR, NO_PAGAR, ESCALAR o PENDIENTE. */
export function Analisis({
  fileId,
  fileIds = [],
  onSelect,
}: {
  fileId: string | null
  /** Las facturas subidas y decididas; con más de una se recorren como cartas. */
  fileIds?: string[]
  onSelect?: (fileId: string) => void
}) {
  if (fileId && onSelect && fileIds.length > 1) {
    return (
      <>
        <Carrusel fileId={fileId} fileIds={fileIds} onSelect={onSelect} />
        <div key={fileId} className="flex min-h-0 flex-1 flex-col animate-in fade-in slide-in-from-right-2 duration-200">
          <Carta fileId={fileId} />
        </div>
      </>
    )
  }
  return <Carta fileId={fileId} />
}

function Carta({ fileId }: { fileId: string | null }) {
  const { data, error, initialLoading, refresh, loading } = useFichero(fileId ?? '')

  if (!fileId) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-8 py-16 text-center">
        <span className="flex size-11 items-center justify-center rounded-2xl bg-accent-soft text-accent-dark">
          <FileSearch className="size-5" />
        </span>
        <p className="mt-4 max-w-[36ch] text-[15px] font-semibold text-ink">
          Aquí verás qué decide la norma y por qué
        </p>
        <p className="mt-2 max-w-[44ch] text-[14px] leading-relaxed text-muted">
          Sube facturas a la izquierda y elige una de la lista. Se cruzan tres fuentes: el PDF, el maestro de
          proveedores y el ERP de 2009. La consola no decide nada, sólo enseña lo que la norma dejó escrito.
        </p>
      </div>
    )
  }

  if (error) return <ErrorState error={error} onRetry={refresh} retrying={loading} />
  if (initialLoading || !data) return <LoadingState label="Leyendo la decisión" rows={5} />

  return <Contenido fichero={data} />
}
