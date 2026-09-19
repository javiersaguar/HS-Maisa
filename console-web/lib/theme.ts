/**
 * The single place where brand colours consumed by JavaScript live
 * (charts, inline SVG, computed styles). Tailwind classes keep using the
 * same hex values; do not introduce a second palette.
 */

export const COLORS = {
  canvas: '#f2f2e8',
  surface: '#f8f8f1',
  primary: '#6b8279',
  primaryDark: '#506c63',
  primarySoft: '#e4e8e4',
  mint: '#6b8279',
  mintStrong: '#506c63',
  lime: '#a87a1e',
  limeSoft: '#f3ecd8',
  danger: '#a4483e',
  dangerSoft: '#a4483e',
  text: '#2b3733',
  textMuted: '#6f7772',
  textFaint: '#6f7772',
  border: '#ddddd1',
  track: '#e6e6db',
} as const

export type Tone = 'green' | 'yellow' | 'red' | 'gray'

import type { EstadoEvento, EstadoFichero } from './types'

export function estadoTone(estado: EstadoFichero | null): Tone {
  if (estado === 'PAGAR') return 'green'
  if (estado === 'ESCALAR') return 'yellow'
  if (estado === 'NO_PAGAR') return 'red'
  return 'gray'
}

export function eventoTone(estado: EstadoEvento): Tone {
  if (estado === 'ok') return 'green'
  if (estado === 'retry' || estado === 'pendiente') return 'yellow'
  if (estado === 'error') return 'red'
  return 'gray'
}

/** Colour ramp for coverage gauges (share of files a stage finished). */
export function progressColor(value: number | null): string {
  const score = value ?? 0
  if (score >= 90) return COLORS.primaryDark
  if (score >= 75) return COLORS.primary
  if (score > 0) return COLORS.danger
  return COLORS.border
}
