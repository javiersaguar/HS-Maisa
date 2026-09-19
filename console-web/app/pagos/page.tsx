'use client'

import { useCallback, useState } from 'react'
import { BRAND } from '@/lib/config'
import { fetchAvisos, fetchBonusResumen, fetchCalendario, fetchProveedores } from '@/lib/api/bonus'
import { useAsync } from '@/hooks/useAsync'
import { useConfianzaDisponible } from '@/hooks/useConfianza'
import { AvisosBonus } from '@/components/pagos/AvisosBonus'
import { CabeceraPagos } from '@/components/pagos/CabeceraPagos'
import { CalendarioTesoreria } from '@/components/pagos/CalendarioTesoreria'
import { ListaPagos, SIN_FILTROS, type FiltrosPagos } from '@/components/pagos/ListaPagos'
import { TablaProveedores } from '@/components/pagos/TablaProveedores'
import { ErrorCard } from '@/components/ui/states'

/** El calendario pide hasta 1000: 540 facturas caben enteras y la paginación es en cliente. */
const LIMITE = 1000

/**
 * Pagos: el calendario de tesorería del bonus (K1) sobre las decisiones PAGAR vigentes. Sólo lectura;
 * contrato en docs/api/bonus.md. Si K3 responde, cada pago lleva además su confianza.
 */
export default function PagosPage() {
  const [filtros, setFiltros] = useState<FiltrosPagos>(SIN_FILTROS)

  const resumen = useAsync(useCallback(() => fetchBonusResumen(), []), [])
  const proveedores = useAsync(useCallback(() => fetchProveedores(), []), [])
  const avisos = useAsync(useCallback(() => fetchAvisos(), []), [])
  const confianza = useConfianzaDisponible()
  const conConfianza = Boolean(confianza.data)

  const calendario = useAsync(
    useCallback(
      () =>
        fetchCalendario({
          semana: filtros.semana ?? undefined,
          proveedor: filtros.proveedor ?? undefined,
          lote: filtros.lote ?? undefined,
          vencido: filtros.vencido ?? undefined,
          limite: LIMITE,
          conConfianza,
        }),
      [filtros, conConfianza],
    ),
    [filtros, conConfianza],
    // Se espera al sondeo de K3 para no pedir el calendario dos veces.
    { enabled: !confianza.loading },
  )

  const proveedorNombre =
    filtros.proveedor === null
      ? null
      : (proveedores.data?.find((p) => p.proveedor_id === filtros.proveedor)?.beneficiario ?? filtros.proveedor)

  return (
    <div className="px-5 py-6 sm:px-8">
      <title>{`Pagos · ${BRAND}`}</title>
      <div className="mx-auto max-w-[1380px] pb-10">
        <CabeceraPagos resumen={resumen.data} />
        {resumen.error && !resumen.data && (
          <div className="mt-6">
            <ErrorCard error={resumen.error} onRetry={resumen.refresh} retrying={resumen.loading} />
          </div>
        )}

        <CalendarioTesoreria
          semanaActiva={filtros.semana}
          onSemana={(semana) => setFiltros((actual) => ({ ...actual, semana }))}
        />

        <TablaProveedores
          proveedores={proveedores.data}
          error={proveedores.error}
          loading={proveedores.loading}
          onRetry={proveedores.refresh}
          activo={filtros.proveedor}
          onSelect={(proveedor) => setFiltros((actual) => ({ ...actual, proveedor }))}
        />

        <ListaPagos
          calendario={calendario.data}
          error={calendario.error}
          loading={calendario.loading}
          onRetry={calendario.refresh}
          filtros={filtros}
          onFiltros={setFiltros}
          semanas={resumen.data ? Object.keys(resumen.data.semanas).sort() : []}
          lotes={resumen.data?.lotes ?? []}
          proveedorNombre={proveedorNombre}
          conConfianza={conConfianza}
        />

        <AvisosBonus avisos={avisos.data} error={avisos.error} />
      </div>
    </div>
  )
}
