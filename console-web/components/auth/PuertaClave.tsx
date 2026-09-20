'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { LoaderCircle, Lock, LogOut } from 'lucide-react'
import { API_BASE_URL, BRAND, USE_MOCK } from '@/lib/config'
import { CABECERA_CLAVE, alCambiarLaClave, borrarClave, claveActual, guardarClave } from './clave'

/**
 * La puerta de la demo pública (PLAN-15, A2). `GET /salud` no pide clave y dice `requiere_clave`:
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
  const campo = useRef<HTMLInputElement>(null)

  /** ¿La acepta el servidor? 200 sí, 401 no, cualquier otra cosa no es culpa de la clave. */
  const compruebaClave = useCallback(async (clave: string): Promise<'ok' | 'mala' | 'sin_respuesta'> => {
    try {
      const r = await fetch(`${API_BASE_URL}${RUTA_PROTEGIDA}`, {
        headers: { Accept: 'application/json', [CABECERA_CLAVE]: clave },
      })
      if (r.status === 401) return 'mala'
      return r.ok ? 'ok' : 'sin_respuesta'
    } catch {
      return 'sin_respuesta'
    }
  }, [])

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
        requiere = false // puente apagado o versión anterior al PLAN-15: se abre, como hasta hoy
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
        if (!claveActual()) setEstado((previo) => (previo === 'abierto' && conClave ? 'pide' : previo))
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
      <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
        <form
          onSubmit={entrar}
          className="w-full max-w-[380px] rounded-[28px] border border-line bg-surface p-7 shadow-[0_8px_24px_rgba(43,55,51,0.06)]"
        >
          <div className="flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="" width={32} height={32} className="size-8 shrink-0" />
            <div>
              <p className="text-[15px] font-semibold tracking-tight text-ink">{BRAND}</p>
              <p className="text-[13px] text-muted">Cuentas a pagar</p>
            </div>
          </div>

          <p className="mt-5 text-[14px] leading-relaxed text-ink-soft">
            Esta demo es privada: pide la clave al equipo. Con ella se ven las 540 facturas y se pueden subir
            las tuyas.
          </p>

          <label htmlFor="clave" className="mt-5 block text-[13px] font-medium text-ink">
            Clave
          </label>
          <input
            id="clave"
            ref={campo}
            type="password"
            autoComplete="current-password"
            spellCheck={false}
            aria-describedby={error ? 'clave-error' : undefined}
            aria-invalid={error ? true : undefined}
            className="mt-1.5 w-full rounded-lg border border-line bg-canvas px-3 py-2 text-[14px] text-ink outline-none focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent-dark/20"
          />

          {error && (
            <p id="clave-error" role="alert" className="mt-2 text-[13px] font-medium text-[#bd3434]">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={enviando}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-accent-dark px-4 py-2.5 text-[14px] font-semibold text-canvas transition hover:bg-ink disabled:opacity-60"
          >
            {enviando ? (
              <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
            ) : (
              <Lock className="size-4" aria-hidden="true" />
            )}
            {enviando ? 'Comprobando…' : 'Entrar'}
          </button>

          <p className="mt-4 text-[12px] leading-relaxed text-muted">
            La clave se guarda sólo en esta pestaña y se borra al cerrarla. Es una clave compartida para que
            nadie de fuera gaste el modelo, no un sistema de usuarios.
          </p>
        </form>
      </div>
    )
  }

  return (
    <>
      {children}
      {conClave && claveActual() && (
        <button
          type="button"
          onClick={() => {
            borrarClave()
            setEstado('pide')
          }}
          title="Olvidar la clave en esta pestaña"
          /* bottom-14 y no bottom-3: en `pnpm dev` el indicador de Next se pone en la esquina y se come el clic */
          className="fixed bottom-14 left-3 z-50 flex items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-[12px] font-semibold text-muted shadow-sm transition hover:text-accent-dark"
        >
          <LogOut className="size-3.5" aria-hidden="true" />
          Salir
        </button>
      )}
    </>
  )
}
