'use client'

import { useCallback, useEffect, useRef, useState, type DragEvent } from 'react'
import Link from 'next/link'
import { Check, ChevronRight, FileUp } from 'lucide-react'
import { API_BASE_URL, USE_MOCK } from '@/lib/config'
import { toApiError } from '@/lib/api/client'
import {
  BANDEJA_EN_CURSO,
  LOTE_BANDEJA,
  fetchBandeja,
  subirFacturas,
  type Bandeja,
  type EstadoBandeja,
} from '@/lib/api/inbox'
import type { EstadoFichero } from '@/lib/types'
import { Card } from '@/components/ui/Card'
import { RecuentoResultados, ResultadoMarca } from '@/components/ui/Resultado'
import { Spinner } from '@/components/ui/Spinner'

const MAX_FICHEROS = 20
const POLL_MS = 1000
const REVISAR_MS = 5000
/** La lista acumulada de la portada sobrevive a cambiar de pantalla, no a cerrar la pestaña. */
const HISTORIAL_KEY = 'albertitos.bandeja.historial'

type Fila = Bandeja['ficheros'][number]

/** Los de `nuevas` arriba (sustituyen a su versión anterior), sin pasar de MAX_FICHEROS filas. */
function acumular(nuevas: Fila[], historial: Fila[]): Fila[] {
  const ids = new Set(nuevas.map((f) => f.fileId))
  return [...nuevas, ...historial.filter((f) => !ids.has(f.fileId))].slice(0, MAX_FICHEROS)
}

function leerHistorial(): Fila[] {
  try {
    const raw = sessionStorage.getItem(HISTORIAL_KEY)
    const lista: unknown = raw ? JSON.parse(raw) : []
    return Array.isArray(lista) ? (lista as Fila[]).filter((f) => f && typeof f.fileId === 'string') : []
  } catch {
    return []
  }
}

function guardarHistorial(filas: Fila[]) {
  try {
    sessionStorage.setItem(HISTORIAL_KEY, JSON.stringify(filas))
  } catch {
    /* sin sessionStorage: la lista vale mientras no cambies de pantalla */
  }
}

/**
 * El comando exacto, con el puerto del puente al que habla esta consola (sin --db: usa dist/bandeja.db). Si la consola
 * no corre en el 3000, el puente tiene que autorizar su origen o cada subida da 403.
 */
function comandoArranque(): string {
  let puerto = '8000'
  try {
    if (API_BASE_URL) puerto = new URL(API_BASE_URL).port || puerto
  } catch {
    /* URL rara: el puerto por defecto */
  }
  const origen = typeof window === 'undefined' ? null : window.location.origin
  const origenes = origen && !/^http:\/\/(localhost|127\.0\.0\.1):3000$/.test(origen) ? `ALBERTITOS_CONSOLA_ORIGENES=${origen} ` : ''
  return `${origenes}uv run python -m albertitos.console.api --bandeja${puerto === '8000' ? '' : ` --puerto ${puerto}`}`
}

const PASOS: Array<{ estado: EstadoBandeja; label: string; detalle: string }> = [
  { estado: 'ingiriendo', label: 'Registrar', detalle: 'Se guarda cada PDF con su huella' },
  { estado: 'extrayendo', label: 'Leer', detalle: 'Se sacan los datos de la factura' },
  { estado: 'decidiendo', label: 'Aplicar la norma', detalle: 'Se cruza con proveedores y ERP' },
]

type Fase = 'elegir' | 'subiendo' | 'procesando' | 'hecho'

function esPdf(file: File) {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
}

/**
 * Tarjeta izquierda de la portada: soltar o elegir PDF y verlos decididos. Los envíos se acumulan en
 * una lista (hasta MAX_FICHEROS); el puente acepta un envío a la vez, así que lo que se suelta mientras
 * trabaja se encola y sale en cuanto queda libre.
 *
 * La consola no decide: el puente guarda los PDF en la bandeja (lote 99, BD aparte de la entrega) y
 * lanza la CLI. Aquí sólo se enseña lo que la BD dice.
 *
 * Cada fila selecciona la factura que se argumenta en la tarjeta de la derecha, así que el trabajo
 * entero —soltar, leer, entender por qué— ocurre sin salir de la portada.
 */
export function InvoiceDropzone({
  onDone,
  onSelect,
  onLista,
  seleccionado = null,
}: {
  onDone: (message: string, tone: 'success' | 'error') => void
  onSelect?: (fileId: string) => void
  /** Los file_id decididos de la lista, en su orden: el carrusel de la derecha los recorre. */
  onLista?: (fileIds: string[]) => void
  seleccionado?: string | null
}) {
  const [fase, setFase] = useState<Fase>('elegir')
  const [bandeja, setBandeja] = useState<Bandeja | null>(null)
  const [historial, setHistorial] = useState<Fila[]>([])
  const [cola, setCola] = useState<File[]>([])
  const [error, setError] = useState<string | null>(null)
  const [noDisponible, setNoDisponible] = useState(USE_MOCK)
  const [arrastrando, setArrastrando] = useState(false)
  const [avisar, setAvisar] = useState(false)
  const [copiado, setCopiado] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const anadirAlHistorial = useCallback((nuevas: Fila[]) => {
    setHistorial((actual) => {
      const next = acumular(nuevas, actual)
      guardarHistorial(next)
      return next
    })
  }, [])

  // Al cargar: si el puente no tiene la bandeja activa se dice; si hay un trabajo en curso se retoma, y
  // si el último envío ya acabó se vuelve a enseñar, para no perderlo al volver de otra pantalla.
  useEffect(() => {
    if (USE_MOCK) return
    let vivo = true
    const guardado = leerHistorial()
    setHistorial(guardado)
    fetchBandeja()
      .then((b) => {
        if (!vivo) return
        setNoDisponible(!b.disponible)
        if (BANDEJA_EN_CURSO.includes(b.estado)) {
          setBandeja(b)
          setFase('procesando')
        } else if (b.ficheros.length) {
          setBandeja(b)
          setFase('hecho')
          anadirAlHistorial(b.ficheros)
          const primera = b.ficheros.find((f) => f.estado)
          if (primera) onSelect?.(primera.fileId)
        } else if (guardado.length) {
          setFase('hecho')
          const primera = guardado.find((f) => f.estado)
          if (primera) onSelect?.(primera.fileId)
        }
      })
      .catch((e) => vivo && setError(toApiError(e).message))
    return () => {
      vivo = false
    }
    // Sólo al montar: onSelect es estable y no debe reabrir la bandeja.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Sin bandeja, se vuelve a mirar cada 5 s: si el puente se reinicia con --bandeja, esto se activa solo.
  useEffect(() => {
    if (USE_MOCK || !noDisponible) return
    let vivo = true
    const timer = window.setInterval(async () => {
      try {
        const b = await fetchBandeja()
        if (vivo && b.disponible) {
          setNoDisponible(false)
          setError(null)
          onDone('Bandeja activa: ya puedes soltar facturas', 'success')
        }
      } catch {
        /* el puente se está reiniciando: se vuelve a mirar en 5 s */
      }
    }, REVISAR_MS)
    return () => {
      vivo = false
      window.clearInterval(timer)
    }
  }, [noDisponible, onDone])

  // Poll mientras la CLI trabaja.
  useEffect(() => {
    if (fase !== 'procesando') return
    let vivo = true
    const tick = async () => {
      try {
        const b = await fetchBandeja()
        if (!vivo) return
        setBandeja(b)
        if (BANDEJA_EN_CURSO.includes(b.estado)) return
        setFase('hecho')
        // Se añaden a la lista, no la sustituyen.
        anadirAlHistorial(b.ficheros)
        // La primera decidida se abre sola a la derecha: ver el porqué no debería costar otro clic.
        const primera = b.ficheros.find((f) => f.estado)
        if (primera) onSelect?.(primera.fileId)
        const pendientes = b.ficheros.filter((f) => f.estado === 'PENDIENTE' || f.estado === null).length
        if (b.estado === 'error') onDone(`La bandeja se paró: ${b.error ?? 'error sin mensaje'}`, 'error')
        else if (pendientes)
          onDone(`${b.ficheros.length - pendientes} decididas · ${pendientes} siguen PENDIENTE`, 'error')
        else onDone(`${b.ficheros.length} facturas decididas`, 'success')
      } catch (e) {
        if (vivo) setError(toApiError(e).message)
      }
    }
    const timer = window.setInterval(tick, POLL_MS)
    tick()
    return () => {
      vivo = false
      window.clearInterval(timer)
    }
  }, [fase, onDone, onSelect, anadirAlHistorial])

  const ocupado = fase === 'subiendo' || fase === 'procesando'
  const bloqueado = noDisponible

  const enviar = async (pdfs: File[]) => {
    setFase('subiendo')
    setBandeja(null)
    try {
      await subirFacturas(pdfs)
      setFase('procesando')
    } catch (e) {
      const apiError = toApiError(e)
      if (apiError.status === 409 && /entrega/.test(apiError.message)) setNoDisponible(true)
      setError(apiError.message)
      setFase(historial.length ? 'hecho' : 'elegir')
    }
  }

  /** Lo soltado mientras el puente trabaja espera aquí; en cuanto queda libre, sale como un envío. */
  useEffect(() => {
    if (ocupado || noDisponible || !cola.length) return
    const siguiente = cola
    setCola([])
    enviar(siguiente)
    // enviar cambia en cada render; sólo importa la cola y que el puente quede libre.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ocupado, noDisponible, cola])

  const subir = (lista: FileList | null) => {
    if (!lista || bloqueado) return
    const todos = Array.from(lista)
    const pdfs = todos.filter(esPdf)
    if (!pdfs.length) {
      setError('Ninguno de esos ficheros es un PDF')
      return
    }
    const hueco = MAX_FICHEROS - cola.length
    if (pdfs.length > hueco) {
      setError(
        cola.length
          ? `Ya hay ${cola.length} en espera: caben ${hueco} más en el siguiente envío (has soltado ${pdfs.length})`
          : `Como mucho ${MAX_FICHEROS} PDF por envío (has soltado ${pdfs.length})`,
      )
      return
    }
    const descartados = todos.length - pdfs.length
    setError(descartados ? `${descartados} fichero(s) no son PDF y se han descartado` : null)
    if (ocupado) setCola((actual) => [...actual, ...pdfs])
    else enviar(pdfs)
  }

  /** Pulsar o soltar sobre la zona desactivada: se señala el recuadro que explica cómo activarla. */
  const explicar = () => {
    setAvisar(true)
    window.setTimeout(() => setAvisar(false), 1600)
  }

  const onDrop = (event: DragEvent) => {
    event.preventDefault() // siempre: si no, el navegador abre el PDF y saca al usuario de la consola
    setArrastrando(false)
    if (bloqueado) {
      if (noDisponible) explicar()
      return
    }
    subir(event.dataTransfer.files)
  }

  const comando = comandoArranque()
  // En una URL pública (Vercel) el comando no le sirve a nadie: ahí el recuadro sólo explica qué pasa.
  const enLocal =
    typeof window === 'undefined' || /^(localhost|127\.0\.0\.1|\[::1\])$/.test(window.location.hostname)
  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(comando)
      setCopiado(true)
      window.setTimeout(() => setCopiado(false), 1500)
    } catch {
      /* sin portapapeles: el comando se puede seleccionar a mano */
    }
  }

  const pasoActual = PASOS.findIndex((p) => p.estado === bandeja?.estado)
  // Mientras corre un envío sus filas van arriba; al acabar ya están en el historial.
  const enCurso: Fila[] =
    bandeja && fase === 'procesando'
      ? bandeja.ficheros.length
        ? bandeja.ficheros
        : bandeja.fileIds.map((fileId) => ({ fileId, nombre: fileId, estado: null }))
      : []
  const filas = acumular(enCurso, historial)

  // Clave estable (string) para no avisar al padre en cada poll si la lista no cambia.
  const decididos = filas
    .filter((f) => f.estado)
    .map((f) => f.fileId)
    .join('\n')
  useEffect(() => {
    onLista?.(decididos ? decididos.split('\n') : [])
  }, [decididos, onLista])
  const hayPendientes = fase === 'hecho' && filas.some((f) => f.estado === 'PENDIENTE' || f.estado === null)
  // El recuento es el de ESTE envío, no el de la BD: si mañana llega otra Caja, la portada habla de ella.
  const porEstado = filas.reduce<Partial<Record<EstadoFichero, number>>>((acc, f) => {
    if (f.estado) acc[f.estado] = (acc[f.estado] ?? 0) + 1
    return acc
  }, {})
  const sinLeer = filas.filter((f) => !f.estado).length
  const conLista = filas.length > 0 && (fase === 'procesando' || fase === 'hecho')
  const conPasos = bandeja !== null && (fase === 'procesando' || fase === 'hecho')

  return (
    <Card className="flex min-h-0 flex-col overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-4">
        <div>
          <h2 className="text-[15px] font-semibold text-ink">Añadir facturas</h2>
          <p className="mt-0.5 text-[13px] text-muted">Se leen y se deciden con la misma norma, fuera de la entrega</p>
        </div>
        {fase === 'hecho' ? (
          <Link
            href={`/invoices?lote=${LOTE_BANDEJA}`}
            className="shrink-0 whitespace-nowrap text-[13px] font-medium text-accent-dark hover:underline"
          >
            Ver la bandeja
          </Link>
        ) : (
          <span className="shrink-0 whitespace-nowrap rounded-full bg-raised px-2 py-0.5 text-[12px] font-medium text-muted">
            Lote {LOTE_BANDEJA}
          </span>
        )}
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-4 p-5">
        <div
          className="shrink-0"
          onDragOver={(event) => {
            event.preventDefault()
            if (!bloqueado) setArrastrando(true)
          }}
          onDragLeave={() => setArrastrando(false)}
          onDrop={onDrop}
        >
        <button
          type="button"
          onClick={() => (noDisponible ? explicar() : inputRef.current?.click())}
          aria-disabled={bloqueado}
          aria-describedby={noDisponible ? 'bandeja-como-activar' : undefined}
          className={`flex w-full flex-col items-center gap-2 rounded-xl border-2 border-dashed px-4 text-center transition ${
            conLista ? 'py-5' : 'py-10'
          } ${
            arrastrando
              ? 'border-accent bg-accent-soft'
              : bloqueado
                ? 'cursor-not-allowed border-line bg-canvas opacity-70'
                : 'border-accent-line bg-canvas hover:border-accent hover:bg-accent-soft'
          }`}
        >
          {ocupado ? <Spinner className="size-6" /> : <FileUp className="size-7 text-accent" />}
          <span className="text-[15px] font-semibold text-ink">
            {noDisponible
              ? 'Subir facturas está desactivado en este puente'
              : fase === 'subiendo'
                ? 'Subiendo…'
                : fase === 'procesando'
                  ? 'Procesando… si sueltas más, esperan su turno'
                  : fase === 'hecho'
                    ? 'Suelta más PDF: se añaden a la lista'
                    : 'Suelta aquí los PDF o haz clic para elegirlos'}
          </span>
          <span className="text-[12px] text-muted">
            {noDisponible
              ? 'Abajo tienes cómo activarlo'
              : cola.length
                ? `${cola.length} en espera · salen al acabar este envío`
                : `Hasta ${MAX_FICHEROS} facturas por envío, 10 MB cada una`}
          </span>
        </button>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          hidden
          onChange={(event) => {
            subir(event.target.files)
            event.target.value = ''
          }}
        />

        {noDisponible && (
          <div
            id="bandeja-como-activar"
            className={`shrink-0 rounded-lg border border-warn-line bg-warn-soft px-3 py-2.5 text-[13px] text-ink-soft transition ${
              avisar ? 'ring-2 ring-warn' : ''
            }`}
          >
            {USE_MOCK ? (
              <p>
                Con datos de ejemplo no se suben facturas: hace falta el puente real y compilar la consola con
                NEXT_PUBLIC_USE_MOCK=false.
              </p>
            ) : enLocal ? (
              <p>
                Este puente sirve la BD de la entrega, que nunca se toca, así que no admite facturas nuevas. Para
                activarlo, para el puente (Ctrl+C en su terminal) y vuelve a arrancarlo, desde la carpeta del
                proyecto, con este comando:
              </p>
            ) : (
              <p>
                Esta demo pública es de sólo lectura: enseña las facturas ya decididas, pero no admite subir
                ninguna. Subir facturas funciona en la consola del equipo, con el puente en modo bandeja.
              </p>
            )}
            {(USE_MOCK || enLocal) && (
            <div className="mt-2 flex items-center gap-2">
              <code className="min-w-0 flex-1 select-all overflow-x-auto whitespace-nowrap rounded-md border border-warn-line bg-surface px-2 py-1 font-mono text-[12px] text-ink">
                {comando}
              </code>
              <button
                type="button"
                onClick={copiar}
                className="shrink-0 rounded-md border border-warn-line bg-surface px-2 py-1 text-[12px] font-semibold text-warn hover:bg-warn-soft"
              >
                {copiado ? 'Copiado' : 'Copiar'}
              </button>
            </div>
            )}
            {!USE_MOCK && enLocal && (
              <p className="mt-2 text-[12px] text-muted">
                Sin --db: trabaja sobre dist/bandeja.db, una copia de la entrega que se crea sola. En cuanto el puente
                vuelva con la bandeja, este recuadro desaparece sin recargar la página.
              </p>
            )}
          </div>
        )}

        {fase === 'elegir' && !bandeja && !historial.length && (
          <div className="shrink-0">
            <p className="text-[13px] font-semibold text-ink">Qué pasa al soltarlas</p>
            <ol className="mt-3 space-y-3">
              {PASOS.map((paso, i) => (
                <li key={paso.estado} className="flex gap-3">
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-raised text-[12px] font-semibold text-ink-soft">
                    {i + 1}
                  </span>
                  <div>
                    <p className="text-[13px] font-medium text-ink">{paso.label}</p>
                    <p className="text-[13px] text-muted">{paso.detalle}</p>
                  </div>
                </li>
              ))}
            </ol>
            <p className="mt-4 text-[13px] leading-relaxed text-muted">
              Cuando acaben, cada factura sale con su resultado. Elige una y a la derecha verás el porqué.
            </p>
          </div>
        )}

        {conLista && (
          <>
            {conPasos && (
              <ol className="grid shrink-0 grid-cols-3 gap-2" aria-label="Pasos del procesamiento">
                {PASOS.map((paso, i) => {
                  const hecho = fase === 'hecho' ? bandeja.estado === 'listo' || i < pasoActual : i < pasoActual
                  const activo = fase === 'procesando' && i === pasoActual
                  return (
                    <li
                      key={paso.estado}
                      aria-current={activo ? 'step' : undefined}
                      title={paso.detalle}
                      className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-[12px] font-semibold ${
                        activo
                          ? 'border-accent bg-accent-soft text-accent-dark'
                          : hecho
                            ? 'border-line-soft bg-canvas text-ink-soft'
                            : 'border-line-soft bg-surface text-muted'
                      }`}
                    >
                      {activo ? (
                        <Spinner className="size-3.5" />
                      ) : hecho ? (
                        <Check className="size-3.5 text-accent" />
                      ) : (
                        <span className="w-3.5 text-center">{i + 1}</span>
                      )}
                      <span className="truncate">{paso.label}</span>
                    </li>
                  )
                })}
              </ol>
            )}

            <div className="shrink-0">
              <p className="text-[13px] font-semibold text-ink">
                Subidas · {filas.length} {filas.length === 1 ? 'factura' : 'facturas'}
                {filas.length >= MAX_FICHEROS && (
                  <span className="ml-1 font-normal text-muted">(las {MAX_FICHEROS} últimas)</span>
                )}
              </p>
              <div className="mt-1">
                <RecuentoResultados porEstado={porEstado} sinLeer={sinLeer} />
              </div>
            </div>

            <ul className="min-h-[120px] flex-1 divide-y divide-line-soft overflow-y-auto rounded-xl border border-line">
              {filas.map((f) => {
                const activa = seleccionado === f.fileId
                return (
                  <li key={f.fileId}>
                    <button
                      type="button"
                      onClick={() => f.estado && onSelect?.(f.fileId)}
                      disabled={!f.estado}
                      aria-current={activa ? 'true' : undefined}
                      className={`group flex min-h-10 w-full items-center gap-3 border-l-2 px-3 py-2 text-left text-[13px] transition disabled:cursor-default ${
                        activa
                          ? 'border-l-accent bg-accent-soft'
                          : 'border-l-transparent hover:bg-canvas disabled:hover:bg-transparent'
                      }`}
                    >
                      <span
                        className={`min-w-0 flex-1 truncate font-mono text-[12px] ${activa ? 'font-medium text-ink' : 'text-ink-soft'}`}
                        title={f.nombre}
                      >
                        {f.nombre}
                      </span>
                      <ResultadoMarca estado={f.estado} />
                      <ChevronRight
                        aria-hidden
                        className={`size-3.5 shrink-0 transition ${
                          !f.estado ? 'invisible' : activa ? 'text-accent-dark' : 'text-line group-hover:text-muted'
                        }`}
                      />
                    </button>
                  </li>
                )
              })}
            </ul>
          </>
        )}

        {hayPendientes && (
          <p className="shrink-0 rounded-lg border border-warn-line bg-warn-soft px-3 py-2 text-[13px] text-ink-soft">
            Alguna factura no se ha podido leer (el LLM no respondió o el PDF es ilegible). Queda PENDIENTE y sin
            decisión: no se inventa ninguna.
          </p>
        )}
        {bandeja?.estado === 'error' && bandeja.error && (
          <p className="shrink-0 rounded-lg border border-bad-line bg-bad-soft px-3 py-2 text-[13px] text-bad">
            {bandeja.error}
          </p>
        )}
        {error && (
          <p role="alert" className="shrink-0 rounded-lg border border-bad-line bg-bad-soft px-3 py-2 text-[13px] text-bad">
            {error}
          </p>
        )}
      </div>
    </Card>
  )
}
