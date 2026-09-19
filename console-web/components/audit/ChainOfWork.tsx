'use client'

import { useState, type ReactNode } from 'react'
import Link from 'next/link'
import { ChevronDown, Database, FileInput, Scale, ScanText, Send, ShieldCheck } from 'lucide-react'
import type { Etapa, PasoTraza } from '@/lib/types'
import { describirEvidencia, describirPasoEvento, frase, formatDateTime, formatTime, resultadoFrase, tituloEvento, tituloRegla } from '@/lib/format'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { EmptyState } from '@/components/ui/states'
import { EventoBadge } from '@/components/invoices/badges'
import { ficheroHref } from '@/lib/routes'

const ETAPA_ICONS: Record<Etapa, typeof FileInput> = {
  ingest: FileInput,
  extract: ScanText,
  validate: ShieldCheck,
  enrich: Database,
  decide: Scale,
  emit: Send,
}

type Nivel = 'pass' | 'warning' | 'fail' | 'info'

/** El color del nodo sigue al paso, para que un fallo destaque en una cadena larga. */
const NODE_CLASSES: Record<Nivel, string> = {
  pass: 'border-[#b8dfcf] text-[#176d59]',
  info: 'border-[#dfe4de] text-[#68736d]',
  warning: 'border-[#eee8bd] text-[#a87000]',
  fail: 'border-[#f1dada] text-[#bd3434]',
}

function nivel(paso: PasoTraza): Nivel {
  if (paso.tipo === 'motivo') return paso.motivo.ok ? 'pass' : paso.motivo.evidencia.no_pagar ? 'fail' : 'warning'
  const estado = paso.evento.estado
  if (estado === 'ok') return 'pass'
  if (estado === 'error') return 'fail'
  if (estado === 'skip') return 'info'
  return 'warning'
}

const PAGE_SIZE = 20

/**
 * La Chain of Work de Albertitos: cada paso es un evento de una etapa del pipeline (con latencia,
 * reintentos, tokens y coste) o una regla de la norma con su evidencia.
 *
 * Un componente, tres superficies: /audit, el detalle de fichero y el detalle de etapa.
 */
export function ChainOfWork({
  pasos,
  showDate = true,
  showFile = true,
  emptyTitle = 'Sin pasos registrados',
  emptyDescription = 'Los pasos aparecen cuando el pipeline procesa el fichero.',
  header,
}: {
  pasos: PasoTraza[]
  showDate?: boolean
  /** Muestra el file_id de cada paso. Apágalo dentro del detalle de un fichero. */
  showFile?: boolean
  emptyTitle?: string
  emptyDescription?: string
  header?: ReactNode
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [visible, setVisible] = useState(PAGE_SIZE)

  if (!pasos.length) {
    return (
      <>
        {header ? <div className="mb-3">{header}</div> : null}
        <EmptyState title={emptyTitle} description={emptyDescription} />
      </>
    )
  }

  const toggle = (id: string) =>
    setExpanded((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const shown = pasos.slice(0, visible)
  const allOpen = shown.every((paso) => expanded.has(paso.id))
  const when = (ts: string | null) => (showDate ? formatDateTime(ts) : formatTime(ts))

  return (
    <>
      <div className={`mb-3 flex items-start gap-3 ${header ? 'justify-between' : 'justify-end'}`}>
        {header ? <div className="min-w-0 flex-1">{header}</div> : null}
        <button
          onClick={() => setExpanded(allOpen ? new Set() : new Set(shown.map((paso) => paso.id)))}
          className="shrink-0 px-2 py-1 text-[13px] font-semibold text-[#315d53] transition"
        >
          {allOpen ? 'Plegar todo' : 'Desplegar evidencia'}
        </button>
      </div>
      <ol className="relative flex flex-col gap-3 before:absolute before:bottom-5 before:left-4 before:top-5 before:w-px before:bg-[#c8e3d6]">
        {shown.map((paso) => {
          const isOpen = expanded.has(paso.id)
          const Icon = paso.tipo === 'motivo' ? Scale : ETAPA_ICONS[paso.evento.etapa]

          let title: string
          let badge: ReactNode
          let meta: string[]
          let body: string | null
          let extra: string[] = []

          if (paso.tipo === 'motivo') {
            const { motivo } = paso
            title = `${tituloRegla(motivo.regla_id)} ${motivo.ok ? 'se cumple' : 'no se cumple'}`
            badge = (
              <StatusBadge tone={motivo.ok ? 'green' : motivo.evidencia.no_pagar ? 'red' : 'yellow'}>
                {motivo.ok ? 'Cumple' : 'Incumple'}
              </StatusBadge>
            )
            meta = [when(paso.ts), `Norma ${paso.norma_version}`]
            body = frase(motivo.detalle)
            extra = describirEvidencia(motivo.evidencia)
          } else {
            const { evento } = paso
            title = tituloEvento(evento)
            badge = <EventoBadge estado={evento.estado} />
            meta = [when(paso.ts)].filter(Boolean)
            body = describirPasoEvento(evento)
          }

          return (
            <li key={paso.id} className="relative pl-10 animate-in fade-in slide-in-from-bottom-1 duration-300">
              <span
                className={`absolute left-0 top-4 flex size-7 items-center justify-center border ${NODE_CLASSES[nivel(paso)]}`}
              >
                <Icon className="size-3.5" />
              </span>
              <div className="border border-[#e1e8e2] bg-white transition hover:-translate-y-0.5 hover:border-[#b8dcca] hover:">
                <button onClick={() => toggle(paso.id)} aria-expanded={isOpen} className="w-full p-4 text-left">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-[14px] font-semibold">{title}</h3>
                        {badge}
                      </div>
                      <p className="mt-1 text-[13px] text-[#8a958e]">
                        {meta.join(' · ')}
                        {showFile && paso.file_id ? (
                          <>
                            {' · '}
                            <span className="font-mono">{paso.file_id}</span>
                          </>
                        ) : null}
                      </p>
                    </div>
                    <ChevronDown
                      aria-hidden="true"
                      className={`mt-1 size-4 shrink-0 text-[#789087] transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                    />
                  </div>
                  {body && <p className="mt-2 text-[13px] leading-5 text-[#68736d]">{body}</p>}
                </button>

                {isOpen && (paso.tipo === 'motivo' || (showFile && paso.file_id)) && (
                  <div className="mx-4 mb-4 flex flex-col gap-2 border-t border-[#edf0ec] pt-3 text-[13px] leading-5 text-[#52605a] animate-in fade-in slide-in-from-top-1 duration-200">
                    {paso.tipo === 'motivo' && (
                      <>
                        {extra.length > 0 ? extra.map((linea) => <p key={linea}>{linea}</p>) : <p>No hay más detalle que el de la propia regla.</p>}
                        <p>La decisión vigente es {resultadoFrase(paso.resultado)}.</p>
                      </>
                    )}
                    {showFile && paso.file_id && (
                      <p>
                        Corresponde a{' '}
                        <Link href={ficheroHref(paso.file_id)} className="font-medium text-[#315d53] underline underline-offset-2">
                          {paso.file_id}
                        </Link>
                        .
                      </p>
                    )}
                  </div>
                )}
              </div>
            </li>
          )
        })}
      </ol>
      {pasos.length > visible && (
        <div className="mt-4 flex justify-center">
          <button
            onClick={() => setVisible((value) => value + PAGE_SIZE)}
            className="border border-[#d5e0d9] bg-white px-4 py-2 text-[14px] font-semibold text-[#315d53] transition hover:border-[#164f45]"
          >
            Ver {Math.min(PAGE_SIZE, pasos.length - visible)} más de {pasos.length - visible} restantes
          </button>
        </div>
      )}
    </>
  )
}
