'use client'

import { useEffect, useRef, useState, type DragEvent } from 'react'
import Link from 'next/link'
import { FileUp } from 'lucide-react'
import { USE_MOCK } from '@/lib/config'
import { toApiError } from '@/lib/api/client'
import {
  BANDEJA_EN_CURSO,
  LOTE_BANDEJA,
  fetchBandeja,
  subirFacturas,
  type Bandeja,
  type EstadoBandeja,
} from '@/lib/api/inbox'
import { ficheroHref } from '@/lib/routes'
import { ResultadoBadge } from '@/components/invoices/badges'
import { Card } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'

const MAX_FICHEROS = 20
const POLL_MS = 1000
const ARRANQUE = 'uv run python -m albertitos.console.api --bandeja'

const PASOS: Array<{ estado: EstadoBandeja; label: string }> = [
  { estado: 'ingiriendo', label: 'Registrar' },
  { estado: 'extrayendo', label: 'Leer' },
  { estado: 'decidiendo', label: 'Aplicar la norma' },
]

type Fase = 'elegir' | 'subiendo' | 'procesando' | 'hecho'

function esPdf(file: File) {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
}

/**
 * Entrada principal del panel: soltar o elegir PDF y verlos decididos. La consola no decide: el
 * puente guarda los PDF en la bandeja (lote 99, BD aparte de la entrega) y lanza la CLI. Aquí sólo
 * se enseña lo que la BD dice.
 */
export function InvoiceDropzone({ onDone }: { onDone: (message: string, tone: 'success' | 'error') => void }) {
  const [fase, setFase] = useState<Fase>('elegir')
  const [bandeja, setBandeja] = useState<Bandeja | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [noDisponible, setNoDisponible] = useState(USE_MOCK)
  const [arrastrando, setArrastrando] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // Al cargar: si el puente no tiene la bandeja activa se dice; si hay un trabajo en curso, se retoma.
  useEffect(() => {
    if (USE_MOCK) return
    let vivo = true
    fetchBandeja()
      .then((b) => {
        if (!vivo) return
        setNoDisponible(!b.disponible)
        if (BANDEJA_EN_CURSO.includes(b.estado)) {
          setBandeja(b)
          setFase('procesando')
        }
      })
      .catch((e) => vivo && setError(toApiError(e).message))
    return () => {
      vivo = false
    }
  }, [])

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
  }, [fase, onDone])

  const ocupado = fase === 'subiendo' || fase === 'procesando'
  const bloqueado = ocupado || noDisponible

  const subir = async (lista: FileList | null) => {
    if (!lista || bloqueado) return
    const todos = Array.from(lista)
    const pdfs = todos.filter(esPdf)
    if (!pdfs.length) {
      setError('Ninguno de esos ficheros es un PDF')
      return
    }
    if (pdfs.length > MAX_FICHEROS) {
      setError(`Como mucho ${MAX_FICHEROS} PDF por envío (has soltado ${pdfs.length})`)
      return
    }
    const descartados = todos.length - pdfs.length
    setError(descartados ? `${descartados} fichero(s) no son PDF y se han descartado` : null)
    setFase('subiendo')
    setBandeja(null)
    try {
      await subirFacturas(pdfs)
      setFase('procesando')
    } catch (e) {
      const apiError = toApiError(e)
      if (apiError.status === 409 && /entrega/.test(apiError.message)) setNoDisponible(true)
      setError(apiError.message)
      setFase('elegir')
    }
  }

  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    setArrastrando(false)
    subir(event.dataTransfer.files)
  }

  const pasoActual = PASOS.findIndex((p) => p.estado === bandeja?.estado)
  const filas = bandeja
    ? bandeja.ficheros.length
      ? bandeja.ficheros
      : bandeja.fileIds.map((fileId) => ({ fileId, nombre: fileId, estado: null }))
    : []
  const hayPendientes = fase === 'hecho' && filas.some((f) => f.estado === 'PENDIENTE' || f.estado === null)

  return (
    <Card className="flex flex-col overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-[#e5e8e3] px-5 py-4">
        <div>
          <h2 className="text-[14px] font-semibold">Añadir facturas</h2>
          <p className="text-[14px] text-[#9aa39e]">Se leen y se deciden con la misma norma, fuera de la entrega</p>
        </div>
        {fase === 'hecho' ? (
          <Link
            href={`/invoices?lote=${LOTE_BANDEJA}`}
            className="shrink-0 whitespace-nowrap text-[13px] font-semibold text-[#315d53] hover:underline"
          >
            Ver la bandeja
          </Link>
        ) : (
          <span className="shrink-0 whitespace-nowrap rounded-full bg-[#f3f4f1] px-2 py-0.5 text-[12px] font-medium text-[#68736d]">
            Lote {LOTE_BANDEJA}
          </span>
        )}
      </div>

      <div className="flex flex-col gap-4 p-5">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(event) => {
            event.preventDefault()
            if (!bloqueado) setArrastrando(true)
          }}
          onDragLeave={() => setArrastrando(false)}
          onDrop={onDrop}
          disabled={bloqueado}
          className={`flex w-full flex-col items-center gap-2 rounded-xl border-2 border-dashed px-4 py-9 text-center transition disabled:cursor-not-allowed ${
            arrastrando
              ? 'border-[#35b889] bg-[#eff8f3]'
              : bloqueado
                ? 'border-[#e5e8e3] bg-[#fbfcfa] opacity-70'
                : 'border-[#cfe3d8] bg-[#fbfdfb] hover:border-[#70bda1] hover:bg-[#f5faf7]'
          }`}
        >
          {ocupado ? <Spinner className="size-6" /> : <FileUp className="size-7 text-[#35b889]" />}
          <span className="text-[15px] font-semibold text-[#233f35]">
            {fase === 'subiendo'
              ? 'Subiendo…'
              : fase === 'procesando'
                ? 'Procesando las facturas…'
                : 'Suelta aquí los PDF o haz clic para elegirlos'}
          </span>
          <span className="text-[12px] text-[#8a9890]">Hasta {MAX_FICHEROS} facturas, 10 MB cada una</span>
        </button>
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
          <p className="rounded-lg bg-[#fff9e6] px-3 py-2 text-[13px] text-[#a87000]">
            {USE_MOCK
              ? 'Con datos de ejemplo no se suben facturas: hace falta el puente real.'
              : 'El puente sirve la BD de la entrega y no escribe en ella.'}{' '}
            Arráncalo con <code className="font-mono text-[12px]">{ARRANQUE}</code>.
          </p>
        )}

        {bandeja && (fase === 'procesando' || fase === 'hecho') && (
          <>
            <ol className="flex gap-2">
              {PASOS.map((paso, i) => {
                const hecho = fase === 'hecho' ? bandeja.estado === 'listo' || i < pasoActual : i < pasoActual
                const activo = fase === 'procesando' && i === pasoActual
                return (
                  <li
                    key={paso.estado}
                    className={`flex flex-1 items-center gap-2 rounded-lg px-3 py-2 text-[12px] font-semibold ${
                      activo
                        ? 'bg-[#eff8f3] text-[#176d59]'
                        : hecho
                          ? 'bg-[#f5f7f3] text-[#59635e]'
                          : 'bg-[#fbfcfa] text-[#a1aaa5]'
                    }`}
                  >
                    {activo ? <Spinner className="size-3.5" /> : <span>{hecho ? '✓' : i + 1}</span>}
                    {paso.label}
                  </li>
                )
              })}
            </ol>
            <ul className="max-h-[220px] divide-y divide-[#edf0ec] overflow-y-auto rounded-xl border border-[#edf0ec]">
              {filas.map((f) => (
                <li key={f.fileId} className="flex items-center justify-between gap-3 px-3 py-2 text-[13px]">
                  {f.estado ? (
                    <Link href={ficheroHref(f.fileId)} className="truncate font-medium text-[#176d59] hover:underline">
                      {f.nombre}
                    </Link>
                  ) : (
                    <span className="truncate font-medium text-[#233f35]">{f.nombre}</span>
                  )}
                  <ResultadoBadge estado={f.estado} />
                </li>
              ))}
            </ul>
          </>
        )}

        {hayPendientes && (
          <p className="rounded-lg bg-[#fff9e6] px-3 py-2 text-[13px] text-[#a87000]">
            Alguna factura no se ha podido leer (el LLM no respondió o el PDF es ilegible). Queda PENDIENTE y sin
            decisión: no se inventa ninguna.
          </p>
        )}
        {bandeja?.estado === 'error' && bandeja.error && (
          <p className="rounded-lg bg-[#fff0f0] px-3 py-2 text-[13px] text-[#bd3434]">{bandeja.error}</p>
        )}
        {error && (
          <p role="alert" className="rounded-lg bg-[#fff0f0] px-3 py-2 text-[13px] text-[#bd3434]">
            {error}
          </p>
        )}
      </div>
    </Card>
  )
}
