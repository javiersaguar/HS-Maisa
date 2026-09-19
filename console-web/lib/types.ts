/**
 * Modelo de dominio de Albertitos.
 *
 * Los tipos de la primera mitad copian `src/albertitos/core/contracts.py` de HS-Maisa campo a campo,
 * con sus nombres en snake_case: si el contrato cambia, se cambia aquí y en `lib/api/mappers.ts`.
 * Diferencias deliberadas: `Decimal` llega como número y las fechas como string ISO.
 *
 * La segunda mitad son vistas que arma la consola (panel, etapas, traza). Van en camelCase porque no
 * existen en el backend: se calculan a partir de las tablas `ficheros`, `hechos`, `decisiones` y `eventos`.
 */

/* ------------------------------------------------------------- contrato --- */

import type { ConfianzaFicha } from './types-confianza'

export type Resultado = 'PAGAR' | 'NO_PAGAR' | 'ESCALAR'

export type Etapa = 'ingest' | 'extract' | 'validate' | 'enrich' | 'decide' | 'emit'

export type EstadoEvento = 'ok' | 'error' | 'pendiente' | 'retry' | 'skip'

export type MetodoExtraccion = 'plantilla' | 'llm_texto' | 'llm_vision' | 'cache'

/** Señales de extract/validate que la norma puede consumir. Nunca decisiones. */
export type Aviso =
  | 'texto_instruccion'
  | 'sin_texto'
  | 'campo_ausente'
  | 'importe_ambiguo'
  | 'fecha_en_letra'
  | 'iva_no_estandar'
  | 'total_no_cuadra'
  | 'iban_invalido'
  | 'nif_invalido'
  | 'duplicado_sospechoso'
  | 'pedido_anulado_segun_pdf'
  | 'discrepancia_extractores'
  | 'extraccion_parcial'
  | 'documento_superpuesto'

export interface LineaFactura {
  concepto: string
  unidades: number | null
  importe: number | null
}

/** Lo que el extractor ve en el PDF. Sólo hechos: no tiene campo de decisión. */
export interface InvoiceFacts {
  file_id: string
  sha256: string
  num_factura: string | null
  fecha: string | null
  razon_social: string | null
  nif_emisor: string | null
  iban: string | null
  pedido: string | null
  base: number | null
  iva_pct: number | null
  iva: number | null
  total: number | null
  lineas: LineaFactura[]
  metodo: MetodoExtraccion
  extractor_version: string
  avisos: Aviso[]
  /** Fragmento literal del PDF que intenta instruir. Es evidencia, nunca una orden. */
  texto_sospechoso: string | null
  /** Dato de extracción. No decide nada. */
  confianza: number | null
}

export interface Proveedor {
  id: string
  razon_social: string
  nif: string
  iban: string
  ciudad: string | null
  condiciones_dias: number | null
}

export interface Pedido {
  pedido: string
  proveedor_id: string
  nif: string
  importe_total: number
  estado: string
  fecha_pedido: string | null
}

export interface ErpEntry {
  asiento_id: string
  fecha_registro: string
  proveedor_id: string
  nif: string
  pedido: string
  importe_esperado: number
  /** PENDIENTE | PAGADA */
  estado: string
}

/** Una regla de la norma aplicada a un fichero. */
export interface Motivo {
  /** "v3.R2" */
  regla_id: string
  ok: boolean
  detalle: string
  evidencia: Record<string, unknown>
}

export interface Decision {
  file_id: string
  sha256: string
  resultado: Resultado
  motivos: Motivo[]
  norma_version: string
  fecha_corte: string
  hechos_hash: string
  maestro_version: string
  erp_version: string
  decidido_en: string | null
}

/** Una fila de la tabla `eventos`. Cada etapa emite al menos uno por fichero. */
export interface Event {
  file_id: string | null
  sha256: string | null
  etapa: Etapa
  estado: EstadoEvento
  intento: number
  latencia_ms: number | null
  tokens_in: number | null
  tokens_out: number | null
  coste_eur: number | null
  /** ORA-00600, ERP-429, SES-401, LLM-TIMEOUT, LLM-INVALID… */
  error_codigo: string | null
  detalle: string | null
  version: string | null
  ts: string | null
}

/* ------------------------------------------------------------ ficheros --- */

/** Resultado vigente de un fichero, o PENDIENTE si no tiene decisión vigente (LLM caído, etc.). */
export type EstadoFichero = Resultado | 'PENDIENTE'

/** Lo que maestro y ERP dicen del fichero. Sólo viene en el detalle. */
export interface Fuentes {
  /** Null si aún no hay snapshot (BD recién ingerida): la UI enseña "sin snapshot", no un 500. */
  maestro_version: string | null
  erp_version: string | null
  proveedor: Proveedor | null
  pedido: Pedido | null
  asientos: ErpEntry[]
}

/** Fila de `ficheros` con sus hechos y su decisión vigente. */
export interface Fichero {
  file_id: string
  sha256: string
  /** 1 = Caja, 2 = lote sorpresa */
  lote: number
  paginas: number | null
  /** false → escaneada, hizo falta visión */
  tiene_texto: boolean | null
  ingerido_en: string | null
  estado: EstadoFichero
  hechos: InvoiceFacts | null
  decision: Decision | null
  /** null en listados; presente en `GET` de un fichero. */
  fuentes: Fuentes | null
}

export interface FicheroQuery {
  q?: string
  estado?: EstadoFichero | 'all'
  /** Regla incumplida, sin versión: "R2". */
  regla?: string | 'all'
  lote?: number | 'all'
  page?: number
  pageSize?: number
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

/* --------------------------------------------------------------- traza --- */

/** Un paso de la Chain of Work: un evento del pipeline o una regla de la norma. */
export type PasoTraza =
  | { id: string; tipo: 'evento'; file_id: string | null; ts: string | null; evento: Event }
  | {
      id: string
      tipo: 'motivo'
      file_id: string
      ts: string | null
      motivo: Motivo
      norma_version: string
      resultado: Resultado
    }

/** Agrupación del filtro de la traza. */
export type CategoriaTraza = 'norma' | 'incidencias' | Etapa

export interface TrazaQuery {
  file_id?: string
  etapa?: Etapa
  categoria?: CategoriaTraza | 'all'
}

/* -------------------------------------------------------------- etapas --- */

export interface EtapaResumen {
  etapa: Etapa
  eventos: number
  /** Ficheros con al menos un evento `ok` en la etapa. */
  ficherosOk: number
  porEstado: Record<EstadoEvento, number>
  latenciaMediaMs: number | null
  reintentos: number
  tokensIn: number
  tokensOut: number
  costeEur: number
  version: string | null
  ultimoEventoEn: string | null
}

export interface EtapasResumen {
  ficheros: number
  etapas: EtapaResumen[]
  recientes: Event[]
}

/* --------------------------------------------------------------- panel --- */

export interface ResultadoShare {
  resultado: Resultado
  count: number
  percent: number
}

export interface MesPunto {
  /** "2026-03" */
  mes: string
  ficheros: number
}

export interface Versiones {
  /** Norma de la decisión vigente más reciente. */
  norma: string | null
  /** Reparto de las decisiones vigentes por norma: el sábado conviven v3 y v4. */
  normas: Array<{ norma: string; ficheros: number }>
  maestro: string | null
  erp: string | null
  extractor: string | null
}

/** La última ráfaga de ingest/extract: de ahí sale el ritmo, no de todo el histórico. */
export interface VentanaPasada {
  ficheros: number
  segundos: number
  desde: string | null
  hasta: string | null
}

export interface Operacion {
  /** Ficheros de la última pasada / su duración. */
  ficherosPorSegundo: number | null
  ventana: VentanaPasada | null
  /** Coste de la extracción vigente (los hechos que deciden hoy). */
  costeEur: number
  /** Todo lo gastado en la BD, runs anteriores incluidos. Null si el backend no lo distingue. */
  costeEurHistorico: number | null
  /** Eventos con intento > 1 (ORA-00600, 429, SES-401 superados). */
  reintentos: number
  /** % de ficheros cuya extracción tocó el LLM (texto o visión). */
  pctLlm: number | null
}

export interface PanelResumen {
  ficheros: number
  porLote: Array<{ lote: number; ficheros: number }>
  porEstado: Record<EstadoFichero, number>
  distribucion: ResultadoShare[]
  versiones: Versiones
  operacion: Operacion
  etapas: EtapaResumen[]
  porMes: MesPunto[]
  recientes: Fichero[]
}

/* --------------------------------------------------------------- salud --- */

/** `GET /salud` del puente: si vive, si tiene BD y de qué tamaño. En mock, `modo: 'mock'`. */
export interface Salud {
  ok: boolean
  modo: 'mock' | 'http'
  /** Versión del contrato que declara el backend (`api`). */
  api: number | null
  bd: {
    ficheros: number
    decisionesVigentes: number
    pendientes: number
    ultimoEventoEn: string | null
    /** P0-1: tabla aditiva `identidades`. El puente la detecta; no la exige. */
    identidades: boolean
    versiones: Versiones
  } | null
}

/* ---------------------------------------------------------------- bonus --- */
/*
 * Calendario de pagos y tesorería (K1). Nombres de campo EXACTOS de docs/api/bonus.md: snake_case, sin
 * mapper que los renombre. Importes como string de 2 decimales ("8107.54"): no se suman en cliente.
 */

/** Una factura PAGAR en el calendario. */
export interface Pago {
  file_id: string
  lote: number
  decision_id: number
  proveedor_id: string
  beneficiario: string
  iban: string
  referencia: string
  importe_eur: string
  fecha_factura: string
  vencimiento: string
  fecha_ejecucion: string
  semana: string
  vencido: boolean
  maestro_version: string
  apto_remesa: boolean
  iban_control_ok: boolean
  /** Sólo con `con_confianza=true`: la ficha de K3 o null si K3 no está. */
  confianza?: ConfianzaFicha | null
}

export interface BonusResumen {
  tipo: string
  fecha_corte: string
  decisiones_pagar: number
  calendario_numero: number
  calendario_total_eur: string
  remesa_numero: number
  remesa_total_eur: string
  excluidos_remesa: number
  remesa_iban_sin_control: number
  sin_vencimiento_calculable: number
  vencidos: number
  vencen_semana_corte: number
  avisos_por_codigo: Record<string, number>
  semanas: Record<string, { numero: number; importe_eur: string }>
  vencido_importe_eur: string
  en_plazo_importe_eur: string
  semana_corte: string
  lotes: number[]
  proveedores: number
}

export interface CalendarioFiltros {
  semana: string | null
  proveedor: string | null
  lote: number | null
  vencido: boolean | null
}

export interface Calendario {
  filtros: CalendarioFiltros
  total: number
  mostrados: number
  pagos: Pago[]
  confianza_nota?: string
}

export interface ProveedorPago {
  proveedor_id: string
  beneficiario: string
  numero: number
  importe_eur: string
  vencidos_numero: number
  vencidos_importe_eur: string
  primera_ejecucion: string
  ultima_ejecucion: string
  lotes: number[]
  iban_control_ok: boolean
  en_remesa_numero: number
}

export interface Remesa {
  tipo: string
  iban_sin_control: number
  total: number
  mostrados: number
  pagos: Pago[]
}

export interface AvisoBonus {
  file_id: string
  codigo: string
  detalle: string
}

export interface SemanaTesoreria {
  semana: string
  desde: string
  numero: number
  importe_eur: string
  acumulado_eur: string
  vencidos_numero: number
  vencidos_importe_eur: string
  en_remesa_numero: number
}

export interface SemanaPrograma {
  semana: string
  desde: string
  numero: number
  importe_eur: string
  supera_tope: boolean
  arrastrado_numero: number
  arrastrado_importe_eur: string
}

export interface Programa {
  tope_semanal_eur: string
  numero: number
  importe_eur: string
  semanas_para_ponerse_al_dia: number | null
  semanas_para_pagarlo_todo: number | null
  sin_programar_numero: number
  semanas: SemanaPrograma[]
}

export interface Tesoreria {
  fecha_corte: string
  semana_corte: string
  numero: number
  importe_eur: string
  vencido_numero: number
  vencido_importe_eur: string
  en_plazo_numero: number
  en_plazo_importe_eur: string
  semanas: SemanaTesoreria[]
  programa?: Programa
}

/* ------------------------------------------------------------ confianza --- */
/* Confianza en la CLASIFICACIÓN por factura (K3): vive en `types-confianza.ts`. No es InvoiceFacts.confianza. */

export * from './types-confianza'

/* ----------------------------------------------------------------- chat --- */
/* Chat de sólo lectura (K2, docs/api/chat.md): proceso aparte en :8001. */

export interface ChatTurno {
  role: 'user' | 'assistant'
  content: string
}

export type ChatEstado = 'ok' | 'solo_lectura' | 'sin_datos' | 'sin_evidencia' | 'limite' | 'degradado'

export interface ChatRespuesta {
  respuesta: string
  citas: string[]
  herramientas_usadas: string[]
  modelo: string
  latencia_ms: number
  estado: ChatEstado
}
