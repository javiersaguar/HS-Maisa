import type { Decision } from '@/lib/types'
import { describirLinaje, shortHash } from '@/lib/format'

/**
 * De qué sale la decisión vigente. La consola no decide: aquí sólo se cuenta
 * qué norma, qué fecha de corte y qué fuentes se cruzaron.
 */
export function Linaje({ decision }: { decision: Decision | null }) {
  return (
    <div className="mt-3 rounded-[var(--radius-card)] border border-[#dfe4de] bg-white p-4 text-[13px] leading-5 text-[#52605a]">
      {decision ? (
        <>
          <p>{describirLinaje(decision)}</p>
          <p className="mt-2 font-mono text-[11px] text-[#8a958e]">
            maestro {shortHash(decision.maestro_version, 12)} · hechos {shortHash(decision.hechos_hash, 12)}
          </p>
        </>
      ) : (
        <p>Todavía no hay decisión. Se tomará en el próximo procesamiento. Desde aquí solo se consulta.</p>
      )}
    </div>
  )
}
