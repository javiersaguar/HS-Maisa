import type { Aviso, EstadoEvento, EstadoFichero, Etapa, Fichero, MetodoExtraccion } from './types'

const currency = new Intl.NumberFormat('es-ES', {
  style: 'currency',
  currency: 'EUR',
  minimumFractionDigits: 2,
})

const number = new Intl.NumberFormat('es-ES')

export function formatAmount(amount: number | null): string {
  return amount === null ? '—' : currency.format(amount)
}

export function formatNumber(value: number): string {
  return number.format(value)
}

export function formatPercent(value: number | null, digits = 1): string {
  if (value === null || Number.isNaN(value)) return '—'
  return `${value.toFixed(digits).replace('.', ',')} %`
}

export function formatEur(value: number | null, digits = 4): string {
  if (value === null) return '—'
  return `${value.toFixed(digits).replace('.', ',')} €`
}

export function formatMs(ms: number | null): string {
  if (ms === null) return '—'
  if (ms < 1000) return `${Math.round(ms)} ms`
  return `${(ms / 1000).toFixed(1).replace('.', ',')} s`
}

/** 9.933 → "9,9 s"; 754 → "12 min 34 s". */
export function formatSeconds(seconds: number | null): string {
  if (seconds === null || Number.isNaN(seconds)) return '—'
  if (seconds < 60) return `${seconds.toFixed(1).replace('.', ',')} s`
  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60)
  return `${minutes} min ${rest} s`
}

export function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso).toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: iso.length === 10 ? 'UTC' : undefined,
  })
}

export function formatTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  return `${formatDate(iso)} · ${new Date(iso).toLocaleTimeString('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
  })}`
}

/** "hace 2 min": sólo se pinta en cliente, con datos ya cargados. */
export function formatRelative(iso: string | null): string {
  if (!iso) return '—'
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.round(diff / 60000)
  if (minutes < 1) return 'ahora'
  if (minutes < 60) return `hace ${minutes} min`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `hace ${hours} h`
  const days = Math.round(hours / 24)
  return `hace ${days} d`
}

/** "2026-03" → "mar 26" */
export function formatMonth(month: string): string {
  const [year, value] = month.split('-').map(Number)
  return new Date(Date.UTC(year, value - 1, 1))
    .toLocaleDateString('es-ES', { month: 'short', year: '2-digit', timeZone: 'UTC' })
    .replace('.', '')
}

export function initials(name: string): string {
  return name
    .split(' ')
    .filter((part) => /^[\p{L}]/u.test(part))
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

export function shortHash(hash: string | null, length = 8): string {
  return hash ? hash.slice(0, length) : '—'
}

export const ESTADOS_FICHERO: EstadoFichero[] = ['PAGAR', 'ESCALAR', 'NO_PAGAR', 'PENDIENTE']

export const ETAPAS: Etapa[] = ['ingest', 'extract', 'validate', 'enrich', 'decide', 'emit']

export const ETAPA_LABELS: Record<Etapa, string> = {
  ingest: 'Ingesta',
  extract: 'Extracción',
  validate: 'Validación',
  enrich: 'Maestro y ERP',
  decide: 'Norma',
  emit: 'Entrega',
}

export const ETAPA_DESCRIPCIONES: Record<Etapa, string> = {
  ingest: 'Registra el PDF: sha256, páginas y si tiene capa de texto.',
  extract: 'Lee el PDF y produce InvoiceFacts: plantilla, LLM sobre texto o visión.',
  validate: 'Comprueba la coherencia interna de los hechos: NIF, IBAN, IVA, total.',
  enrich: 'Cruza con el maestro Excel y con el snapshot del ERP 2009.',
  decide: 'Aplica la norma de pagos como código y deja un motivo por regla.',
  emit: 'Escribe la línea de outcomes.jsonl para la entrega.',
}

export const ESTADO_EVENTO_LABELS: Record<EstadoEvento, string> = {
  ok: 'OK',
  error: 'Error',
  pendiente: 'Pendiente',
  retry: 'Reintento',
  skip: 'Omitido',
}

export const METODO_LABELS: Record<MetodoExtraccion, string> = {
  plantilla: 'Plantilla',
  llm_texto: 'LLM sobre texto',
  llm_vision: 'LLM visión',
  cache: 'Caché LLM',
}

export const AVISO_LABELS: Record<Aviso, string> = {
  texto_instruccion: 'Texto que intenta instruir',
  sin_texto: 'Sin capa de texto',
  campo_ausente: 'Campo ausente',
  importe_ambiguo: 'Importe ambiguo',
  fecha_en_letra: 'Fecha en letra',
  iva_no_estandar: 'IVA no estándar',
  total_no_cuadra: 'Total no cuadra',
  iban_invalido: 'IBAN inválido',
  nif_invalido: 'NIF inválido',
  duplicado_sospechoso: 'Duplicado sospechoso',
  pedido_anulado_segun_pdf: 'Pedido anulado según el PDF',
  discrepancia_extractores: 'Discrepancia entre extractores',
  extraccion_parcial: 'Extracción parcial',
  documento_superpuesto: 'Documento superpuesto',
}

/** Primera regla incumplida, como `Decision.motivo_principal` en el backend. */
export function motivoPrincipal(fichero: Pick<Fichero, 'decision'>): string {
  const fallo = fichero.decision?.motivos.find((motivo) => !motivo.ok)
  if (fallo) return `${fallo.regla_id}: ${fallo.detalle}`
  return fichero.decision ? 'todas las reglas cumplidas' : 'sin decisión vigente'
}

/** "v3.R2" → "R2" */
export function reglaCorta(reglaId: string): string {
  return reglaId.split('.').pop() ?? reglaId
}
