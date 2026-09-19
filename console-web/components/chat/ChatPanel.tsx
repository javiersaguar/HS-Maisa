'use client'

import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { MessageCircle, RotateCcw, X } from 'lucide-react'
import { toApiError } from '@/lib/api/client'
import {
  CHAT_GRABADAS,
  chatSalud,
  preguntar,
  validarMensaje,
  type MensajeHistorial,
  type SaludChat,
} from '@/lib/api/chat'
import { USE_MOCK } from '@/lib/config'
import { GRABACION, RESPUESTAS_GRABADAS, SUGERENCIAS, respuestaGrabada } from '@/lib/mock/chat'
import { ChatComposer } from './ChatComposer'
import { ContadorLlamadas } from './ContadorLlamadas'
import { EstadoModelo } from './EstadoModelo'
import { MensajeChat, type Mensaje } from './MensajeChat'

const SONDEO_MS = 30_000
/** Un mensaje antes de darle id (Omit distributivo: cada variante conserva sus campos). */
type NuevoMensaje = Mensaje extends infer T ? (T extends unknown ? Omit<T, 'id'> : never) : never
const AYUDA = 'Pregunta a AlbertitosAI: consulta decisiones y facturas, sin modificar nada.'

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
  const boton = useRef<HTMLButtonElement>(null)
  const [pulso, setPulso] = useState(false)
  const pulsoHecho = useRef(false)
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

  useEffect(() => {
    if (!salud?.modelo_disponible || pulsoHecho.current) return
    pulsoHecho.current = true
    setPulso(true)
    const timer = setTimeout(() => setPulso(false), 250)
    return () => clearTimeout(timer)
  }, [salud?.modelo_disponible])

  const cerrar = () => {
    setAbierto(false)
    requestAnimationFrame(() => boton.current?.focus())
  }

  // Al abrir: estado al día y el foco en el campo. Escape cierra.
  useEffect(() => {
    if (!abierto) return
    void refrescarSalud()
    campo.current?.focus()
    const alPulsar = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') cerrar()
    }
    window.addEventListener('keydown', alPulsar)
    return () => window.removeEventListener('keydown', alPulsar)
  }, [abierto, refrescarSalud])

  // Cada mensaje nuevo, a la vista.
  useEffect(() => {
    lista.current?.scrollTo({ top: lista.current.scrollHeight, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
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
      if (r.llamadas_restantes !== undefined) {
        setSalud(prev => prev ? { ...prev, llamadas_restantes: r.llamadas_restantes } : prev)
      }
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

  return (
    <>
      {!abierto ? (
        <button
          type="button"
          onClick={() => setAbierto(true)}
          ref={boton}
          aria-label="Abrir AlbertitosAI"
          title={AYUDA}
          data-pulse={pulso}
          aria-expanded={false}
          aria-controls={idPanel}
          className="chat-trigger chat-press fixed right-6 bottom-6 z-40 inline-flex items-center gap-2 rounded-full bg-[#164f45] px-4 py-3 text-[14px] font-semibold text-white shadow-lg hover:bg-[#0d4037] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#164f45]"
        >
          <MessageCircle className="size-4" aria-hidden="true" />
          AlbertitosAI
        </button>
      ) : null}

      {abierto ? (
        <aside
          id={idPanel}
          role="dialog"
          aria-modal="false"
          aria-labelledby={titulo}
          className="chat-panel fixed inset-0 z-50 flex w-full flex-col overflow-hidden sm:inset-auto sm:top-3 sm:right-3 sm:bottom-3 sm:w-[440px] sm:max-w-[calc(100vw-24px)] sm:rounded-2xl border border-[#e1e5df] bg-[#f7f8f5] shadow-2xl"
        >
          <header className="flex flex-col gap-2 border-b border-[#e1e5df] bg-white px-4 pt-3 pb-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h2 id={titulo} className="text-[15px] font-semibold text-[#17211e]">
                  AlbertitosAI
                </h2>
                <p className="text-[12px] font-medium text-[#68736d]">Consulta de sólo lectura · la norma decide</p>
              </div>
              <button
                type="button"
                onClick={cerrar}
                aria-label="Cerrar el chat (Escape)"
                title="Cerrar (Escape)"
                className="rounded-lg p-1.5 text-[#68736d] hover:bg-[#f3f4f1] focus-visible:outline-2 focus-visible:outline-[#164f45]"
              >
                <X className="size-4" aria-hidden="true" />
              </button>
            </div>
            <div className="flex items-center justify-between gap-2">
              <EstadoModelo salud={salud} grabado={grabadoActivo} />
              <ContadorLlamadas salud={salud} />
            </div>
            <button type="button" disabled={enviando || mensajes.length === 0} onClick={() => { setMensajes([]); setEntrada(''); campo.current?.focus() }} className="flex w-fit items-center gap-1 text-[11px] text-[#68736d] disabled:opacity-40">
              <RotateCcw className="size-3" />Nueva conversación
            </button>
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
              <div className="space-y-3"><p className="text-[13px] leading-relaxed text-[#68736d]">
                Pregunta por una factura, un pedido o los pagos. El chat consulta la Caja en sólo lectura y cita las
                facturas en que se apoya. No paga ni cambia decisiones: las toma la norma.
              </p>
              <div className="flex flex-col gap-2" aria-label="Preguntas sugeridas">
                {SUGERENCIAS.map(s => <button type="button" key={s} onClick={() => void enviar(s)} className="chat-press rounded-xl border border-[#e1e5df] bg-white p-3 text-left text-xs text-[#164f45]">{s}</button>)}
              </div></div>
            ) : null}
            {mensajes.map((m) => (
              <div key={m.id} className="chat-message"><MensajeChat mensaje={m} /></div>
            ))}
            {enviando ? (
              <div role="status" className="chat-message flex w-fit items-center gap-3 rounded-2xl border border-[#e1e5df] bg-white px-4 py-3 text-xs text-[#68736d]">
                <span className="chat-thinking flex gap-1" aria-hidden="true"><i /><i /><i /></span>
                AlbertitosAI está consultando…
              </div>
            ) : null}
          </div>

          {grabadoActivo && mensajes.length > 0 ? <details className="border-t border-[#e1e5df] px-4 py-2 text-xs">
            <summary className="cursor-pointer text-[#68736d]">Más preguntas grabadas</summary>
            <div className="mt-2 flex max-h-28 flex-col gap-1 overflow-y-auto">{sugerencias.map(s => <button type="button" key={s} onClick={() => void enviar(s)} className="rounded border border-[#e1e5df] p-2 text-left">{s}</button>)}</div>
          </details> : null}
          <ChatComposer entrada={entrada} cambiar={setEntrada} enviar={s => void enviar(s)} enviando={enviando} campo={campo} />
        </aside>
      ) : null}
    </>
  )
}
