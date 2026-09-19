/**
 * Backend mock en memoria.
 *
 * Implementa las mismas lecturas que `lib/api/*` haría por HTTP. No hay escrituras: la consola es de
 * sólo lectura y la decisión la toma la norma en el backend (`albertitos run` / `reprocess --impacted`).
 * Nada de aquí se importa desde la UI.
 */

import type {
  EstadoEvento,
  EstadoFichero,
  Etapa,
  EtapaResumen,
  EtapasResumen,
  Event,
  Fichero,
  FicheroQuery,
  MesPunto,
  Paginated,
  PanelResumen,
  PasoTraza,
  Resultado,
  TrazaQuery,
} from '../types'
import { EVENTOS, FICHEROS, VERSIONES, fuentesDe } from './data'

const ETAPAS: Etapa[] = ['ingest', 'extract', 'validate', 'enrich', 'decide', 'emit']
const RESULTADOS: Resultado[] = ['PAGAR', 'ESCALAR', 'NO_PAGAR']

const delay = (ms = 160) => new Promise<void>((resolve) => setTimeout(resolve, ms))

const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T

function notFound(entity: string, id: string): never {
  const error = new Error(`${entity} ${id} no existe`) as Error & { status?: number }
  error.status = 404
  throw error
}

const byTsDesc = (a: { ts: string | null }, b: { ts: string | null }) => (b.ts ?? '').localeCompare(a.ts ?? '')

/** Listados: sin `fuentes`, como haría un endpoint de cola. */
const resumen = (fichero: Fichero): Fichero => ({ ...fichero, fuentes: null })

/** Más recientes primero: por decisión, y los PENDIENTE por ingesta. */
function recientes(): Fichero[] {
  return [...FICHEROS].sort((a, b) =>
    (b.decision?.decidido_en ?? b.ingerido_en ?? '').localeCompare(a.decision?.decidido_en ?? a.ingerido_en ?? ''),
  )
}

/* ---------------------------------------------------------------- etapas --- */

function resumenEtapa(etapa: Etapa): EtapaResumen {
  const events = EVENTOS.filter((event) => event.etapa === etapa)
  const porEstado: Record<EstadoEvento, number> = { ok: 0, error: 0, pendiente: 0, retry: 0, skip: 0 }
  events.forEach((event) => {
    porEstado[event.estado] += 1
  })
  const latencias = events.map((event) => event.latencia_ms).filter((value): value is number => value !== null)
  return {
    etapa,
    eventos: events.length,
    ficherosOk: new Set(events.filter((event) => event.estado === 'ok').map((event) => event.file_id)).size,
    porEstado,
    latenciaMediaMs: latencias.length ? Math.round(latencias.reduce((sum, value) => sum + value, 0) / latencias.length) : null,
    reintentos: events.filter((event) => event.intento > 1).length,
    tokensIn: events.reduce((sum, event) => sum + (event.tokens_in ?? 0), 0),
    tokensOut: events.reduce((sum, event) => sum + (event.tokens_out ?? 0), 0),
    costeEur: events.reduce((sum, event) => sum + (event.coste_eur ?? 0), 0),
    version: events.at(-1)?.version ?? null,
    ultimoEventoEn: events.reduce<string | null>((max, event) => (event.ts && (!max || event.ts > max) ? event.ts : max), null),
  }
}

export async function getEtapas(): Promise<EtapasResumen> {
  await delay()
  return clone({
    ficheros: FICHEROS.length,
    etapas: ETAPAS.map(resumenEtapa),
    recientes: [...EVENTOS].sort(byTsDesc).slice(0, 10),
  })
}

export async function listEventos(query: { etapa?: Etapa; limit?: number } = {}): Promise<Event[]> {
  await delay()
  return clone(
    EVENTOS.filter((event) => !query.etapa || event.etapa === query.etapa)
      .sort(byTsDesc)
      .slice(0, query.limit ?? 12),
  )
}

/* ----------------------------------------------------------------- panel --- */

function porMes(): MesPunto[] {
  const counts = new Map<string, number>()
  FICHEROS.forEach((fichero) => {
    const mes = fichero.hechos?.fecha?.slice(0, 7)
    if (mes) counts.set(mes, (counts.get(mes) ?? 0) + 1)
  })
  return Array.from(counts.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([mes, ficheros]) => ({ mes, ficheros }))
}

export async function getPanel(): Promise<PanelResumen> {
  await delay()
  const porEstado: Record<EstadoFichero, number> = { PAGAR: 0, ESCALAR: 0, NO_PAGAR: 0, PENDIENTE: 0 }
  FICHEROS.forEach((fichero) => {
    porEstado[fichero.estado] += 1
  })
  const decididos = FICHEROS.length - porEstado.PENDIENTE || 1

  const lotes = new Map<number, number>()
  FICHEROS.forEach((fichero) => lotes.set(fichero.lote, (lotes.get(fichero.lote) ?? 0) + 1))

  const entrada = EVENTOS.filter((event) => event.etapa === 'ingest' || event.etapa === 'extract')
    .map((event) => new Date(event.ts ?? 0).getTime())
    .sort((a, b) => a - b)
  const span = entrada.length > 1 ? (entrada[entrada.length - 1] - entrada[0]) / 1000 : 0
  const conHechos = FICHEROS.filter((fichero) => fichero.hechos)
  const conLlm = conHechos.filter((fichero) => fichero.hechos?.metodo === 'llm_texto' || fichero.hechos?.metodo === 'llm_vision')

  return clone({
    ficheros: FICHEROS.length,
    porLote: Array.from(lotes.entries()).map(([lote, ficheros]) => ({ lote, ficheros })),
    porEstado,
    distribucion: RESULTADOS.map((resultado) => ({
      resultado,
      count: porEstado[resultado],
      percent: Math.round((porEstado[resultado] / decididos) * 100),
    })),
    versiones: VERSIONES,
    operacion: {
      ficherosPorSegundo: span > 0 ? Math.round((FICHEROS.length / span) * 100) / 100 : null,
      costeEur: EVENTOS.reduce((sum, event) => sum + (event.coste_eur ?? 0), 0),
      reintentos: EVENTOS.filter((event) => event.intento > 1).length,
      pctLlm: conHechos.length ? Math.round((conLlm.length / conHechos.length) * 1000) / 10 : null,
    },
    etapas: ETAPAS.map(resumenEtapa),
    porMes: porMes(),
    recientes: recientes().slice(0, 6).map(resumen),
  })
}

/* -------------------------------------------------------------- ficheros --- */

export async function listFicheros(query: FicheroQuery = {}): Promise<Paginated<Fichero>> {
  await delay()
  const q = (query.q ?? '').trim().toLowerCase()
  const page = Math.max(1, query.page ?? 1)
  const pageSize = query.pageSize ?? 15

  const filtered = recientes().filter((fichero) => {
    if (q) {
      const h = fichero.hechos
      const haystack =
        `${fichero.file_id} ${h?.razon_social ?? ''} ${h?.num_factura ?? ''} ${h?.pedido ?? ''} ${h?.nif_emisor ?? ''} ${h?.total ?? ''}`.toLowerCase()
      if (!haystack.includes(q)) return false
    }
    if (query.estado && query.estado !== 'all' && fichero.estado !== query.estado) return false
    if (query.lote !== undefined && query.lote !== 'all' && fichero.lote !== query.lote) return false
    if (query.regla && query.regla !== 'all') {
      const regla = query.regla
      if (!fichero.decision?.motivos.some((motivo) => !motivo.ok && motivo.regla_id.endsWith(`.${regla}`))) return false
    }
    return true
  })

  const start = (page - 1) * pageSize
  return clone({
    items: filtered.slice(start, start + pageSize).map(resumen),
    total: filtered.length,
    page,
    pageSize,
  })
}

export async function getFichero(fileId: string): Promise<Fichero> {
  await delay()
  const id = fileId.normalize('NFC')
  const fichero = FICHEROS.find((item) => item.file_id === id)
  if (!fichero) notFound('El fichero', id)
  return clone({ ...fichero, fuentes: fuentesDe(fichero) })
}

/* ----------------------------------------------------------------- traza --- */

function eventoPaso(event: Event, index: number): PasoTraza {
  return { id: `ev-${event.file_id}-${event.etapa}-${event.intento}-${index}`, tipo: 'evento', file_id: event.file_id, ts: event.ts, evento: event }
}

function motivoPasos(fichero: Fichero): PasoTraza[] {
  const decision = fichero.decision
  if (!decision) return []
  return decision.motivos.map((motivo) => ({
    id: `mo-${fichero.file_id}-${motivo.regla_id}`,
    tipo: 'motivo' as const,
    file_id: fichero.file_id,
    ts: decision.decidido_en,
    motivo,
    norma_version: decision.norma_version,
    resultado: decision.resultado,
  }))
}

/**
 * Traza de un fichero en orden de lectura: hechos → maestro/ERP → reglas → resultado.
 * Las reglas van justo detrás del evento `decide` que las produjo.
 */
function trazaFichero(fichero: Fichero): PasoTraza[] {
  const events = EVENTOS.filter((event) => event.file_id === fichero.file_id).sort((a, b) =>
    (a.ts ?? '').localeCompare(b.ts ?? ''),
  )
  const pasos: PasoTraza[] = []
  events.forEach((event, index) => {
    pasos.push(eventoPaso(event, index))
    if (event.etapa === 'decide') pasos.push(...motivoPasos(fichero))
  })
  return pasos
}

function matches(paso: PasoTraza, query: TrazaQuery): boolean {
  const etapa = query.etapa
  if (etapa && (paso.tipo !== 'evento' || paso.evento.etapa !== etapa)) {
    // las reglas cuentan como etapa `decide`
    if (!(etapa === 'decide' && paso.tipo === 'motivo')) return false
  }
  const categoria = query.categoria
  if (!categoria || categoria === 'all') return true
  if (categoria === 'norma') return paso.tipo === 'motivo'
  if (categoria === 'incidencias') return paso.tipo === 'evento' ? paso.evento.estado !== 'ok' : !paso.motivo.ok
  return paso.tipo === 'evento' ? paso.evento.etapa === categoria : categoria === 'decide'
}

export async function listTraza(query: TrazaQuery = {}): Promise<PasoTraza[]> {
  await delay()

  if (query.file_id) {
    const id = query.file_id.normalize('NFC')
    const fichero = FICHEROS.find((item) => item.file_id === id)
    if (!fichero) notFound('El fichero', id)
    return clone(trazaFichero(fichero).filter((paso) => matches(paso, query)))
  }

  // global: lo más reciente primero, acotado para no pintar miles de pasos
  const pasos: PasoTraza[] = [
    ...EVENTOS.map(eventoPaso),
    ...FICHEROS.flatMap(motivoPasos),
  ].filter((paso) => matches(paso, query))
  pasos.sort(byTsDesc)
  return clone(pasos.slice(0, 200))
}
