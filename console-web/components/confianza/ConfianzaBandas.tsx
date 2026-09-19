'use client'

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { BandaConfianza, ConfianzaResumen } from '@/lib/types'
import { COLORS } from '@/lib/theme'

/*
 * Bandas de confianza por resultado (`/confianza/resumen`), una barra apilada por PAGAR / NO_PAGAR / ESCALAR.
 * Hecha para el panel, pero todavía no se monta: el panel está en otra refactorización.
 */

const BANDAS: Array<[BandaConfianza, string]> = [
  ['alta', '#087b5b'],
  ['media', '#d9a21b'],
  ['baja', COLORS.danger],
]

const RESULTADOS = ['PAGAR', 'NO_PAGAR', 'ESCALAR'] as const

const AXIS = { fill: COLORS.textMuted, fontSize: 12 }

export function ConfianzaBandas({ resumen }: { resumen: ConfianzaResumen }) {
  const data = RESULTADOS.map((resultado) => ({
    resultado,
    ...(resumen.por_resultado[resultado] ?? { alta: 0, media: 0, baja: 0 }),
  }))

  return (
    <figure className="h-[180px] w-full">
      <figcaption className="sr-only">
        Confianza en la clasificación por resultado:{' '}
        {data.map((fila) => `${fila.resultado} ${fila.alta} alta, ${fila.media} media, ${fila.baja} baja`).join('; ')}
      </figcaption>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 12, bottom: 0, left: 0 }} barCategoryGap={10}>
          <CartesianGrid horizontal={false} stroke={COLORS.track} />
          <XAxis type="number" allowDecimals={false} tick={AXIS} tickLine={false} axisLine={false} />
          <YAxis type="category" dataKey="resultado" tick={AXIS} tickLine={false} axisLine={false} width={84} />
          <Tooltip cursor={{ fill: COLORS.primarySoft }} />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
          {BANDAS.map(([banda, color]) => (
            <Bar key={banda} dataKey={banda} name={banda} stackId="bandas" fill={color} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </figure>
  )
}
