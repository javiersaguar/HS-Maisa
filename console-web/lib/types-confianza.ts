import type { Resultado } from './types'

/*
 * Confianza en la CLASIFICACIÓN por factura (K3). Contrato: docs/api/confianza.md, nombres exactos.
 * No es `InvoiceFacts.confianza` (0-1, lo segura que fue la lectura del PDF) ni una probabilidad de pago.
 */

export type BandaConfianza = 'alta' | 'media' | 'baja'

/** Una duda con nombre: resta `aplicado` = `puntos` × `factor`. Con `factor` 0 no cuenta (y `por_que` dice por qué). */
export interface ConfianzaDuda {
  id: string
  texto: string
  puntos: number
  factor: number
  aplicado: number
  por_que: string
  fuente?: string
}

export interface ConfianzaOpinion {
  opinion: 'de_acuerdo' | 'desacuerdo' | 'no_se'
  frase: string
  modelo?: string
}

export interface ConfianzaFuente {
  penalizacion: number
  dudas: ConfianzaDuda[]
  a_favor: string[]
  /** Sólo `politica`: lo máximo que pueden restar las preguntas abiertas. */
  tope?: number
  /** Sólo `revisor`, con el revisor LLM encendido; null si no opinó. */
  opinion?: ConfianzaOpinion | null
}

/** Plantilla: `{contraste, campos_distintos}`. Escaneada: `{n, campos_distintos}`. */
export interface ConfianzaLecturas {
  contraste?: boolean
  n?: number
  campos_distintos: string[]
}

/** `GET /confianza/fichero?file_id=` */
export interface ConfianzaFicha {
  api?: number
  file_id: string
  lote: number
  resultado: Resultado
  regla: string | null
  puntuacion: number
  banda: BandaConfianza
  razones: string[]
  causa: string
  metodo: string
  lecturas?: ConfianzaLecturas | null
  mismo_pdf_que: string[]
  fuentes: Record<string, ConfianzaFuente>
  escala?: string
  version?: string
}

/** Fila de `GET /confianza/ficheros`. */
export interface ConfianzaItem {
  file_id: string
  lote: number
  resultado: Resultado
  regla: string | null
  puntuacion: number
  banda: BandaConfianza
  razon_principal: string
  razones: string[]
}

export interface ConfianzaLista {
  api?: number
  items: ConfianzaItem[]
  total: number
  limite?: number
}

export interface ConfianzaQuery {
  banda?: BandaConfianza
  resultado?: Resultado
  lote?: number
  /** 50 por defecto en el backend; máximo 1000. */
  limite?: number
  /** `asc` (defecto): menor confianza primero. */
  orden?: 'asc' | 'desc'
}

/** `GET /confianza/resumen?lote=` */
export interface ConfianzaResumen {
  api?: number
  version: string
  total: number
  bandas: Record<BandaConfianza, number>
  por_resultado: Record<string, Record<BandaConfianza, number>>
  por_lote?: Record<string, Record<BandaConfianza, number>>
  media: number
  umbrales: { alta: number; media: number }
  escala: string
  segundos?: number | string
}
