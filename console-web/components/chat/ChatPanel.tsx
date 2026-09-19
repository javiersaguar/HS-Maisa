'use client'

import { useCallback, useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { MessageCircle, SendHorizontal, X } from 'lucide-react'
import { Spinner } from '@/components/ui/Spinner'
import { toApiError } from '@/lib/api/client'
import {
  CHAT_GRABADAS,
  MAX_MENSAJE,
  chatSalud,
  preguntar,
  validarMensaje,
  type MensajeHistorial,
  type SaludChat,
} from '@/lib/api/chat'
import { USE_MOCK } from '@/lib/config'
import { GRABACION, RESPUESTAS_GRABADAS, SUGERENCIAS, respuestaGrabada } from '@/lib/mock/chat'
import { EstadoModelo } from './EstadoModelo'
import { MensajeChat, type Mensaje } from './MensajeChat'

const SONDEO_MS = 30_000
/** Un mensaje antes de darle id (Omit distributivo: cada variante conserva sus campos). */
type NuevoMensaje = Mensaje extends infer T ? (T extends unknown ? Omit<T, 'id'> : never) : never
const AYUDA =
  'Chat de sólo lectura sobre las decisiones. Arranque: make chat (o uv run python -m albertitos.chat --servidor), ' +
  'que lee dist/albertitos.db en sólo lectura. Repliegue en terminal: uv run python -m albertitos.chat "pregunta".'

/**
 * El chat en la consola: botón flotante + panel lateral contra el proceso del chat (:8001, `make chat`).
 * Sólo consulta: no hay ningún botón que ejecute nada. La línea de estado dice siempre si contesta el modelo en vivo;
 * el modo «respuestas grabadas» enseña la evaluación del 19/09 con su etiqueta, nunca como si fuera en vivo.
 */
export function ChatPanel() {
  const [salud, setSalud] = useState<SaludChat | null>(null)
  const [abierto, setAbierto] = useState(false)
  const [mensajes, setMensajes] = useState<Mensaje[]>([])
  const [entrada, setEntrada] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [grabado, setGrabado] = useState(false)
  const [huboDegradado, setHuboDegradado] = useState(false)
  const siguiente = useRef(0)
  const campo = useRef<HTMLTextAreaElement>(null)
  const lista = useRef<HTMLDivElement>(null)
  const peticion = useRef<AbortController | null>(null)
  const titulo = useId()
  const idPanel = useId()

  const refrescarSalud = useCallback(async (signal?: AbortSignal) => {
    const s = await chatSalud(signal)
    if (!signal?.aborted) setSalud(s)
  }, [])

  // Al montar y cada 30 s: GET /chat/salud (no gasta llamadas al modelo). Decide si el botón aparece.
  useEffect(() => {
    const control = new AbortController()
    void refrescarSalud(control.signal)
    const id = setInterval(() => void refrescarSalud(control.signal), SONDEO_MS)
    return () => {
      control.abort()
      clearInterval(id)
      peticion.current?.abort()
    }
  }, [refrescarSalud])

  // Al abrir: estado al día y el foco en el campo. Escape cierra.
  useEffect(() => {
    if (!abierto) return
    void refrescarSalud()
    campo.current?.focus()
    const alPulsar = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') setAbierto(false)
    }
    window.addEventListener('keydown', alPulsar)
    return () => window.removeEventListener('keydown', alPulsar)
  }, [abierto, refrescarSalud])

  // Cada mensaje nuevo, a la vista.
  useEffect(() => {
    lista.current?.scrollTo({ top: lista.current.scrollHeight, behavior: 'smooth' })
  }, [mensajes, enviando])

  const servidor = salud?.ok === true
  // Sin servidor sólo se puede enseñar lo grabado, y sólo si se pidió (USE_MOCK o NEXT_PUBLIC_CHAT_GRABADAS).
  const soloGrabado = !servidor && (USE_MOCK || CHAT_GRABADAS)
  const visible = servidor || USE_MOCK || CHAT_GRABADAS
  const grabadoActivo = grabado || soloGrabado
  const grabadoDisponible =
    !servidor || salud?.modelo_disponible === false || huboDegradado || USE_MOCK || CHAT_GRABADAS

  const anadir = (m: NuevoMensaje | NuevoMensaje[]) => {
    const nuevos = (Array.isArray(m) ? m : [m]).map((x) => ({ ...x, id: `m${siguiente.current++}` }) as Mensaje)
    setMensajes((prev) => [...prev, ...nuevos])
  }

  /** El historial para el modelo: sólo lo hablado EN VIVO (nunca lo grabado, ni notas ni errores). */
  const historial = (): MensajeHistorial[] => {
    const out: MensajeHistorial[] = []
    for (const m of mensajes) {
      if (m.tipo === 'usuario' && !m.grabado) out.push({ role: 'user', content: m.texto })
      else if (m.tipo === 'respuesta' && !m.grabada) out.push({ role: 'assistant', content: m.respuesta.respuesta })
    }
    return out.slice(-10)
  }

  const enviar = async (texto: string) => {
    if (enviando) return
    const invalido = validarMensaje(texto)
    if (invalido) {
      anadir({ tipo: 'nota', texto: invalido })
      return
    }
    const pregunta = texto.trim()
    setEntrada('')

    if (grabadoActivo) {
      const g = respuestaGrabada(pregunta)
      anadir(
        g
          ? [
              { tipo: 'usuario', texto: pregunta, grabado: true },
              { tipo: 'respuesta', respuesta: g.respuesta, grabada: { evaluacion: g.evaluacion, fuente: g.fuente } },
            ]
          : [
              { tipo: 'usuario', texto: pregunta, grabado: true },
              {
                tipo: 'nota',
                texto:
                  'No hay respuesta grabada para esa pregunta: en modo grabado sólo se enseñan las 15 preguntas de ' +
                  'la evaluación, tal cual. Para preguntar otra cosa hace falta el modelo en vivo.',
              },
            ],
      )
      return
    }

    const previo = historial()
    anadir({ tipo: 'usuario', texto: pregunta })
    setEnviando(true)
    const control = new AbortController()
    peticion.current = control
    try {
      const r = await preguntar(pregunta, previo, control.signal)
      if (control.signal.aborted) return
      anadir({ tipo: 'respuesta', respuesta: r })
      if (r.estado === 'degradado') setHuboDegradado(true)
    } catch (error) {
      if (control.signal.aborted) return
      anadir({ tipo: 'error', texto: toApiError(error).message })
    } finally {
      if (peticion.current === control) peticion.current = null
      setEnviando(false)
      void refrescarSalud() // las llamadas restantes han podido cambiar
    }
  }

  const alEnviar = (e: FormEvent) => {
    e.preventDefault()
    void enviar(entrada)
  }

  const alTeclear = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void enviar(entrada)
    }
  }

  const cambiarModo = (activar: boolean) => {
    setGrabado(activar)
    anadir({
      tipo: 'nota',
      texto: activar
        ? `Modo grabado: lo que sigue son respuestas reales de la ${GRABACION}, no consultas en vivo.`
        : 'Modo en vivo: lo que sigue lo contesta el chat ahora.',
    })
  }

  if (!visible) return null

  const sugerencias = grabadoActivo ? RESPUESTAS_GRABADAS.map((r) => r.pregunta) : SUGERENCIAS
  const largo = entrada.trim().length

  return (
    <>
      {!abierto ? (
        <button
          type="button"
          onClick={() => setAbierto(true)}
          title={AYUDA}
          aria-expanded={false}
          aria-controls={idPanel}
          className="fixed right-6 bottom-6 z-40 inline-flex items-center gap-2 rounded-full bg-[#164f45] px-4 py-3 text-[14px] font-semibold text-white shadow-lg hover:bg-[#0d4037] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#164f45]"
        >
          <MessageCircle className="size-4" aria-hidden="true" />
          Pregunta a Albertitos
        </button>
      ) : null}

      {abierto ? (
        <aside
          id={idPanel}
          role="dialog"
          aria-modal="false"
          aria-labelledby={titulo}
          className="fixed top-3 right-3 bottom-3 z-50 flex w-[420px] max-w-[calc(100vw-24px)] flex-col overflow-hidden rounded-2xl border border-[#e1e5df] bg-[#f7f8f5] shadow-2xl"
        >
          <header className="flex flex-col gap-2 border-b border-[#e1e5df] bg-white px-4 pt-3 pb-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h2 id={titulo} className="text-[15px] font-semibold text-[#17211e]">
                  Pregunta a Albertitos
                </h2>
                <p className="text-[12px] font-medium text-[#68736d]">Consulta de sólo lectura · la norma decide</p>
              </div>
              <button
                type="button"
                onClick={() => setAbierto(false)}
                aria-label="Cerrar el chat (Escape)"
                title="Cerrar (Escape)"
                className="rounded-lg p-1.5 text-[#68736d] hover:bg-[#f3f4f1] focus-visible:outline-2 focus-visible:outline-[#164f45]"
              >
                <X className="size-4" aria-hidden="true" />
              </button>
            </div>
            <EstadoModelo salud={salud} grabado={grabadoActivo} />
            {grabadoDisponible ? (
              <label className="flex items-center gap-2 text-[12px] text-[#17211e]">
                <input
                  type="checkbox"
                  checked={grabadoActivo}
                  disabled={soloGrabado}
                  onChange={(e) => cambiarModo(e.target.checked)}
                  className="size-3.5 accent-[#8a7400]"
                />
                Ver respuestas grabadas ({GRABACION})
                {soloGrabado ? <span className="text-[#68736d]">· sin servidor, sólo grabadas</span> : null}
              </label>
            ) : null}
          </header>

          <div ref={lista} aria-live="polite" className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-3">
            {mensajes.length === 0 ? (
              <p className="text-[13px] leading-relaxed text-[#68736d]">
                Pregunta por una factura, un pedido o los pagos. El chat consulta la Caja en sólo lectura y cita las
                facturas en que se apoya. No paga ni cambia decisiones: las toma la norma.
              </p>
            ) : null}
            {mensajes.map((m) => (
              <MensajeChat key={m.id} mensaje={m} />
            ))}
            {enviando ? (
              <p className="flex items-center gap-2 text-[12px] font-medium text-[#68736d]">
                <Spinner />
                consultando… (hasta 60 s)
              </p>
            ) : null}
          </div>

          <div className="border-t border-[#e1e5df] bg-white px-4 pt-2.5 pb-3">
            <div
              className={`mb-2 flex flex-wrap gap-1.5 ${grabadoActivo ? 'max-h-28 overflow-y-auto' : ''}`}
              aria-label={grabadoActivo ? 'Las 15 preguntas de la evaluación' : 'Sugerencias'}
            >
              {sugerencias.map((s) => (
                <button
                  key={s}
                  type="button"
                  disabled={enviando}
                  onClick={() => void enviar(s)}
                  className="rounded-full border border-[#e1e5df] bg-[#f7f8f5] px-2 py-0.5 text-left text-[12px] text-[#17211e] hover:border-[#164f45] disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-[#164f45]"
                >
                  {s}
                </button>
              ))}
            </div>
            <form onSubmit={alEnviar} className="flex items-end gap-2">
              <label className="sr-only" htmlFor={`${idPanel}-campo`}>
                Tu pregunta
              </label>
              <textarea
                id={`${idPanel}-campo`}
                ref={campo}
                value={entrada}
                onChange={(e) => setEntrada(e.target.value)}
                onKeyDown={alTeclear}
                rows={2}
                placeholder={grabadoActivo ? 'Una de las 15 preguntas de la evaluación…' : '¿Por qué se escala…?'}
                className="min-h-[44px] flex-1 resize-none rounded-xl border border-[#e1e5df] bg-white px-3 py-2 text-[13px] text-[#17211e] focus-visible:outline-2 focus-visible:outline-[#164f45]"
              />
              <button
                type="submit"
                disabled={enviando || largo === 0 || largo > MAX_MENSAJE}
                aria-label={enviando ? 'Consultando' : 'Enviar la pregunta'}
                className="inline-flex h-[44px] items-center gap-1.5 rounded-xl bg-[#164f45] px-3 text-[13px] font-semibold text-white disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#164f45]"
              >
                {enviando ? <Spinner /> : <SendHorizontal className="size-4" aria-hidden="true" />}
                {enviando ? 'consultando…' : 'Enviar'}
              </button>
            </form>
            {largo > MAX_MENSAJE - 500 ? (
              <p className={`mt-1 text-right text-[11px] ${largo > MAX_MENSAJE ? 'text-[#bd3434]' : 'text-[#68736d]'}`}>
                {largo}/{MAX_MENSAJE}
              </p>
            ) : null}
          </div>
        </aside>
      ) : null}
    </>
  )
}
