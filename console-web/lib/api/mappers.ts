/**
 * Payload del backend → modelo de `lib/types.ts`.
 *
 * Es el ÚNICO sitio que sabe cómo llegan los datos. Acepta:
 * - el contrato de HS-Maisa (`resultado`, `PAGAR`, `file_id`, `motivos`, `hechos`, `etapa`…);
 * - filas crudas de la SQLite (`motivos_json`, `hechos_json`, `tiene_texto` 0/1, `vigente`);
 * - los nombres del prototipo viejo (`decision`, `PAY`, `id`, `reasoningFindings`) mientras duren.
 * Si el puente de la fase 3 usa otros nombres, se añaden aquí y ninguna pantalla cambia.
 */

import { API_CONTRACT_VERSION } from '../config'
import type {
  Aviso,
  Decision,
  ErpEntry,
  EstadoEvento,
  EstadoFichero,
  Etapa,
  EtapaResumen,
  EtapasResumen,
  Event,
  Fichero,
  Fuentes,
  InvoiceFacts,
  LineaFactura,
  MesPunto,
  MetodoExtraccion,
  Motivo,
  Operacion,
  Paginated,
  PanelResumen,
  PasoTraza,
  Pedido,
  Proveedor,
  Resultado,
  ResultadoShare,
  Salud,
  VentanaPasada,
  Versiones,
} from '../types'

type Raw = Record<string, unknown>

const asRecord = (value: unknown): Raw => (value && typeof value === 'object' ? (value as Raw) : {})

/** Lee la primera clave presente, así snake_case y camelCase funcionan igual. */
function pick(raw: Raw, ...keys: string[]): unknown {
  for (const key of keys) {
    if (raw[key] !== undefined && raw[key] !== null) return raw[key]
  }
  return undefined
}

function str(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : value === undefined || value === null ? fallback : String(value)
}

function strOrNull(value: unknown): string | null {
  if (value === undefined || value === null || value === '') return null
  return String(value)
}

function num(value: unknown, fallback: number): number {
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

/** `Decimal` de pydantic llega como string ("2489.99"). */
function numOrNull(value: unknown): number | null {
  if (value === undefined || value === null || value === '') return null
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function boolOrNull(value: unknown): boolean | null {
  if (value === undefined || value === null) return null
  if (typeof value === 'boolean') return value
  if (value === 1 || value === '1' || value === 'true') return true
  if (value === 0 || value === '0' || value === 'false') return false
  return null
}

function oneOf<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  const normalised = String(value ?? '').toLowerCase()
  return (allowed.find((item) => item.toLowerCase() === normalised) ?? fallback) as T
}

const array = (value: unknown): unknown[] => (Array.isArray(value) ? value : [])

let apiJsonAvisada = false

/**
 * Las colecciones declaran `api` en el JSON (además de la cabecera). Si el backend sube de versión
 * y un proxy se come `X-Albertitos-Api`, esto sigue avisando. Campos de más no avisan.
 */
function noteApi(raw: Raw) {
  const declarada = numOrNull(pick(raw, 'api'))
  if (declarada === null || apiJsonAvisada) return
  if (declarada !== API_CONTRACT_VERSION) {
    apiJsonAvisada = true
    console.warn(
      `[albertitos] el JSON declara contrato v${declarada} y esta consola espera v${API_CONTRACT_VERSION}: revisa lib/api/mappers.ts`,
    )
  }
}

/** Columnas `*_json` de la SQLite: aceptan string JSON u objeto ya parseado. */
function json(value: unknown): unknown {
  if (typeof value !== 'string') return value
  try {
    return JSON.parse(value)
  } catch {
    return undefined
  }
}

/** El contrato valida `file_id` en NFC; una tilde descompuesta no encontraría el fichero. */
const nfc = (value: string) => value.normalize('NFC')

/* ----------------------------------------------------------------- enums --- */

const ETAPAS = ['ingest', 'extract', 'validate', 'enrich', 'decide', 'emit'] as const
const ESTADOS_EVENTO = ['ok', 'error', 'pendiente', 'retry', 'skip'] as const
const METODOS = ['plantilla', 'llm_texto', 'llm_vision', 'cache'] as const
const AVISOS: readonly Aviso[] = [
  'texto_instruccion',
  'sin_texto',
  'campo_ausente',
  'importe_ambiguo',
  'fecha_en_letra',
  'iva_no_estandar',
  'total_no_cuadra',
  'iban_invalido',
  'nif_invalido',
  'duplicado_sospechoso',
  'pedido_anulado_segun_pdf',
  'discrepancia_extractores',
  'extraccion_parcial',
  'documento_superpuesto',
]

/** Nombres viejos del prototipo → contrato. */
const RESULTADO_ALIAS: Record<string, Resultado> = {
  PAGAR: 'PAGAR',
  NO_PAGAR: 'NO_PAGAR',
  ESCALAR: 'ESCALAR',
  PAY: 'PAGAR',
  NO_PAY: 'NO_PAGAR',
  ESCALATE: 'ESCALAR',
}

export function toResultado(value: unknown): Resultado | null {
  const normalised = String(value ?? '').toUpperCase().replace(/[\s-]/g, '_')
  return RESULTADO_ALIAS[normalised] ?? null
}

function toEtapa(value: unknown): Etapa {
  return oneOf<Etapa>(value, ETAPAS, 'ingest')
}

function toAvisos(value: unknown): Aviso[] {
  return array(value)
    .map((item) => String(item).toLowerCase())
    .filter((item): item is Aviso => (AVISOS as readonly string[]).includes(item))
}

/* ---------------------------------------------------------------- hechos --- */

function toLinea(input: unknown): LineaFactura {
  const raw = asRecord(input)
  return {
    concepto: str(pick(raw, 'concepto', 'description')),
    unidades: numOrNull(pick(raw, 'unidades')),
    importe: numOrNull(pick(raw, 'importe', 'amount')),
  }
}

export function toHechos(input: unknown, fallbackFileId = ''): InvoiceFacts | null {
  const parsed = json(input)
  if (!parsed || typeof parsed !== 'object') return null
  const raw = asRecord(parsed)
  return {
    file_id: nfc(str(pick(raw, 'file_id', 'fileId'), fallbackFileId)),
    sha256: str(pick(raw, 'sha256')),
    num_factura: strOrNull(pick(raw, 'num_factura', 'invoiceNumber', 'invoice_number')),
    fecha: strOrNull(pick(raw, 'fecha', 'invoiceDate', 'invoice_date')),
    razon_social: strOrNull(pick(raw, 'razon_social', 'supplier', 'supplier_name')),
    nif_emisor: strOrNull(pick(raw, 'nif_emisor', 'taxId', 'tax_id')),
    iban: strOrNull(pick(raw, 'iban')),
    pedido: strOrNull(pick(raw, 'pedido', 'poNumber', 'po_number')),
    base: numOrNull(pick(raw, 'base')),
    iva_pct: numOrNull(pick(raw, 'iva_pct')),
    iva: numOrNull(pick(raw, 'iva')),
    total: numOrNull(pick(raw, 'total', 'amount')),
    lineas: array(pick(raw, 'lineas')).map(toLinea),
    metodo: oneOf<MetodoExtraccion>(pick(raw, 'metodo'), METODOS, 'plantilla'),
    extractor_version: str(pick(raw, 'extractor_version'), ''),
    avisos: toAvisos(pick(raw, 'avisos')),
    texto_sospechoso: strOrNull(pick(raw, 'texto_sospechoso')),
    confianza: numOrNull(pick(raw, 'confianza', 'confidence')),
  }
}

/* -------------------------------------------------------------- decisión --- */

export function toMotivo(input: unknown): Motivo {
  const raw = asRecord(input)
  // prototipo viejo: { result: 'pass' | 'fail' | 'warning', text }
  const legacyOk = pick(raw, 'result') !== undefined ? pick(raw, 'result') === 'pass' : undefined
  return {
    regla_id: str(pick(raw, 'regla_id', 'reglaId', 'regla', 'rule'), '—'),
    ok: boolOrNull(pick(raw, 'ok')) ?? legacyOk ?? false,
    detalle: str(pick(raw, 'detalle', 'text', 'message')),
    evidencia: asRecord(json(pick(raw, 'evidencia', 'evidence'))),
  }
}

export function toDecision(input: unknown, fallbackFileId = ''): Decision | null {
  if (!input) return null
  const raw = asRecord(input)
  const resultado = toResultado(pick(raw, 'resultado', 'result', 'decision'))
  if (!resultado) return null
  return {
    file_id: nfc(str(pick(raw, 'file_id', 'fileId', 'id'), fallbackFileId)),
    sha256: str(pick(raw, 'sha256')),
    resultado,
    motivos: array(json(pick(raw, 'motivos', 'motivos_json', 'reasoningFindings', 'findings'))).map(toMotivo),
    norma_version: str(pick(raw, 'norma_version'), '—'),
    fecha_corte: str(pick(raw, 'fecha_corte'), ''),
    hechos_hash: str(pick(raw, 'hechos_hash')),
    maestro_version: str(pick(raw, 'maestro_version'), '—'),
    erp_version: str(pick(raw, 'erp_version'), '—'),
    decidido_en: strOrNull(pick(raw, 'decidido_en', 'decidedAt')),
  }
}

/* ---------------------------------------------------------------- fuentes --- */

function toProveedor(input: unknown): Proveedor | null {
  if (!input) return null
  const raw = asRecord(input)
  return {
    id: str(pick(raw, 'id', 'proveedor_id')),
    razon_social: str(pick(raw, 'razon_social')),
    nif: str(pick(raw, 'nif')),
    iban: str(pick(raw, 'iban')),
    ciudad: strOrNull(pick(raw, 'ciudad')),
    condiciones_dias: numOrNull(pick(raw, 'condiciones_dias')),
  }
}

function toPedido(input: unknown): Pedido | null {
  if (!input) return null
  const raw = asRecord(input)
  return {
    pedido: str(pick(raw, 'pedido')),
    proveedor_id: str(pick(raw, 'proveedor_id')),
    nif: str(pick(raw, 'nif')),
    importe_total: num(pick(raw, 'importe_total'), 0),
    estado: str(pick(raw, 'estado')),
    fecha_pedido: strOrNull(pick(raw, 'fecha_pedido')),
  }
}

function toAsiento(input: unknown): ErpEntry {
  const raw = asRecord(input)
  return {
    asiento_id: str(pick(raw, 'asiento_id')),
    fecha_registro: str(pick(raw, 'fecha_registro')),
    proveedor_id: str(pick(raw, 'proveedor_id')),
    nif: str(pick(raw, 'nif')),
    pedido: str(pick(raw, 'pedido')),
    importe_esperado: num(pick(raw, 'importe_esperado'), 0),
    estado: str(pick(raw, 'estado')),
  }
}

function toFuentes(input: unknown): Fuentes | null {
  if (!input) return null
  const raw = asRecord(input)
  return {
    maestro_version: strOrNull(pick(raw, 'maestro_version')),
    erp_version: strOrNull(pick(raw, 'erp_version')),
    proveedor: toProveedor(pick(raw, 'proveedor')),
    pedido: toPedido(pick(raw, 'pedido')),
    asientos: array(pick(raw, 'asientos')).map(toAsiento),
  }
}

/* --------------------------------------------------------------- ficheros --- */

export function toFichero(input: unknown): Fichero {
  const raw = asRecord(input)
  const file_id = nfc(str(pick(raw, 'file_id', 'fileId', 'id'), 'desconocido.pdf'))
  const hechos = toHechos(pick(raw, 'hechos', 'hechos_json', 'facts'), file_id)
  // la decisión puede venir anidada, aplanada en la fila (JOIN ficheros × decisiones)
  // o, en el prototipo viejo, como string suelto (`decision: 'PAY'`)
  const nested = pick(raw, 'decision_vigente', 'decision')
  const decision =
    typeof nested === 'string'
      ? toDecision({ ...raw, resultado: nested }, file_id)
      : (toDecision(nested, file_id) ?? (pick(raw, 'resultado') ? toDecision(raw, file_id) : null))
  const estado: EstadoFichero = decision?.resultado ?? 'PENDIENTE'

  return {
    file_id,
    sha256: str(pick(raw, 'sha256'), hechos?.sha256 ?? ''),
    lote: num(pick(raw, 'lote'), 1),
    paginas: numOrNull(pick(raw, 'paginas')),
    tiene_texto: boolOrNull(pick(raw, 'tiene_texto')),
    ingerido_en: strOrNull(pick(raw, 'ingerido_en')),
    estado,
    hechos,
    decision,
    fuentes: toFuentes(pick(raw, 'fuentes')),
  }
}

export function toPaginatedFicheros(input: unknown, fallbackPageSize: number): Paginated<Fichero> {
  if (Array.isArray(input)) {
    const items = input.map(toFichero)
    return { items, total: items.length, page: 1, pageSize: fallbackPageSize }
  }
  const raw = asRecord(input)
  noteApi(raw)
  const items = array(pick(raw, 'items', 'results', 'data', 'ficheros')).map(toFichero)
  return {
    items,
    total: num(pick(raw, 'total', 'count'), items.length),
    page: num(pick(raw, 'page'), 1),
    pageSize: num(pick(raw, 'pageSize', 'page_size'), fallbackPageSize),
  }
}

/* ---------------------------------------------------------------- eventos --- */

export function toEvent(input: unknown): Event {
  const raw = asRecord(input)
  const fileId = strOrNull(pick(raw, 'file_id'))
  return {
    file_id: fileId ? nfc(fileId) : null,
    sha256: strOrNull(pick(raw, 'sha256')),
    etapa: toEtapa(pick(raw, 'etapa')),
    estado: oneOf<EstadoEvento>(pick(raw, 'estado'), ESTADOS_EVENTO, 'ok'),
    intento: num(pick(raw, 'intento'), 1),
    latencia_ms: numOrNull(pick(raw, 'latencia_ms')),
    tokens_in: numOrNull(pick(raw, 'tokens_in')),
    tokens_out: numOrNull(pick(raw, 'tokens_out')),
    coste_eur: numOrNull(pick(raw, 'coste_eur')),
    error_codigo: strOrNull(pick(raw, 'error_codigo')),
    detalle: strOrNull(pick(raw, 'detalle')),
    version: strOrNull(pick(raw, 'version')),
    ts: strOrNull(pick(raw, 'ts', 'timestamp')),
  }
}

/**
 * Un paso de traza: `{ tipo: 'motivo', motivo, ... }` o `{ tipo: 'evento', evento }`.
 * Una fila de `eventos` a pelo también vale.
 */
export function toPasoTraza(input: unknown, index = 0): PasoTraza {
  const raw = asRecord(input)
  const tipo = str(pick(raw, 'tipo'))
  if (tipo === 'motivo' || pick(raw, 'regla_id') !== undefined) {
    const motivo = toMotivo(pick(raw, 'motivo') ?? raw)
    return {
      id: str(pick(raw, 'id'), `paso-${index}`),
      tipo: 'motivo',
      file_id: nfc(str(pick(raw, 'file_id'))),
      ts: strOrNull(pick(raw, 'ts', 'decidido_en')),
      motivo,
      norma_version: str(pick(raw, 'norma_version'), motivo.regla_id.split('.')[0] ?? '—'),
      resultado: toResultado(pick(raw, 'resultado')) ?? 'ESCALAR',
    }
  }
  const evento = toEvent(pick(raw, 'evento') ?? raw)
  return {
    id: str(pick(raw, 'id'), `paso-${index}`),
    tipo: 'evento',
    file_id: evento.file_id,
    ts: evento.ts,
    evento,
  }
}

export function toTraza(input: unknown): PasoTraza[] {
  const source = Array.isArray(input)
    ? input
    : array(pick(asRecord(input), 'items', 'pasos', 'eventos', 'data'))
  return source.map((item, index) => toPasoTraza(item, index))
}

/* ----------------------------------------------------------------- etapas --- */

const EMPTY_ESTADOS: Record<EstadoEvento, number> = { ok: 0, error: 0, pendiente: 0, retry: 0, skip: 0 }

export function toEtapaResumen(input: unknown): EtapaResumen {
  const raw = asRecord(input)
  const porEstado = asRecord(pick(raw, 'porEstado', 'por_estado'))
  return {
    etapa: toEtapa(pick(raw, 'etapa')),
    eventos: num(pick(raw, 'eventos', 'n'), 0),
    ficherosOk: num(pick(raw, 'ficherosOk', 'ficheros_ok'), 0),
    porEstado: Object.fromEntries(
      ESTADOS_EVENTO.map((estado) => [estado, num(porEstado[estado], EMPTY_ESTADOS[estado])]),
    ) as Record<EstadoEvento, number>,
    latenciaMediaMs: numOrNull(pick(raw, 'latenciaMediaMs', 'latencia_media_ms', 'lat_media_ms')),
    reintentos: num(pick(raw, 'reintentos'), 0),
    tokensIn: num(pick(raw, 'tokensIn', 'tokens_in'), 0),
    tokensOut: num(pick(raw, 'tokensOut', 'tokens_out'), 0),
    costeEur: num(pick(raw, 'costeEur', 'coste_eur'), 0),
    version: strOrNull(pick(raw, 'version')),
    ultimoEventoEn: strOrNull(pick(raw, 'ultimoEventoEn', 'ultimo_evento_en', 'ultimo_ts')),
  }
}

export function toEtapasResumen(input: unknown): EtapasResumen {
  const raw = asRecord(input)
  noteApi(raw)
  return {
    ficheros: num(pick(raw, 'ficheros'), 0),
    etapas: array(pick(raw, 'etapas')).map(toEtapaResumen),
    recientes: array(pick(raw, 'recientes', 'eventos')).map(toEvent),
  }
}

/* ------------------------------------------------------------------ panel --- */

function toShare(input: unknown): ResultadoShare {
  const raw = asRecord(input)
  return {
    resultado: toResultado(pick(raw, 'resultado', 'decision')) ?? 'PAGAR',
    count: num(pick(raw, 'count', 'n'), 0),
    percent: num(pick(raw, 'percent'), 0),
  }
}

function toMes(input: unknown): MesPunto {
  const raw = asRecord(input)
  return { mes: str(pick(raw, 'mes')), ficheros: num(pick(raw, 'ficheros', 'n'), 0) }
}

export function toVersiones(input: unknown): Versiones {
  const raw = asRecord(input)
  const norma = strOrNull(pick(raw, 'norma'))
  const normas = array(pick(raw, 'normas'))
    .map((item) => {
      const entry = asRecord(item)
      return { norma: str(pick(entry, 'norma', 'norma_version')), ficheros: num(pick(entry, 'ficheros', 'n'), 0) }
    })
    .filter((item) => item.norma)
  return {
    norma,
    normas,
    maestro: strOrNull(pick(raw, 'maestro')),
    erp: strOrNull(pick(raw, 'erp')),
    extractor: strOrNull(pick(raw, 'extractor')),
  }
}

function toVentana(input: unknown): VentanaPasada | null {
  if (!input || typeof input !== 'object') return null
  const raw = asRecord(input)
  return {
    ficheros: num(pick(raw, 'ficheros'), 0),
    segundos: num(pick(raw, 'segundos'), 0),
    desde: strOrNull(pick(raw, 'desde')),
    hasta: strOrNull(pick(raw, 'hasta')),
  }
}

export function toOperacion(input: unknown): Operacion {
  const raw = asRecord(input)
  return {
    ficherosPorSegundo: numOrNull(pick(raw, 'ficherosPorSegundo', 'ficheros_s')),
    ventana: toVentana(pick(raw, 'ventana')),
    costeEur: num(pick(raw, 'costeEur', 'coste_eur'), 0),
    costeEurHistorico: numOrNull(pick(raw, 'costeEurHistorico', 'coste_eur_historico')),
    reintentos: num(pick(raw, 'reintentos'), 0),
    pctLlm: numOrNull(pick(raw, 'pctLlm', 'pct_llm')),
  }
}

export function toPanel(input: unknown): PanelResumen {
  const raw = asRecord(input)
  noteApi(raw)
  const porEstado = asRecord(pick(raw, 'porEstado', 'por_estado'))
  return {
    ficheros: num(pick(raw, 'ficheros'), 0),
    porLote: array(pick(raw, 'porLote', 'por_lote')).map((item) => {
      const lote = asRecord(item)
      return { lote: num(pick(lote, 'lote'), 1), ficheros: num(pick(lote, 'ficheros', 'n'), 0) }
    }),
    porEstado: {
      PAGAR: num(porEstado.PAGAR, 0),
      ESCALAR: num(porEstado.ESCALAR, 0),
      NO_PAGAR: num(porEstado.NO_PAGAR, 0),
      PENDIENTE: num(porEstado.PENDIENTE, 0),
    },
    distribucion: array(pick(raw, 'distribucion')).map(toShare),
    versiones: toVersiones(pick(raw, 'versiones')),
    operacion: toOperacion(pick(raw, 'operacion')),
    etapas: array(pick(raw, 'etapas')).map(toEtapaResumen),
    porMes: array(pick(raw, 'porMes', 'por_mes')).map(toMes),
    recientes: array(pick(raw, 'recientes')).map(toFichero),
  }
}

/* ------------------------------------------------------------------ salud --- */

/** `GET /salud`: `{ ok, api, bd: { ficheros, decisiones_vigentes, pendientes, versiones } | null }`. */
export function toSalud(input: unknown): Salud {
  const raw = asRecord(input)
  noteApi(raw)
  const bd = pick(raw, 'bd')
  const bdRaw = bd && typeof bd === 'object' ? asRecord(bd) : null
  return {
    ok: boolOrNull(pick(raw, 'ok')) ?? true,
    modo: 'http',
    api: numOrNull(pick(raw, 'api')),
    bd: bdRaw
      ? {
          ficheros: num(pick(bdRaw, 'ficheros'), 0),
          decisionesVigentes: num(pick(bdRaw, 'decisionesVigentes', 'decisiones_vigentes'), 0),
          pendientes: num(pick(bdRaw, 'pendientes'), 0),
          ultimoEventoEn: strOrNull(pick(bdRaw, 'ultimoEventoEn', 'ultimo_evento_en')),
          identidades: boolOrNull(pick(bdRaw, 'identidades')) ?? false,
          versiones: toVersiones(pick(bdRaw, 'versiones')),
        }
      : null,
  }
}
