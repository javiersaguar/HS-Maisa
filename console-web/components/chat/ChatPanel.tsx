'use client'

import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import Link from 'next/link'
import { MessageCircle, Send, X } from 'lucide-react'
import { chatDisponible, preguntar } from '@/lib/api/chat'
import { toApiError } from '@/lib/api/client'
import type { ChatRespuesta, ChatTurno } from '@/lib/types'
import { formatMs } from '@/lib/format'
import { ficheroHref } from '@/lib/routes'
import { useAsync } from '@/hooks/useAsync'
import { Spinner } from '@/components/ui/Spinner'

type Mensaje =
  | { role: 'user'; content: string }
  | { role: 'assistant'; content: string; respuesta: ChatRespuesta }
  | { role: 'error'; content: string }

const ESTADO_LABEL: Record<string, string> = {
  solo_lectura: 'Sólo lectura: no ejecuta nada',
  sin_datos: 'Sin datos para responder',
  sin_evidencia: 'Sin evidencia en la BD',
  limite: 'Límite de consultas alcanzado',
  degradado: 'Respuesta degradada',
}

/**
 * «Pregunta a Albertitos»: el chat de sólo lectura (K2, docs/api/chat.md), en su propio proceso. El botón
 * flotante sólo aparece si `GET /chat/salud` responde. La respuesta se pinta como texto (nunca HTML) y cada
 * cita enlaza al detalle del fichero: la decisión guardada y su traza siguen siendo la fuente de verdad.
 */
export function ChatPanel() {
  const { data: disponible } = useAsync(useCallback(() => chatDisponible(), []), [])
  const [abierto, setAbierto] = useState(false)
  const [mensajes, setMensajes] = useState<Mensaje[]>([])
  const [borrador, setBorrador] = useState('')
  const [enviando, setEnviando] = useState(false)
  const finRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    finRef.current?.scrollIntoView({ block: 'end' })
  }, [mensajes, enviando])

  if (!disponible) return null

  const enviar = async (event: FormEvent) => {
    event.preventDefault()
    const mensaje = borrador.trim().slice(0, 4000)
    if (!mensaje || enviando) return
    const historial: ChatTurno[] = mensajes
      .filter((m): m is Exclude<Mensaje, { role: 'error' }> => m.role !== 'error')
      .map((m) => ({ role: m.role, content: m.content.slice(0, 4000) }))
    setMensajes((actual) => [...actual, { role: 'user', content: mensaje }])
    setBorrador('')
    setEnviando(true)
    try {
      const respuesta = await preguntar(mensaje, historial)
      setMensajes((actual) => [...actual, { role: 'assistant', content: respuesta.respuesta, respuesta }])
    } catch (caught) {
      setMensajes((actual) => [...actual, { role: 'error', content: toApiError(caught).message }])
    } finally {
      setEnviando(false)
    }
  }

  if (!abierto) {
    return (
      <button
        onClick={() => setAbierto(true)}
        className="fixed right-6 bottom-6 z-40 inline-flex items-center gap-2 rounded-full bg-[#164f45] px-4 py-3 text-[14px] font-semibold text-white shadow-[0_10px_28px_rgba(20,75,60,0.28)] transition hover:bg-[#0d4037]"
      >
        <MessageCircle className="size-4" />
        Pregunta a Albertitos
      </button>
    )
  }

  return (
    <aside
      aria-label="Pregunta a Albertitos"
      className="fixed right-6 bottom-6 z-40 flex h-[min(640px,calc(100vh-48px))] w-[min(420px,calc(100vw-48px))] flex-col overflow-hidden rounded-2xl border border-[#d9e2dc] bg-white shadow-[0_16px_40px_rgba(20,55,45,0.18)] animate-in fade-in slide-in-from-bottom-2 duration-200"
    >
      <header className="flex items-start justify-between gap-3 border-b border-[#e3e9e4] px-4 py-3">
        <div>
          <p className="text-[15px] font-semibold">Pregunta a Albertitos</p>
          <p className="text-[12px] text-[#8a958e]">Consulta de sólo lectura · la norma decide</p>
        </div>
        <button onClick={() => setAbierto(false)} aria-label="Cerrar el chat" className="rounded-lg p-1 text-[#789087] hover:bg-[#f1f5f1]">
          <X className="size-4" />
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-3 text-[14px]">
        {mensajes.length === 0 && (
          <p className="text-[13px] leading-5 text-[#8a958e]">
            Pregunta por una factura, un proveedor o los pagos de una semana. Por ejemplo: «¿Por qué se escala
            F26-2201_transportes.pdf?». Puede equivocarse al explicar; la traza de cada factura es la fuente de verdad.
          </p>
        )}
        <div className="flex flex-col gap-3">
          {mensajes.map((m, index) =>
            m.role === 'user' ? (
              <p key={index} className="ml-8 self-end rounded-xl bg-[#eff8f3] px-3 py-2 whitespace-pre-wrap text-[#17211e]">
                {m.content}
              </p>
            ) : m.role === 'error' ? (
              <p key={index} role="alert" className="mr-8 rounded-xl border border-[#f1dada] bg-[#fff5f5] px-3 py-2 text-[13px] text-[#8f2a2a]">
                {m.content}
              </p>
            ) : (
              <div key={index} className="mr-8 rounded-xl border border-[#e4e5df] bg-[#fafbf9] px-3 py-2">
                {m.respuesta.estado !== 'ok' && (
                  <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-[#a08400]">
                    {ESTADO_LABEL[m.respuesta.estado] ?? m.respuesta.estado}
                  </p>
                )}
                <p className="whitespace-pre-wrap leading-5 text-[#17211e]">{m.content}</p>
                {m.respuesta.citas.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {m.respuesta.citas.map((cita) => (
                      <Link
                        key={cita}
                        href={ficheroHref(cita)}
                        className="rounded-md border border-[#dcefe6] bg-white px-1.5 py-0.5 font-mono text-[11px] font-semibold text-[#176d59] hover:underline"
                      >
                        {cita}
                      </Link>
                    ))}
                  </div>
                )}
                <p className="mt-1.5 text-[11px] text-[#9aa39e]">
                  {m.respuesta.modelo} · {formatMs(m.respuesta.latencia_ms)}
                  {m.respuesta.herramientas_usadas.length > 0 && ` · ${m.respuesta.herramientas_usadas.join(', ')}`}
                </p>
              </div>
            ),
          )}
          {enviando && (
            <p className="flex items-center gap-2 text-[13px] text-[#8a958e]">
              <Spinner className="size-3 text-[#315d53]" /> Consultando… (hasta 60 s)
            </p>
          )}
          <div ref={finRef} />
        </div>
      </div>

      <form onSubmit={enviar} className="flex items-end gap-2 border-t border-[#e3e9e4] p-3">
        <textarea
          value={borrador}
          onChange={(event) => setBorrador(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              event.currentTarget.form?.requestSubmit()
            }
          }}
          rows={2}
          maxLength={4000}
          disabled={enviando}
          placeholder="Escribe tu pregunta…"
          className="min-h-0 flex-1 resize-none rounded-lg border border-[#d5e0d9] px-3 py-2 text-[14px] outline-none focus:border-[#164f45] focus:ring-2 focus:ring-[#164f45]/15 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={enviando || !borrador.trim()}
          aria-label="Enviar"
          className="inline-flex size-10 items-center justify-center rounded-lg bg-[#164f45] text-white transition hover:bg-[#0d4037] disabled:opacity-50"
        >
          {enviando ? <Spinner className="size-3.5 text-white" /> : <Send className="size-4" />}
        </button>
      </form>
    </aside>
  )
}
