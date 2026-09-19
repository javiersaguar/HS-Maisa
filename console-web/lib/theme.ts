/**
 * The single place where brand colours consumed by JavaScript live
 * (charts, inline SVG, computed styles). Tailwind classes keep using the
 * same hex values; do not introduce a second palette.
 */

export const COLORS = {
  canvas: '#f7f8f5',
  surface: '#ffffff',
  primary: '#164f45',
  primaryDark: '#0d4037',
  primarySoft: '#eff8f3',
  mint: '#67d4ad',
  mintStrong: '#35b889',
  lime: '#d6f52a',
  limeSoft: '#fff6c9',
  danger: '#bd3434',
  dangerSoft: '#f05b5b',
  text: '#17211e',
  textMuted: '#68736d',
  textFaint: '#9aa39e',
  border: '#e1e5df',
  track: '#e7e9e5',
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
  if (score >= 90) return COLORS.mintStrong
  if (score >= 75) return '#8b5cf6'
  if (score > 0) return COLORS.dangerSoft
  return '#b8c0ba'
}
