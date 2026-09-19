'use client'

import { useCallback, useState, type FormEvent } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Programa, SemanaTesoreria, Tesoreria } from '@/lib/types'
import { fetchTesoreria } from '@/lib/api/bonus'
import { formatDate, formatImporte, formatNumber, formatSemana } from '@/lib/format'
import { COLORS } from '@/lib/theme'
import { useAsync } from '@/hooks/useAsync'
import { Card } from '@/components/ui/Card'
import { Spinner } from '@/components/ui/Spinner'
import { ErrorState, LoadingState } from '@/components/ui/states'

/*
 * Colores validados (dataviz, modo claro): vencido danger · en plazo mintStrong pasan CVD; el contraste
 * bajo del verde se compensa con leyenda, tooltip y la lista de pagos como vista en tabla.
 * Nunca dos ejes: el acumulado (hasta 2,4 M€) va en su propio gráfico, alineado por semana (syncId).
 */
const VENCIDO = COLORS.danger
const EN_PLAZO = COLORS.mintStrong
const ACUMULADO = COLORS.primary
const PROGRAMA = COLORS.primary
const GRID = COLORS.border
const AXIS = { fontSize: 11, fill: COLORS.textMuted }

const TOPE_DEMO = 150000

/** Eje en miles: "150 k€". Los importes exactos van en el tooltip. */
const kEur = (value: number) =>
  value >= 1_000_000 ? `${(value / 1_000_000).toLocaleString('es-ES', { maximumFractionDigits: 1 })} M€` : `${Math.round(value / 1000)} k€`

interface PuntoSemana {
  semana: string
  etiqueta: string
  desde: string
  numero: number
  vencidos_numero: number
  /** Números sólo para dibujar; el texto sale de los strings de la API. */
  vencido: number
  enPlazo: number
  acumulado: number
  raw: SemanaTesoreria
}

function puntos(semanas: SemanaTesoreria[]): PuntoSemana[] {
  return semanas.map((s) => {
    const importe = Number(s.importe_eur)
    const vencido = Number(s.vencidos_importe_eur)
    return {
      semana: s.semana,
      etiqueta: formatSemana(s.semana),
      desde: s.desde,
      numero: s.numero,
      vencidos_numero: s.vencidos_numero,
      vencido,
      enPlazo: Math.max(0, importe - vencido),
      acumulado: Number(s.acumulado_eur),
      raw: s,
    }
  })
}

function Leyenda({ items }: { items: Array<{ color: string; label: string; line?: boolean }> }) {
  return (
    <div className="flex flex-wrap items-center gap-4 text-[12px] text-[#52605a]">
      {items.map((item) => (
        <span key={item.label} className="inline-flex items-center gap-1.5">
          <span
            className={item.line ? 'h-0.5 w-4 rounded' : 'size-2.5 rounded-sm'}
            style={{ backgroundColor: item.color }}
          />
          {item.label}
        </span>
      ))}
    </div>
  )
}

type TooltipProps = { active?: boolean; payload?: Array<{ payload: unknown }> }

function TooltipSemana({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload as PuntoSemana
  return (
    <div className="rounded-lg border border-[#e1e5df] bg-white px-3 py-2 text-[12px] shadow-[0_8px_24px_rgba(20,55,45,0.12)]">
      <p className="font-semibold text-[#17211e]">
        {p.semana} · desde {formatDate(p.desde)}
      </p>
      <p className="mt-1 text-[#52605a]">
        {formatNumber(p.numero)} facturas · <b className="font-semibold text-[#17211e]">{formatImporte(p.raw.importe_eur)}</b>
      </p>
      {p.vencidos_numero > 0 && (
        <p className="text-[#52605a]">
          {formatNumber(p.vencidos_numero)} vencidas · {formatImporte(p.raw.vencidos_importe_eur)}
        </p>
      )}
      <p className="text-[#52605a]">Acumulado {formatImporte(p.raw.acumulado_eur)}</p>
      <p className="mt-1 text-[11px] text-[#9aa39e]">Pulsa la barra para ver sus pagos</p>
    </div>
  )
}

function TooltipPrograma({ active, payload }: TooltipProps) {
  if (!active || !payload?.length) return null
  const s = (payload[0].payload as { raw: Programa['semanas'][number] }).raw
  return (
    <div className="rounded-lg border border-[#e1e5df] bg-white px-3 py-2 text-[12px] shadow-[0_8px_24px_rgba(20,55,45,0.12)]">
      <p className="font-semibold text-[#17211e]">
        {s.semana} · desde {formatDate(s.desde)}
      </p>
      <p className="mt-1 text-[#52605a]">
        Se pagan {formatNumber(s.numero)} · <b className="font-semibold text-[#17211e]">{formatImporte(s.importe_eur)}</b>
      </p>
      {s.supera_tope && <p className="font-semibold text-[#bd3434]">Supera el tope (una factura sola no cabe)</p>}
      <p className="text-[#52605a]">
        Quedan para después {formatNumber(s.arrastrado_numero)} · {formatImporte(s.arrastrado_importe_eur)}
      </p>
    </div>
  )
}

function frasePrograma(programa: Programa): string {
  const tope = formatImporte(programa.tope_semanal_eur).replace(',00', '')
  const alDia = programa.semanas_para_ponerse_al_dia
  const todo = programa.semanas_para_pagarlo_todo
  const partes = [`Con ${tope} por semana`]
  partes.push(alDia === null ? 'no se llega a estar al día' : `al día en ${formatNumber(alDia)} semanas`)
  const cola = todo === null ? '' : `; todo pagado en ${formatNumber(todo)}`
  return `${partes.join(', ')}${cola}.`
}

function GraficoPrograma({ programa }: { programa: Programa }) {
  const tope = Number(programa.tope_semanal_eur)
  const data = programa.semanas.map((s) => ({
    etiqueta: formatSemana(s.semana),
    importe: Number(s.importe_eur),
    supera: s.supera_tope,
    raw: s,
  }))
  const superan = programa.semanas.filter((s) => s.supera_tope).length
  return (
    <div className="mt-6 border-t border-[#edf0ec] pt-5 animate-in fade-in duration-300">
      <p className="text-[18px] font-semibold tracking-[-0.02em] text-[#17211e]">{frasePrograma(programa)}</p>
      <p className="mt-1 text-[13px] text-[#8a958e]">
        Lo vencido primero, por orden de vencimiento, sin pasar del tope. {formatNumber(programa.numero)} facturas ·{' '}
        {formatImporte(programa.importe_eur)}
        {programa.sin_programar_numero > 0 && ` · ${formatNumber(programa.sin_programar_numero)} sin programar`}
        {superan > 0 && ` · ${superan} semana${superan === 1 ? '' : 's'} por encima del tope`}
      </p>
      <div className="mt-3">
        <Leyenda
          items={[
            { color: PROGRAMA, label: 'Pago programado' },
            ...(superan > 0 ? [{ color: VENCIDO, label: 'Supera el tope' }] : []),
            { color: COLORS.textFaint, label: 'Tope semanal', line: true },
          ]}
        />
      </div>
      <div className="mt-2 h-[190px]" role="img" aria-label={frasePrograma(programa)}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }} barCategoryGap={2}>
            <CartesianGrid vertical={false} stroke={GRID} />
            <XAxis dataKey="etiqueta" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} interval="preserveStartEnd" />
            <YAxis tickFormatter={kEur} tick={AXIS} tickLine={false} axisLine={false} width={56} />
            <Tooltip content={<TooltipPrograma />} cursor={{ fill: COLORS.primarySoft }} />
            <ReferenceLine y={tope} stroke={COLORS.textFaint} strokeDasharray="4 4" />
            <Bar dataKey="importe" radius={[4, 4, 0, 0]} maxBarSize={28} isAnimationActive={false}>
              {data.map((d) => (
                <Cell key={d.raw.semana} fill={d.supera ? VENCIDO : PROGRAMA} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

/**
 * El calendario semanal de tesorería: barras por semana de ejecución (vencido en rojo, en plazo en
 * verde), el acumulado debajo y, con un tope, el programa que lo reparte.
 */
export function CalendarioTesoreria({
  semanaActiva,
  onSemana,
}: {
  semanaActiva: string | null
  onSemana: (semana: string | null) => void
}) {
  const [tope, setTope] = useState<number | undefined>(undefined)
  const [borrador, setBorrador] = useState('')
  const loader = useCallback(() => fetchTesoreria(tope), [tope])
  // useAsync conserva el último dato bueno: si un tope da 400, el calendario sigue y el error va junto al campo.
  const { data: teso, error, loading, refresh } = useAsync<Tesoreria>(loader, [tope])

  const aplicar = (event: FormEvent) => {
    event.preventDefault()
    const valor = Number(borrador.replace(/\./g, '').replace(',', '.'))
    setTope(borrador.trim() === '' ? undefined : valor)
  }

  const quitar = () => {
    setBorrador('')
    setTope(undefined)
  }

  const data_ = teso ? puntos(teso.semanas) : []
  const corte = teso ? formatSemana(teso.semana_corte) : null

  return (
    <Card className="mt-6 rounded-2xl border-[#e1e7e2] p-5 shadow-[0_8px_28px_rgba(20,55,45,0.045)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-[22px] font-semibold tracking-[-0.025em]">Calendario de tesorería</h2>
          <p className="mt-1 text-[13px] text-[#8a958e]">
            Importe por semana de vencimiento. Lo vencido se ejecutaría el día de corte; la línea roja discontinua marca
            esa semana.
          </p>
        </div>
        <form onSubmit={aplicar} className="flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1 text-[12px] font-semibold text-[#52605a]">
            Tope semanal (€)
            <input
              inputMode="decimal"
              value={borrador}
              onChange={(event) => setBorrador(event.target.value)}
              placeholder={TOPE_DEMO.toLocaleString('es-ES')}
              className="h-9 w-40 rounded-lg border border-[#d5e0d9] bg-white px-3 text-[14px] font-normal tabular-nums outline-none focus:border-[#164f45] focus:ring-2 focus:ring-[#164f45]/15"
            />
          </label>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-[#164f45] px-4 text-[14px] font-semibold text-white transition hover:bg-[#0d4037] disabled:opacity-60"
          >
            {loading && tope !== undefined && <Spinner className="size-3 text-white" />}
            Programar
          </button>
          {borrador === '' && tope === undefined && (
            <button
              type="button"
              onClick={() => {
                setBorrador(TOPE_DEMO.toLocaleString('es-ES'))
                setTope(TOPE_DEMO)
              }}
              className="h-9 rounded-lg border border-[#d5e0d9] bg-white px-3 text-[13px] font-semibold text-[#315d53] transition hover:bg-[#eff8f3]"
            >
              Probar con {TOPE_DEMO.toLocaleString('es-ES')} €
            </button>
          )}
          {tope !== undefined && (
            <button
              type="button"
              onClick={quitar}
              className="h-9 rounded-lg px-3 text-[13px] font-semibold text-[#315d53] underline"
            >
              Quitar tope
            </button>
          )}
        </form>
      </div>

      {error && tope !== undefined && teso && (
        <p role="alert" className="mt-3 rounded-lg border border-[#f1dada] bg-[#fff5f5] px-3 py-2 text-[13px] text-[#8f2a2a]">
          {error.message}
        </p>
      )}

      {!teso ? (
        error ? (
          <ErrorState error={error} onRetry={refresh} retrying={loading} />
        ) : (
          <LoadingState label="Cargando calendario" rows={4} />
        )
      ) : (
        <>
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            <Leyenda
              items={[
                { color: VENCIDO, label: `Vencido · ${formatImporte(teso.vencido_importe_eur)}` },
                { color: EN_PLAZO, label: `En plazo · ${formatImporte(teso.en_plazo_importe_eur)}` },
              ]}
            />
            {semanaActiva && (
              <button onClick={() => onSemana(null)} className="text-[12px] font-semibold text-[#315d53] underline">
                Quitar filtro {formatSemana(semanaActiva)}
              </button>
            )}
          </div>
          <div className="mt-2 h-[240px]" role="img" aria-label={`Importe por semana: ${formatImporte(teso.importe_eur)} en ${teso.semanas.length} semanas`}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={data_}
                syncId="tesoreria"
                margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
                barCategoryGap={2}
                onClick={(state) => {
                  const index = Number((state as { activeTooltipIndex?: number | string } | null)?.activeTooltipIndex)
                  const punto = Number.isInteger(index) ? data_[index] : undefined
                  if (punto) onSemana(punto.semana === semanaActiva ? null : punto.semana)
                }}
              >
                <CartesianGrid vertical={false} stroke={GRID} />
                <XAxis dataKey="etiqueta" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} interval="preserveStartEnd" />
                <YAxis tickFormatter={kEur} tick={AXIS} tickLine={false} axisLine={false} width={56} />
                <Tooltip content={<TooltipSemana />} cursor={{ fill: COLORS.primarySoft }} />
                {corte && <ReferenceLine x={corte} stroke={VENCIDO} strokeDasharray="4 4" />}
                <Bar dataKey="vencido" stackId="s" fill={VENCIDO} maxBarSize={28} isAnimationActive={false} className="cursor-pointer">
                  {data_.map((d) => (
                    <Cell key={d.semana} fillOpacity={semanaActiva && semanaActiva !== d.semana ? 0.3 : 1} />
                  ))}
                </Bar>
                <Bar dataKey="enPlazo" stackId="s" fill={EN_PLAZO} radius={[4, 4, 0, 0]} maxBarSize={28} isAnimationActive={false} className="cursor-pointer">
                  {data_.map((d) => (
                    <Cell key={d.semana} fillOpacity={semanaActiva && semanaActiva !== d.semana ? 0.3 : 1} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <p className="mt-4 text-[12px] font-semibold uppercase tracking-[0.1em] text-[#78867e]">
            Acumulado · {formatImporte(teso.importe_eur)}
          </p>
          <div className="mt-1 h-[120px]" role="img" aria-label={`Acumulado hasta ${formatImporte(teso.importe_eur)}`}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data_} syncId="tesoreria" margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid vertical={false} stroke={GRID} />
                <XAxis dataKey="etiqueta" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} interval="preserveStartEnd" />
                <YAxis tickFormatter={kEur} tick={AXIS} tickLine={false} axisLine={false} width={56} />
                <Tooltip content={<TooltipSemana />} />
                {corte && <ReferenceLine x={corte} stroke={VENCIDO} strokeDasharray="4 4" />}
                <Area
                  type="monotone"
                  dataKey="acumulado"
                  stroke={ACUMULADO}
                  strokeWidth={2}
                  fill={ACUMULADO}
                  fillOpacity={0.08}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {teso.programa && !error && <GraficoPrograma programa={teso.programa} />}
        </>
      )}
    </Card>
  )
}
