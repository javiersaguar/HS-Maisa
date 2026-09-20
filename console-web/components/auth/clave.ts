/**
 * La clave de la demo pública (PLAN-15, contrato A1↔A2), guardada **sólo en `sessionStorage`**: se borra al
 * cerrar la pestaña, nunca va a `localStorage` ni a una cookie ni al build (nada de `NEXT_PUBLIC_CLAVE`).
 *
 * Aquí no se valida nada: la clave la comprueba el servidor y devuelve 401. Este módulo sólo la guarda, la
 * reparte a quien hace las peticiones (`lib/api/client.ts` y `lib/api/chat.ts`) y avisa a la pantalla cuando
 * deja de valer, para volver a pedirla sin recargar la página.
 */

export const CABECERA_CLAVE = 'X-Albertitos-Clave'

const CLAVE_GUARDADA = 'albertitos.clave'

/** En navegación privada, o con el almacenamiento bloqueado, cualquier acceso puede lanzar. */
function almacen(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.sessionStorage
  } catch {
    return null
  }
}

export function leerClave(): string {
  try {
    return almacen()?.getItem(CLAVE_GUARDADA) ?? ''
  } catch {
    return ''
  }
}

export function guardarClave(clave: string): void {
  try {
    almacen()?.setItem(CLAVE_GUARDADA, clave)
  } catch {
    /* sin almacén, la clave vive en memoria hasta que se recargue: mejor eso que no dejar entrar */
  }
  claveEnMemoria = clave
  avisar()
}

export function borrarClave(): void {
  try {
    almacen()?.removeItem(CLAVE_GUARDADA)
  } catch {
    /* nada que borrar */
  }
  claveEnMemoria = ''
  avisar()
}

/** Respaldo para el navegador que no deja escribir en `sessionStorage`. */
let claveEnMemoria = ''

/** La que hay que mandar en la cabecera, o '' si no hay ninguna. */
export function claveActual(): string {
  return leerClave() || claveEnMemoria
}

/** La cabecera de la clave, o nada: sin clave no se manda cabecera y la petición es idéntica a la de hoy. */
export function cabeceraClave(): Record<string, string> {
  const clave = claveActual()
  return clave ? { [CABECERA_CLAVE]: clave } : {}
}

const oyentes = new Set<() => void>()

function avisar(): void {
  for (const oyente of oyentes) oyente()
}

/** La pantalla se suscribe para volver a aparecer en cuanto una petición diga 401. */
export function alCambiarLaClave(oyente: () => void): () => void {
  oyentes.add(oyente)
  return () => {
    oyentes.delete(oyente)
  }
}

/**
 * Un 401 de cualquier petición: la clave guardada ya no vale (o el equipo la ha rotado). Se borra y la
 * pantalla vuelve sola, sin recargar y sin perder la página en la que estaba.
 */
export function claveRechazada(): void {
  if (claveActual()) borrarClave()
}

/**
 * Quién enseña hoy un «Salir». Lo natural es el pie de la barra lateral, pero la barra puede no estar montada
 * (pantalla estrecha, una vista sin `AppShell`), y entonces nadie podría soltar la clave. Cada botón se registra
 * al montarse y `PuertaClave` pone el suyo de respaldo sólo si no hay ninguno.
 */
let salidasMontadas = 0
const oyentesSalida = new Set<() => void>()

export function registrarSalida(): () => void {
  salidasMontadas += 1
  for (const oyente of oyentesSalida) oyente()
  return () => {
    salidasMontadas -= 1
    for (const oyente of oyentesSalida) oyente()
  }
}

export function haySalida(): boolean {
  return salidasMontadas > 0
}

export function alCambiarLasSalidas(oyente: () => void): () => void {
  oyentesSalida.add(oyente)
  return () => {
    oyentesSalida.delete(oyente)
  }
}
