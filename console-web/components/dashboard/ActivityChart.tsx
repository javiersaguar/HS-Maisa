'use client'

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { MesPunto } from '@/lib/types'
import { formatMonth } from '@/lib/format'
import { COLORS } from '@/lib/theme'
import { Card } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/states'

/** Facturas de la Caja por mes de emisión (`InvoiceFacts.fecha`). */
export function ActivityChart({ data }: { data: MesPunto[] }) {
  const points = data.map((point) => ({ ...point, label: formatMonth(point.mes) }))
  return (
    <Card className="flex min-h-[260px] flex-1 flex-col p-5">
      <div>
        <h2 className="text-[14px] font-semibold">Facturas por mes</h2>
        <p className="text-[14px] text-[#9aa39e]">Según la fecha impresa en la factura</p>
      </div>
      {points.length === 0 ? (
        <EmptyState title="Sin fechas todavía" description="Aparecen cuando la extracción lee las facturas." />
      ) : (
        <div className="mt-4 min-h-[180px] w-full flex-1">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={points} margin={{ top: 8, right: 3, left: -24, bottom: 0 }}>
              <defs>
                <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#cfeee1" stopOpacity={0.7} />
                  <stop offset="100%" stopColor="#f9fbf9" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="#e8ebe6" strokeDasharray="3 3" />
              <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: '#a2aaa5', fontSize: 10 }} dy={8} />
              <YAxis tickLine={false} axisLine={false} tick={{ fill: '#a2aaa5', fontSize: 10 }} allowDecimals={false} />
              <Tooltip
                cursor={{ stroke: '#c9d9d0' }}
                formatter={(value) => [value, 'ficheros']}
                contentStyle={{ borderRadius: 8, border: '1px solid #e0e6e0', fontSize: 12 }}
              />
              <Area type="monotone" dataKey="ficheros" stroke={COLORS.primary} strokeWidth={2} fill="url(#areaFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  )
}
