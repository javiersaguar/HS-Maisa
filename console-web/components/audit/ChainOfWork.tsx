'use client'

import { useState, type ReactNode } from 'react'
import Link from 'next/link'
import { ChevronDown, Database, FileInput, Scale, ScanText, Send, ShieldCheck } from 'lucide-react'
import type { Etapa, PasoTraza } from '@/lib/types'
import { ETAPA_LABELS, formatDateTime, formatEur, formatMs, formatTime } from '@/lib/format'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { EmptyState } from '@/components/ui/states'
import { EventoBadge } from '@/components/invoices/badges'
import { ficheroHref } from '@/components/invoices/InvoiceTable'

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
  pass: 'border-[#b8dfcf] bg-[#eff8f3] text-[#176d59]',
  info: 'border-[#dfe4de] bg-[#f5f7f3] text-[#68736d]',
  warning: 'border-[#eee8bd] bg-[#fff9e6] text-[#a87000]',
  fail: 'border-[#f1dada] bg-[#fff0f0] text-[#bd3434]',
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

function DetailRow({ label, value }: { label: string; value: ReactNode }) {
  if (value === null || value === undefined || value === '') return null
  return (
    <div className="grid gap-1 sm:grid-cols-[120px_1fr] sm:gap-3">
      <dt className="text-[12px] font-bold uppercase tracking-[0.1em] text-[#7b8981]">{label}</dt>
      <dd className="text-[13px] leading-5 break-words text-[#52605a]">{value}</dd>
    </div>
  )
}

function evidenciaValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (Array.isArray(value)) return value.length ? value.join(', ') : '—'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

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
          className="shrink-0 rounded-lg px-2 py-1 text-[13px] font-semibold text-[#315d53] transition hover:bg-[#eff8f3]"
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

          if (paso.tipo === 'motivo') {
            const { motivo } = paso
            title = `${motivo.regla_id} · ${motivo.ok ? 'se cumple' : 'no se cumple'}`
            badge = (
              <StatusBadge tone={motivo.ok ? 'green' : motivo.evidencia.no_pagar ? 'red' : 'yellow'}>
                {motivo.ok ? 'Cumple' : 'Incumple'}
              </StatusBadge>
            )
            meta = [when(paso.ts), `Norma ${paso.norma_version}`]
            body = motivo.detalle
          } else {
            const { evento } = paso
            title = `${ETAPA_LABELS[evento.etapa]}${evento.intento > 1 ? ` · intento ${evento.intento}` : ''}`
            badge = <EventoBadge estado={evento.estado} />
            meta = [
              when(paso.ts),
              evento.latencia_ms !== null ? formatMs(evento.latencia_ms) : '',
              evento.error_codigo ?? '',
            ].filter(Boolean)
            body = evento.detalle
          }

          return (
            <li key={paso.id} className="relative pl-10 animate-in fade-in slide-in-from-bottom-1 duration-300">
              <span
                className={`absolute left-0 top-4 flex size-8 items-center justify-center rounded-full border ${NODE_CLASSES[nivel(paso)]}`}
              >
                <Icon className="size-3.5" />
              </span>
              <div className="rounded-xl border border-[#e1e8e2] bg-white shadow-[0_1px_2px_rgba(20,55,45,0.03)] transition hover:-translate-y-0.5 hover:border-[#b8dcca] hover:shadow-[0_7px_18px_rgba(20,75,60,0.08)]">
                <button onClick={() => toggle(paso.id)} aria-expanded={isOpen} className="w-full p-4 text-left">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-mono text-[14px] font-semibold">{title}</h3>
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

                {isOpen && (
                  <dl className="mx-4 mb-4 flex flex-col gap-2.5 border-t border-[#edf0ec] pt-3 animate-in fade-in slide-in-from-top-1 duration-200">
                    {paso.tipo === 'motivo' ? (
                      <>
                        {Object.entries(paso.motivo.evidencia).map(([key, value]) => (
                          <DetailRow key={key} label={key.replace(/_/g, ' ')} value={<span className="font-mono">{evidenciaValue(value)}</span>} />
                        ))}
                        {Object.keys(paso.motivo.evidencia).length === 0 && <DetailRow label="Evidencia" value="—" />}
                        <DetailRow label="Resultado" value={`${paso.resultado} (decisión vigente)`} />
                      </>
                    ) : (
                      <>
                        <DetailRow label="Etapa" value={<span className="font-mono">{paso.evento.etapa}</span>} />
                        <DetailRow label="Estado" value={<span className="font-mono">{paso.evento.estado}</span>} />
                        <DetailRow label="Intento" value={String(paso.evento.intento)} />
                        <DetailRow label="Latencia" value={formatMs(paso.evento.latencia_ms)} />
                        {(paso.evento.tokens_in !== null || paso.evento.tokens_out !== null) && (
                          <DetailRow label="Tokens" value={`${paso.evento.tokens_in ?? 0} entrada · ${paso.evento.tokens_out ?? 0} salida`} />
                        )}
                        {paso.evento.coste_eur !== null && <DetailRow label="Coste" value={formatEur(paso.evento.coste_eur, 5)} />}
                        <DetailRow label="Error" value={paso.evento.error_codigo} />
                        <DetailRow label="Versión" value={paso.evento.version} />
                      </>
                    )}
                    {showFile && paso.file_id && (
                      <DetailRow
                        label="Fichero"
                        value={
                          <Link href={ficheroHref(paso.file_id)} className="font-mono text-[#315d53] underline underline-offset-2">
                            {paso.file_id}
                          </Link>
                        }
                      />
                    )}
                  </dl>
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
            className="rounded-lg border border-[#d5e0d9] bg-white px-4 py-2 text-[14px] font-semibold text-[#315d53] transition hover:border-[#164f45] hover:bg-[#eff8f3]"
          >
            Ver {Math.min(PAGE_SIZE, pasos.length - visible)} más de {pasos.length - visible} restantes
          </button>
        </div>
      )}
    </>
  )
}
