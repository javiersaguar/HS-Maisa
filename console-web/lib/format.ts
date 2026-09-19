import type {
  Aviso,
  Decision,
  EstadoEvento,
  EstadoFichero,
  Etapa,
  EtapaResumen,
  Event,
  Fichero,
  InvoiceFacts,
  MetodoExtraccion,
  Resultado,
} from './types'

const currency = new Intl.NumberFormat('es-ES', {
  style: 'currency',
  currency: 'EUR',
  minimumFractionDigits: 2,
})

const number = new Intl.NumberFormat('es-ES')

export function formatAmount(amount: number | null): string {
  return amount === null ? '—' : currency.format(amount)
}

/**
 * Importe del contrato del bonus (string con 2 decimales, "2428159.06") → "2.428.159,06 €".
 * Sólo para pintar: los totales vienen ya sumados de la API y aquí no se suma nada.
 */
export function formatImporte(value: string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  const amount = Number(value)
  return Number.isFinite(amount) ? currency.format(amount) : value
}

/** "2026-W38" → "sem. 38" */
export function formatSemana(semana: string): string {
  const match = semana.match(/W(\d+)$/)
  return match ? `sem. ${Number(match[1])}` : semana
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

/**
 * Cómo deja eventos cada etapa. ingest/extract/decide anotan un fichero;
 * validate sólo cuando cambia un grupo de duplicados; enrich son peticiones
 * HTTP al ERP (sin file_id); emit es el lote al empaquetar, más un fichero
 * si cambia lo entregado.
 */
export type GranoEtapa = 'fichero' | 'cambio' | 'lote'

export const ETAPA_GRANO: Record<Etapa, GranoEtapa> = {
  ingest: 'fichero',
  extract: 'fichero',
  validate: 'cambio',
  enrich: 'lote',
  decide: 'fichero',
  emit: 'fichero',
}

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
  validate: 'Marca duplicados: mismo pedido o mismo (NIF, nº de factura) en más de un PDF.',
  enrich: 'Descarga el ERP 2009 a un snapshot (una petición por página) y cruza el maestro.',
  decide: 'Aplica la norma de pagos como código y deja un motivo por regla.',
  emit: 'Escribe las decisiones vigentes en outcomes.jsonl para la entrega.',
}

/** Qué acaba de pasar, en una frase, para el detalle del fichero. */
export const ETAPA_ACCIONES: Record<Etapa, string> = {
  ingest: 'Se registró el PDF',
  extract: 'Se leyeron los datos',
  validate: 'Se marcó o se quitó un duplicado',
  enrich: 'Se pidió una página al ERP 2009',
  decide: 'La norma decidió',
  emit: 'Se preparó la entrega',
}

/** Línea bajo el nombre de la etapa: no todas cuentan ficheros. */
export function lineaResumenEtapa(etapa: EtapaResumen, ficheros = 0): string {
  const media = `media ${formatMs(etapa.latenciaMediaMs)}`
  const retries = etapa.reintentos > 0 ? ` · ${formatNumber(etapa.reintentos)} reintentos` : ''
  const grano = ETAPA_GRANO[etapa.etapa]
  if (etapa.eventos === 0) {
    if (etapa.etapa === 'emit') {
      return ficheros
        ? `${formatNumber(ficheros)} ficheros · listos para outcomes.jsonl`
        : 'Listo para outcomes.jsonl'
    }
    if (grano === 'cambio') return 'Ningún grupo de duplicados ha cambiado'
    return `0 ficheros · ${media}`
  }
  if (grano === 'lote') {
    return `${formatNumber(etapa.eventos)} peticiones · ${media}${retries}`
  }
  if (grano === 'cambio') {
    return `${formatNumber(etapa.ficherosOk)} ficheros marcados · ${media}${retries}`
  }
  return `${formatNumber(etapa.ficherosOk)} ficheros · ${media}${retries}`
}

/** Qué cuenta el anillo: cobertura de la etapa, no si PAGAR acierta. */
export function tooltipCoberturaEtapa(
  etapa: EtapaResumen,
  ficheros: number,
  cobertura: number | null,
): string {
  const grano = ETAPA_GRANO[etapa.etapa]
  const pct = cobertura === null ? '—' : `${Math.round(cobertura)}%`
  if (cobertura === null) {
    return 'Aún no hay cobertura: esta etapa no ha dejado eventos.'
  }
  if (grano === 'cambio') {
    if (etapa.eventos === 0) {
      return `${pct}: la validación solo anota cuando cambia un grupo de duplicados. Sin cambios se muestra como 100%.`
    }
    const relevantes = etapa.porEstado.ok + etapa.porEstado.error + etapa.porEstado.pendiente
    return `${pct}: grupos de duplicados resueltos en ok (${formatNumber(etapa.porEstado.ok)} de ${formatNumber(relevantes)}).`
  }
  if (grano === 'lote') {
    const relevantes = etapa.porEstado.ok + etapa.porEstado.error + etapa.porEstado.pendiente
    const total = relevantes || etapa.eventos
    return `${pct}: peticiones al ERP 2009 que salieron ok (${formatNumber(etapa.porEstado.ok)} de ${formatNumber(total)}). No cuenta ficheros.`
  }
  if (etapa.etapa === 'emit' && etapa.eventos === 0) {
    return `${pct}: ficheros con decisión vigente, listos para outcomes.jsonl. Todavía no se ha empaquetado.`
  }
  return `${pct}: ficheros que terminaron esta etapa en ok (${formatNumber(etapa.ficherosOk)} de ${formatNumber(ficheros)}). Es cobertura, no acierto de PAGAR/NO_PAGAR.`
}

/** Pie del KPI de cobertura en el detalle de una etapa. */
export function pieCoberturaEtapa(etapa: EtapaResumen, ficheros: number): string {
  const grano = ETAPA_GRANO[etapa.etapa]
  const cuando = formatRelative(etapa.ultimoEventoEn)
  if (grano === 'lote') {
    return `${formatNumber(etapa.eventos)} peticiones al ERP · ${cuando}`
  }
  if (grano === 'cambio') {
    if (etapa.eventos === 0) return 'Sólo deja evento cuando un duplicado cambia'
    return `${formatNumber(etapa.ficherosOk)} ficheros con marca de duplicado · ${cuando}`
  }
  if (etapa.etapa === 'emit' && etapa.eventos === 0) {
    return `${formatNumber(ficheros)} de ${formatNumber(ficheros)} ficheros con decisión vigente`
  }
  return `${formatNumber(etapa.ficherosOk)} de ${formatNumber(ficheros)} ficheros · ${cuando}`
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
  if (fallo) return frase(fallo.detalle)
  return fichero.decision ? 'Todas las reglas se cumplen.' : 'Todavía no hay decisión.'
}

/** "v3.R2" → "R2" */
export function reglaCorta(reglaId: string): string {
  return reglaId.split('.').pop() ?? reglaId
}

/** Primera letra mayúscula, para pintar un detalle de regla como frase. */
export function frase(texto: string): string {
  const trimmed = texto.trim()
  if (!trimmed) return trimmed
  return trimmed.charAt(0).toLocaleUpperCase('es-ES') + trimmed.slice(1)
}

export function loteNombre(lote: number): string {
  if (lote === 1) return 'la Caja'
  if (lote === 2) return 'el lote sorpresa'
  if (lote === 99) return 'la bandeja (fuera de la entrega)'
  return `el lote ${lote}`
}

export function resultadoFrase(resultado: Resultado): string {
  if (resultado === 'PAGAR') return 'pagar'
  if (resultado === 'NO_PAGAR') return 'no pagar'
  return 'escalar a una persona'
}

function numeroRegla(reglaId: string): string {
  return reglaCorta(reglaId).replace(/^R/i, '')
}

function listarReglas(ids: string[]): string {
  const nums = ids.map(numeroRegla)
  if (nums.length === 0) return ''
  if (nums.length === 1) return `la regla ${nums[0]}`
  if (nums.length === 2) return `las reglas ${nums[0]} y ${nums[1]}`
  return `las reglas ${nums.slice(0, -1).join(', ')} y ${nums[nums.length - 1]}`
}

export function tituloRegla(reglaId: string): string {
  return `Regla ${numeroRegla(reglaId)}`
}

export function resumenReglas(decision: Decision): string {
  const fallos = decision.motivos.filter((motivo) => !motivo.ok)
  if (decision.motivos.length === 0) return 'La norma aún no ha dejado reglas para este fichero.'
  if (fallos.length === 0) return 'Ninguna regla impide el pago.'
  return `Hay que revisar ${listarReglas(fallos.map((motivo) => motivo.regla_id))}.`
}

/** Cómo se leyó el PDF: método, versión y confianza en una frase. */
export function describirExtraccion(hechos: InvoiceFacts): string {
  const version = hechos.extractor_version ? ` (extractor ${hechos.extractor_version})` : ''
  const confianza =
    hechos.confianza === null || Number.isNaN(hechos.confianza)
      ? ''
      : ` La lectura tiene una confianza del ${Math.round(hechos.confianza * 100)} %.`
  const escaneada = hechos.avisos.includes('sin_texto')

  switch (hechos.metodo) {
    case 'plantilla':
      return `Se reconoció la plantilla del proveedor y se leyeron los campos sin pasar por el modelo de lenguaje${version}.${confianza}`
    case 'llm_texto':
      return `El modelo de lenguaje leyó el texto del PDF${version}.${confianza}`
    case 'llm_vision':
      return `El PDF iba escaneado, sin texto que se pudiera copiar. El modelo de lenguaje lo leyó como imagen${version}.${confianza}`
    case 'cache':
      return escaneada
        ? `El PDF iba escaneado, sin texto que se pudiera copiar. Los datos salieron de una lectura anterior del modelo de lenguaje${version}, sin volver a llamarlo.${confianza}`
        : `Los datos salieron de una lectura anterior del modelo de lenguaje${version}, sin volver a llamarlo.${confianza}`
  }
}

/** De qué versiones sale la decisión, sin hashes ni comandos. */
export function describirLinaje(decision: Decision): string {
  const dia = formatDate(decision.decidido_en)
  const hora = decision.decidido_en
    ? new Date(decision.decidido_en).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
    : null
  const cuando = hora ? `${dia} a las ${hora}` : dia
  const corte = formatDate(decision.fecha_corte)
  const erp =
    decision.erp_version && decision.erp_version !== '—'
      ? `el ERP 2009 (${decision.erp_version})`
      : 'el ERP 2009'
  return `La norma ${decision.norma_version} tomó esta decisión el ${cuando}. Usó como fecha de corte el ${corte} y cruzó el maestro de proveedores con ${erp}.`
}

export function tituloEvento(evento: Event): string {
  if (evento.estado === 'error') {
    const fallos: Record<Etapa, string> = {
      ingest: 'No se pudo registrar el PDF',
      extract: 'No se pudieron leer los datos',
      validate: 'Falló la comprobación',
      enrich: 'No se pudo cruzar con maestro o ERP',
      decide: 'La norma no pudo decidir',
      emit: 'No se pudo preparar la entrega',
    }
    return fallos[evento.etapa]
  }
  if (evento.estado === 'retry') return `Se reintentó: ${ETAPA_LABELS[evento.etapa].toLowerCase()}`
  if (evento.estado === 'pendiente') return `${ETAPA_LABELS[evento.etapa]} a medias`
  if (evento.estado === 'skip') return `Se saltó: ${ETAPA_LABELS[evento.etapa].toLowerCase()}`
  return ETAPA_ACCIONES[evento.etapa]
}

function avisoHumano(aviso: string): string {
  return AVISO_LABELS[aviso as Aviso] ?? aviso.replace(/_/g, ' ')
}

function metodoHumano(metodo: string): string {
  return METODO_LABELS[metodo as MetodoExtraccion] ?? metodo.replace(/_/g, ' ')
}

function parseListaPython(raw: string): string[] {
  return raw
    .split(',')
    .map((item) => item.trim().replace(/^['"]|['"]$/g, ''))
    .filter(Boolean)
}

function describirJsonEvento(data: Record<string, unknown>, evento: Event): string | null {
  if (typeof data.resultado === 'string') {
    const resultado = data.resultado as Resultado
    const fallos = Array.isArray(data.reglas_ko) ? data.reglas_ko.map(String) : []
    const por = typeof data.por === 'string' && data.por ? ` Se recalculó porque ${data.por}.` : ''
    if (fallos.length === 0) {
      return `La norma decidió ${resultadoFrase(resultado)}. Todas las reglas se cumplen.${por}`
    }
    const verbo = fallos.length === 1 ? 'no se cumple' : 'no se cumplen'
    return `La norma decidió ${resultadoFrase(resultado)} porque ${verbo} ${listarReglas(fallos)}.${por}`
  }
  if (data.linaje === 'sin impacto') {
    return 'No hizo falta recalcular: el cambio de maestro o ERP no afecta a esta factura.'
  }
  if (typeof data.pendiente === 'string') {
    const extract = typeof data.extract === 'string' && data.extract ? ` La extracción quedó en ${data.extract}.` : ''
    return `No se decidió porque aún no hay datos leídos.${extract}`
  }
  if (data.aviso === 'duplicado_sospechoso' || data.accion) {
    const otros = Array.isArray(data.con) ? data.con.map(String) : []
    const copias = otros.length ? ` de ${otros.join(', ')}` : ''
    if (data.accion === 'quitado') return 'Se quitó la marca de posible copia.'
    return `Se marcó como posible copia${copias}.`
  }
  if (data.tipo === 'erp_descarga') {
    const version = typeof data.version === 'string' ? data.version : null
    return version
      ? `Se descargó el snapshot ${version} del ERP 2009.`
      : 'Se descargó un snapshot nuevo del ERP 2009.'
  }
  if (evento.etapa === 'emit' && data.entrega) {
    const lote = typeof data.lote === 'number' ? data.lote : null
    const lineas = typeof data.lineas === 'number' ? data.lineas : null
    if (lote !== null && lineas !== null) {
      const archivo = typeof data.entrega === 'string' ? data.entrega : 'outcomes.jsonl'
      return `Se escribió ${archivo} del lote ${lote}: ${formatNumber(lineas)} líneas.`
    }
    return evento.file_id ? 'Se escribió la línea de entrega de este fichero.' : 'Se escribió el fichero de entrega.'
  }
  return null
}

function describirParesEvento(detalle: string): string | null {
  if (/^GET \/erp\//.test(detalle)) {
    const pagina = detalle.match(/pagina['":\s]+(\d+)/)
    if (detalle.includes('/erp/estado')) return 'Se consultó el estado del ERP 2009.'
    if (pagina) return `Se pidió la página ${pagina[1]} de asientos al ERP 2009.`
    return `Petición al ERP 2009: ${detalle.replace(/^GET /, '')}.`
  }

  if (/copia exacta de /i.test(detalle)) {
    const match = detalle.match(/copia exacta de (.+)$/i)
    return match ? `Es una copia exacta de ${match[1].trim()}.` : 'Es una copia exacta de otro PDF.'
  }

  const lote = detalle.match(/\blote=(\d+)/)
  const paginas = detalle.match(/\bpaginas=(\d+)/)
  const texto = detalle.match(/\btexto=(si|no)/)
  if (lote || paginas || texto) {
    const partes: string[] = []
    if (lote) partes.push(`Es de ${loteNombre(Number(lote[1]))}`)
    if (paginas) {
      const n = Number(paginas[1])
      partes.push(n === 1 ? 'tiene 1 página' : `tiene ${n} páginas`)
    }
    if (texto?.[1] === 'no') partes.push('va escaneada, sin texto que se pueda copiar')
    else if (texto?.[1] === 'si') partes.push('tiene texto seleccionable')
    if (partes.length === 0) return 'Se registró el PDF.'
    const cabeza = partes[0]
    const resto = partes.slice(1)
    if (resto.length === 0) return `${cabeza}.`
    if (resto.length === 1) return `${cabeza} y ${resto[0]}.`
    return `${cabeza}, ${resto.slice(0, -1).join(', ')} y ${resto[resto.length - 1]}.`
  }

  if (detalle.startsWith('import:')) {
    const metodo = detalle.slice('import:'.length)
    if (metodo === 'cache') {
      return 'Los datos se tomaron de una lectura anterior, sin volver a llamar al modelo.'
    }
    if (metodo === 'llm_vision') {
      return 'Los datos se importaron de una lectura del modelo sobre la imagen del PDF.'
    }
    if (metodo === 'llm_texto') {
      return 'Los datos se importaron de una lectura del modelo sobre el texto del PDF.'
    }
    if (metodo === 'plantilla') {
      return 'Los datos se importaron de una lectura por plantilla del proveedor.'
    }
    return `Los datos se importaron (${metodoHumano(metodo)}).`
  }

  const extract = detalle.match(/^(plantilla|llm_texto|llm_vision|cache)\b(.*)$/)
  if (extract) {
    const metodo = extract[1]
    const resto = extract[2]
    const avisosMatch = resto.match(/avisos=\[([^\]]*)\]/)
    const avisos = avisosMatch ? parseListaPython(avisosMatch[1]).map(avisoHumano) : []
    const modelo = resto.match(/\bmodelo=(\S+)/)?.[1]
    const respaldo = /\brespaldo=si\b/.test(resto)
    const como =
      metodo === 'cache'
        ? 'Se reutilizó una lectura anterior del modelo'
        : metodo === 'llm_vision'
          ? 'El modelo de lenguaje leyó el PDF como imagen'
          : metodo === 'llm_texto'
            ? 'El modelo de lenguaje leyó el texto del PDF'
            : 'Se leyó con la plantilla del proveedor'
    const extra: string[] = []
    if (modelo) extra.push(`con ${modelo}`)
    if (respaldo) extra.push('usando el modelo de respaldo')
    const cabeza = extra.length ? `${como} (${extra.join(', ')})` : como
    const cola = avisos.length ? `. ${avisos.map((aviso) => frase(aviso.toLowerCase())).join('. ')}.` : '.'
    return `${cabeza}${cola}`
  }

  return null
}

/** El `detalle` crudo del backend (`lote=1 paginas=1 texto=no`, JSON, import:cache…) en una frase. */
export function describirEvento(evento: Event): string {
  const detalle = evento.detalle?.trim() ?? ''

  if (detalle.startsWith('{')) {
    try {
      const parsed: unknown = JSON.parse(detalle)
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        const fraseJson = describirJsonEvento(parsed as Record<string, unknown>, evento)
        if (fraseJson) return fraseJson
      }
    } catch {
      /* no era JSON: se sigue con los otros formatos */
    }
  }

  const pares = detalle ? describirParesEvento(detalle) : null
  if (pares) return pares

  if (evento.error_codigo && detalle) {
    return `${evento.error_codigo.replace(/-/g, ' ').toLowerCase()}: ${frase(detalle)}`
  }
  if (evento.error_codigo) return `Quedó en ${evento.error_codigo.replace(/-/g, ' ').toLowerCase()}.`
  if (detalle) return frase(detalle)
  if (evento.estado === 'ok') return `${ETAPA_ACCIONES[evento.etapa]}.`
  return ESTADO_EVENTO_LABELS[evento.estado]
}

/** Cómo fue el paso: resultado + tiempo + tokens, sin filas clave/valor. */
export function describirPasoEvento(evento: Event): string {
  const partes = [describirEvento(evento)]
  if (evento.intento > 1) partes.push(`Hizo falta el intento ${evento.intento}.`)
  if (evento.latencia_ms !== null && evento.latencia_ms > 0) {
    partes.push(`Tardó ${formatMs(evento.latencia_ms)}.`)
  }
  if (evento.tokens_in !== null || evento.tokens_out !== null) {
    partes.push(
      `Consumió ${formatNumber(evento.tokens_in ?? 0)} tokens de entrada y ${formatNumber(evento.tokens_out ?? 0)} de salida.`,
    )
  }
  if (evento.coste_eur !== null && evento.coste_eur > 0) {
    partes.push(`Coste registrado: ${formatEur(evento.coste_eur, 5)}.`)
  }
  if (evento.version && !describirEvento(evento).includes(evento.version)) {
    if (evento.etapa === 'decide') partes.push(`Con la norma ${evento.version}.`)
    else if (evento.etapa === 'extract') partes.push(`Extractor ${evento.version}.`)
    else partes.push(`Con la versión ${evento.version}.`)
  }
  return partes.join(' ')
}

function valorEvidencia(value: unknown): string {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'boolean') return value ? 'sí' : 'no'
  if (typeof value === 'number') return Number.isInteger(value) ? formatNumber(value) : formatAmount(value)
  if (Array.isArray(value)) {
    return value.map((item) => (typeof item === 'string' ? avisoHumano(item) : String(item))).join(', ')
  }
  const text = String(value)
  if (/^-?\d+(?:[.,]\d+)?$/.test(text) && text.includes('.')) {
    const amount = Number(text)
    if (!Number.isNaN(amount) && amount >= 1) return formatAmount(amount)
  }
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) return formatDate(text)
  return text
}

/** La evidencia de una regla, en frases. No se pinta como diccionario. */
export function describirEvidencia(evidencia: Record<string, unknown>): string[] {
  const frases: string[] = []
  const used = new Set<string>()

  const take = (key: string) => {
    if (!(key in evidencia) || used.has(key)) return ''
    used.add(key)
    return valorEvidencia(evidencia[key])
  }

  const ibanFactura = take('iban_factura')
  const ibanMaestro = take('iban_maestro')
  if (ibanFactura || ibanMaestro) {
    frases.push(
      ibanFactura && ibanMaestro
        ? `El IBAN de la factura es ${ibanFactura} y el del maestro es ${ibanMaestro}.`
        : `IBAN visto: ${ibanFactura || ibanMaestro}.`,
    )
  }

  const base = take('base')
  const iva = take('iva')
  const total = take('total')
  if (base || iva || total) {
    const trozos = [
      base && `base ${base}`,
      iva && `IVA ${iva}`,
      total && `total ${total}`,
    ].filter(Boolean)
    frases.push(`Cuentas de la factura: ${trozos.join(', ')}.`)
  }

  const fecha = take('fecha')
  const corte = take('fecha_corte')
  if (fecha || corte) {
    frases.push(
      [fecha && `La factura es del ${fecha}`, corte && `la fecha de corte es el ${corte}`]
        .filter(Boolean)
        .join(' y ') + '.',
    )
  }

  const pedido = take('pedido')
  const importe = take('importe') || take('importe_erp')
  if (pedido && importe) frases.push(`El pedido ${pedido} es de ${importe}.`)
  else if (pedido) frases.push(`El pedido es ${pedido}.`)
  else if (importe) frases.push(`El importe comparado es ${importe}.`)

  const asiento = take('asiento')
  if (asiento) frases.push(`El asiento del ERP es ${asiento}.`)

  const proveedor = take('proveedor')
  if (proveedor) frases.push(`Proveedor del maestro: ${proveedor}.`)

  const nif = take('nif')
  if (nif) frases.push(`El NIF comparado es ${nif}.`)

  const avisos = take('avisos')
  if (avisos) frases.push(`Al leer el PDF se vio: ${avisos.toLowerCase()}.`)

  const texto = take('texto_sospechoso')
  if (texto) frases.push(`El documento dice: “${texto}”.`)

  const confianza = take('confianza')
  if (confianza) frases.push(`Confianza de la lectura: ${confianza}.`)

  if (evidencia.no_pagar === true) {
    used.add('no_pagar')
    frases.push('Esta regla, si falla, impide pagar.')
  }

  for (const [key, value] of Object.entries(evidencia)) {
    if (used.has(key) || value === null || value === undefined || value === '') continue
    const humano = valorEvidencia(value)
    if (!humano || humano === '—' || humano === 'false') continue
    frases.push(`${frase(key.replace(/_/g, ' '))} ${humano}.`)
  }

  return frases
}
