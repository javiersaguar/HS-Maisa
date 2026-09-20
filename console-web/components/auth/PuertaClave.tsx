'use client'

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { Eye, EyeOff, LoaderCircle, LogOut } from 'lucide-react'
import { API_BASE_URL, BRAND, USE_MOCK } from '@/lib/config'
import {
  CABECERA_CLAVE,
  alCambiarLaClave,
  alCambiarLasSalidas,
  borrarClave,
  claveActual,
  guardarClave,
  haySalida,
} from './clave'

/**
 * La puerta de la demo pública (PLAN-15). `GET /salud` no pide clave y dice `requiere_clave`:
 *
 * - `false` (o no hay backend, o es el mock): no se enseña nada y la consola es la de siempre;
 * - `true`: se pide la clave, se comprueba contra el servidor y se guarda en `sessionStorage`.
 *
 * Si el puente no contesta, **no se bloquea la consola**: se deja pasar y que la propia consola enseñe su
 * «sin conexión», que es más útil que una pantalla de clave delante de un backend caído.
 */
type Estado = 'comprobando' | 'abierto' | 'pide'

/** Una ruta que sí exige clave, para saber si la que tenemos guardada sigue valiendo. */
const RUTA_PROTEGIDA = '/panel'

export function PuertaClave({ children }: { children: React.ReactNode }) {
  const [estado, setEstado] = useState<Estado>(USE_MOCK || !API_BASE_URL ? 'abierto' : 'comprobando')
  const [conClave, setConClave] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)
  const [verClave, setVerClave] = useState(false)
  const campo = useRef<HTMLInputElement>(null)

  /** ¿La acepta el servidor? 200 sí, 401 no, cualquier otra cosa no es culpa de la clave. */
  const compruebaClave = useCallback(
    async (clave: string): Promise<'ok' | 'mala' | 'sin_respuesta'> => {
      try {
        const r = await fetch(`${API_BASE_URL}${RUTA_PROTEGIDA}`, {
          headers: { Accept: 'application/json', [CABECERA_CLAVE]: clave },
        })
        if (r.status === 401) return 'mala'
        return r.ok ? 'ok' : 'sin_respuesta'
      } catch {
        return 'sin_respuesta'
      }
    },
    [],
  )

  useEffect(() => {
    if (USE_MOCK || !API_BASE_URL) return
    let vivo = true
    ;(async () => {
      let requiere = false
      try {
        const r = await fetch(`${API_BASE_URL}/salud`, { headers: { Accept: 'application/json' } })
        const cuerpo = (await r.json()) as { requiere_clave?: boolean }
        requiere = cuerpo?.requiere_clave === true
      } catch {
        requiere = false // puente apagado o anterior al PLAN-15: se abre, como hasta hoy
      }
      if (!vivo) return
      setConClave(requiere)
      if (!requiere) {
        setEstado('abierto')
        return
      }
      const guardada = claveActual()
      if (!guardada) {
        setEstado('pide')
        return
      }
      const veredicto = await compruebaClave(guardada)
      if (!vivo) return
      if (veredicto === 'mala') {
        borrarClave()
        setEstado('pide')
      } else {
        setEstado('abierto') // 'sin_respuesta': no se echa a nadie por un backend que no contesta
      }
    })()
    return () => {
      vivo = false
    }
  }, [compruebaClave])

  // Un 401 en cualquier petición borra la clave: la pantalla vuelve sola, sin recargar.
  useEffect(
    () =>
      alCambiarLaClave(() => {
        if (!claveActual()) {
          setEstado((previo) => (previo === 'abierto' && conClave ? 'pide' : previo))
        }
      }),
    [conClave],
  )

  useEffect(() => {
    if (estado === 'pide') campo.current?.focus()
  }, [estado])

  async function entrar(event: React.FormEvent) {
    event.preventDefault()
    const clave = campo.current?.value.trim() ?? ''
    if (!clave) {
      setError('Escribe la clave.')
      campo.current?.focus()
      return
    }
    setEnviando(true)
    setError(null)
    const veredicto = await compruebaClave(clave)
    setEnviando(false)
    if (veredicto === 'ok') {
      guardarClave(clave)
      setEstado('abierto')
      return
    }
    setError(
      veredicto === 'mala'
        ? 'Esa clave no es. Pídesela al equipo.'
        : 'No se ha podido comprobar: el servidor no contesta. Espera unos segundos y reinténtalo.',
    )
    campo.current?.select()
  }

  if (estado === 'comprobando') {
    return (
      <div className="flex h-screen items-center justify-center bg-canvas text-muted">
        <p role="status" className="flex items-center gap-2 text-[14px]">
          <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
          Abriendo {BRAND}…
        </p>
      </div>
    )
  }

  if (estado === 'pide') {
    return (
      <main className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10 sm:px-6">
        <form
          onSubmit={entrar}
          className="w-full max-w-[400px] rounded-[28px] border border-line bg-surface p-6 shadow-[0_8px_24px_rgba(43,55,51,0.06)] sm:p-8"
        >
          <div className="flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="" width={40} height={40} className="size-10 shrink-0" />
            <div className="min-w-0">
              <p className="truncate text-[17px] font-semibold tracking-tight text-ink">{BRAND}</p>
              <p className="truncate text-[13px] text-muted">Cuentas a pagar de Alberto</p>
            </div>
          </div>

          <p className="mt-5 text-[14px] leading-relaxed text-ink-soft">
            540 facturas decididas <strong className="font-semibold text-ink">con la norma, no con el modelo</strong>:
            el LLM sólo lee el PDF y cada decisión deja su porqué. Esta demo es privada; pide la clave al equipo.
          </p>

          <label htmlFor="clave" className="mt-6 block text-[13px] font-medium text-ink">
            Clave
          </label>
          <div className="relative mt-1.5">
            <input
              id="clave"
              ref={campo}
              type={verClave ? 'text' : 'password'}
              autoComplete="current-password"
              autoCapitalize="off"
              autoCorrect="off"
              spellCheck={false}
              enterKeyHint="go"
              disabled={enviando}
              aria-describedby="clave-error clave-nota"
              aria-invalid={error ? true : undefined}
              className="w-full rounded-lg border border-line bg-canvas py-2.5 pl-3 pr-11 text-[15px] text-ink outline-none transition focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent-dark/20 disabled:opacity-60 sm:text-[14px]"
            />
            <button
              type="button"
              onClick={() => {
                setVerClave((v) => !v)
                campo.current?.focus()
              }}
              aria-label={verClave ? 'Ocultar la clave' : 'Ver la clave'}
              aria-pressed={verClave}
              title={verClave ? 'Ocultar la clave' : 'Ver la clave'}
              className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-lg text-muted transition hover:text-accent-dark focus-visible:ring-2 focus-visible:ring-accent-dark/30"
            >
              {verClave ? <EyeOff className="size-4" aria-hidden="true" /> : <Eye className="size-4" aria-hidden="true" />}
            </button>
          </div>

          {/* Hueco fijo: el error aparece sin mover el botón ni la caja. */}
          <p id="clave-error" role="alert" aria-live="polite" className="mt-1.5 min-h-[18px] text-[13px] font-medium leading-[18px] text-bad">
            {error}
          </p>

          <button
            type="submit"
            disabled={enviando}
            className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg bg-accent-dark px-4 py-2.5 text-[15px] font-semibold text-canvas transition hover:bg-ink focus-visible:ring-2 focus-visible:ring-accent-dark/30 disabled:cursor-not-allowed disabled:opacity-60 sm:text-[14px]"
          >
            {enviando && <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />}
            {enviando ? 'Comprobando…' : 'Entrar'}
          </button>

          <p id="clave-nota" className="mt-5 border-t border-line pt-4 text-[12px] leading-relaxed text-muted">
            Es una clave compartida para que nadie de fuera gaste el modelo, no un sistema de usuarios: no hay
            cuentas ni permisos. Se guarda sólo en esta pestaña y se borra al cerrarla.
          </p>
        </form>
      </main>
    )
  }

  return (
    <>
      {children}
      <SalidaDeRespaldo activa={conClave} alSalir={() => setEstado('pide')} />
    </>
  )
}

/**
 * El «Salir» vive en el pie de la barra lateral. Si esa barra no está montada (pantalla estrecha, una vista sin
 * `AppShell`), nadie podría soltar la clave: sólo entonces se enseña este botón, y lo menos posible.
 */
function SalidaDeRespaldo({ activa, alSalir }: { activa: boolean; alSalir: () => void }) {
  const hay = useSyncExternalStore(alCambiarLasSalidas, haySalida, () => true)
  if (!activa || hay || !claveActual()) return null
  return (
    <button
      type="button"
      onClick={() => {
        borrarClave()
        alSalir()
      }}
      title="Olvidar la clave en esta pestaña"
      className="fixed right-3 top-3 z-50 flex items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-[12px] font-semibold text-muted shadow-sm transition hover:text-accent-dark"
    >
      <LogOut className="size-3.5" aria-hidden="true" />
      Salir
    </button>
  )
}
