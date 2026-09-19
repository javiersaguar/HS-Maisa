'use client'

import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import { FichaResolucion } from './FichaResolucion'
import { Archive, CircleAlert, Copy, Check, Info, Lock, TriangleAlert } from 'lucide-react'
import type { EstadoChat, RespuestaChat } from '@/lib/api/chat'
import { ETIQUETA_GRABADA, GRABACION, type RespuestaGrabada } from '@/lib/mock/chat'
import { ficheroHref } from '@/lib/routes'

export type Mensaje =
  | { id: string; tipo: 'usuario'; texto: string; /** preguntada en modo grabado: no entra en el historial */ grabado?: boolean }
  | {
      id: string
      tipo: 'respuesta'
      respuesta: RespuestaChat
      /** Si viene de la evaluación grabada: la etiqueta es obligatoria y va siempre. */
      grabada?: Pick<RespuestaGrabada, 'evaluacion' | 'fuente'>
    }
  | { id: string; tipo: 'error'; texto: string }
  | { id: string; tipo: 'nota'; texto: string }

const segundos = new Intl.NumberFormat('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

const ETIQUETA_ESTADO: Record<EstadoChat, string> = {
  ok: 'respondida',
  solo_lectura: 'sólo lectura',
  sin_datos: 'sin datos',
  sin_evidencia: 'sin evidencia',
  limite: 'límite de consultas',
  degradado: 'degradada',
}

export function MensajeChat({ mensaje }: { mensaje: Mensaje }) {
  if (mensaje.tipo === 'usuario') {
    return (
      <div className="ml-8 self-end rounded-2xl rounded-br-md bg-[#164f45] px-3 py-2 text-[13px] text-white">
        <span className="sr-only">Tu pregunta: </span>
        <p className="whitespace-pre-wrap break-words">{mensaje.texto}</p>
      </div>
    )
  }
  if (mensaje.tipo === 'error') {
    return (
      <div
        role="alert"
        className="mr-8 flex gap-2 rounded-xl border border-[#f1dada] bg-[#fff0f0] px-3 py-2 text-[13px] text-[#bd3434]"
      >
        <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
        <p className="whitespace-pre-wrap break-words">
          <span className="font-semibold">No se pudo consultar: </span>
          {mensaje.texto}
        </p>
      </div>
    )
  }
  if (mensaje.tipo === 'nota') {
    return (
      <p className="mx-2 flex gap-2 text-[12px] text-[#68736d]">
        <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
        <span>{mensaje.texto}</span>
      </p>
    )
  }

  const { respuesta, grabada } = mensaje
  const citas = respuesta.citas ?? []
  return (
    <article
      aria-label={grabada ? `Respuesta grabada (${ETIQUETA_ESTADO[respuesta.estado]})` : 'Respuesta del chat'}
      className="mr-8 flex flex-col gap-2 rounded-2xl rounded-bl-md border border-[#e1e5df] bg-white px-3 py-2.5 text-[13px] text-[#17211e]"
    >
      {grabada ? (
        <p className="inline-flex w-fit items-center gap-1.5 rounded-full border border-[#eee8bd] bg-[#fffbe8] px-2 py-0.5 text-[11px] font-semibold text-[#8a7400]">
          <Archive className="size-3 shrink-0" aria-hidden="true" />
          {ETIQUETA_GRABADA}
        </p>
      ) : null}

      {respuesta.estado === 'solo_lectura' ? (
        <Aviso icono={<Lock className="size-3.5 shrink-0" aria-hidden="true" />} tono="info">
          El chat sólo consulta. Las decisiones las toma la norma.
        </Aviso>
      ) : null}
      {respuesta.estado === 'degradado' ? (
        <Aviso icono={<TriangleAlert className="size-3.5 shrink-0" aria-hidden="true" />} tono="aviso">
          Respuesta degradada: no se ha podido contestar. La decisión y su traza siguen en la consola.
        </Aviso>
      ) : null}

      {/* Texto plano: nunca HTML del modelo. */}
      <TextoRespuesta texto={respuesta.respuesta} />
      {citas[0] ? <FichaResolucion fileId={citas[0]} /> : null}

      {citas.length > 1 ? (
        <div className="flex flex-wrap gap-1.5">
          <span className="sr-only">Facturas citadas:</span>
          {citas.slice(1).map((c, i) => (
            <Link
              key={c}
              style={{ animationDelay: Math.min(i, 4) * 40 + 'ms' }}
              href={ficheroHref(c)}
              title={`Abrir la traza de ${c}`}
              className="chat-cita rounded-full border border-[#dcefe6] bg-[#eff8f3] px-2 py-0.5 text-[12px] font-medium text-[#176d59] hover:bg-[#dcefe6] focus-visible:outline-2 focus-visible:outline-[#164f45]"
            >
              {respuesta.estado === 'degradado' ? `Ver la traza de ${c}` : c}
            </Link>
          ))}
        </div>
      ) : null}

      {citas.length >= 20 ? <p className="text-xs text-[#68736d]">Puede haber más facturas; la consulta está limitada.</p> : null}
      <p className="text-[11px] text-[#68736d]">
        {[
          ETIQUETA_ESTADO[respuesta.estado],
          `${segundos.format((respuesta.latencia_ms ?? 0) / 1000)} s`,
        ]
          .filter(Boolean)
          .join(' · ')}
      </p>

      {grabada ? (
        <p className="border-t border-[#eef0ec] pt-1.5 text-[11px] text-[#68736d]">
          {GRABACION}: {grabada.evaluacion.veredicto ?? 'sin evaluar'}
          {grabada.evaluacion.veredicto && grabada.evaluacion.veredicto !== 'correcta' && grabada.evaluacion.observacion
            ? ` — ${grabada.evaluacion.observacion}`
            : ''}
        </p>
      ) : null}
    </article>
  )
}

function Aviso({ icono, tono, children }: { icono: React.ReactNode; tono: 'info' | 'aviso'; children: React.ReactNode }) {
  const clases =
    tono === 'aviso'
      ? 'border-[#eee8bd] bg-[#fffbe8] text-[#8a7400]'
      : 'border-[#e1e7e2] bg-[#f7f8f5] text-[#164f45]'
  return (
    <p className={`flex items-start gap-2 rounded-lg border px-2.5 py-1.5 text-[12px] font-medium ${clases}`}>
      <span className="mt-0.5">{icono}</span>
      <span>{children}</span>
    </p>
  )
}


function TextoRespuesta({ texto }: { texto: string }) {
  const [expandido, setExpandido] = useState(false)
  const [largo, setLargo] = useState(false)
  const [copia, setCopia] = useState<'copiar' | 'copiado' | 'error'>('copiar')
  const parrafo = useRef<HTMLParagraphElement>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    const el = parrafo.current
    if (!el) return
    const medir = () => setLargo(el.scrollHeight > parseFloat(getComputedStyle(el).lineHeight) * 5 + 1)
    const observer = new ResizeObserver(medir)
    observer.observe(el)
    medir()
    return () => { observer.disconnect(); if (timer.current) clearTimeout(timer.current) }
  }, [texto])
  const copiar = async () => {
    try { await navigator.clipboard.writeText(texto); setCopia('copiado') }
    catch { setCopia('error') }
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setCopia('copiar'), 1800)
  }
  return <div>
    <p ref={parrafo} className={'whitespace-pre-wrap break-words leading-relaxed ' + (!expandido ? 'chat-texto-corto' : '')} data-fade={!expandido && largo}>{texto}</p>
    <div className="mt-1 flex items-center justify-between gap-2 text-[11px] text-[#176d59]">
      {largo ? <button type="button" aria-expanded={expandido} onClick={() => setExpandido(!expandido)}>{expandido ? 'Ver menos' : 'Ver más'}</button> : <span />}
      <button type="button" onClick={() => void copiar()} className="flex items-center gap-1">{copia === 'copiado' ? <Check className="size-3" /> : <Copy className="size-3" />}{copia === 'copiado' ? 'Copiado' : copia === 'error' ? 'No se pudo copiar' : 'Copiar respuesta'}</button>
    </div>
  </div>
}
