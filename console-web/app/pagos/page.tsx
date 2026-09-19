'use client'

import { useCallback, useMemo, useState } from 'react'
import { BRAND } from '@/lib/config'
import { fetchBonusResumen, fetchCalendario } from '@/lib/api/bonus'
import { useAsync } from '@/hooks/useAsync'
import { CalendarioMes, agruparPorDia } from '@/components/pagos/CalendarioMes'
import { ListaDia } from '@/components/pagos/ListaDia'
import { EmptyState, ErrorCard, LoadingCard } from '@/components/ui/states'

/** El calendario pide hasta 1000: las 540 de la Caja caben enteras y se agrupan por día en el cliente. */
const LIMITE = 1000

/**
 * Pagos (bonus K1) como agenda: el mes a pantalla completa por fecha de ejecución y, al pinchar un día, un
 * overlay con sus facturas. Sólo lectura sobre las decisiones PAGAR vigentes; contrato en docs/api/bonus.md.
 */
export default function PagosPage() {
  // El resumen sólo aporta el día de corte: la cabecera con totales se quitó para dar sitio al mes.
  const resumen = useAsync(useCallback(() => fetchBonusResumen(), []), [])
  const calendario = useAsync(useCallback(() => fetchCalendario({ limite: LIMITE }), []), [])

  const fechaCorte = resumen.data?.fecha_corte ?? null
  const dias = useMemo(() => agruparPorDia(calendario.data?.pagos ?? []), [calendario.data])
  const meses = useMemo(() => [...new Set([...dias.keys()].map((fecha) => fecha.slice(0, 7)))].sort(), [dias])

  const [mesElegido, setMes] = useState<string | null>(null)
  /** Día con el overlay abierto. Empieza cerrado: ni el día de corte se abre solo. */
  const [dia, setDia] = useState<string | null>(null)
  const cerrar = useCallback(() => setDia(null), [])

  const mes = mesElegido ?? fechaCorte?.slice(0, 7) ?? meses[0] ?? null
  const diaAbierto = dia ? (dias.get(dia) ?? null) : null
  const error = resumen.error ?? calendario.error

  return (
    <div className="flex h-full min-h-0 flex-col px-3 pb-0.5 sm:pr-4 sm:pl-5">
      <title>{`Pagos · ${BRAND}`}</title>
      {error && !calendario.data ? (
        <ErrorCard
          error={error}
          onRetry={() => {
            resumen.refresh()
            calendario.refresh()
          }}
          retrying={resumen.loading || calendario.loading}
        />
      ) : !calendario.data ? (
        <LoadingCard label="Cargando el calendario" />
      ) : !mes ? (
        <EmptyState title="No hay pagos que programar" description="Ninguna decisión PAGAR vigente." />
      ) : (
        <CalendarioMes
          mes={mes}
          meses={meses}
          onMes={setMes}
          dias={dias}
          fechaCorte={fechaCorte}
          diaActivo={diaAbierto ? dia : null}
          onDia={setDia}
        />
      )}
      {diaAbierto && <ListaDia dia={diaAbierto} fechaCorte={fechaCorte} onCerrar={cerrar} />}
    </div>
  )
}
