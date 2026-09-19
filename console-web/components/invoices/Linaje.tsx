import type { Decision } from '@/lib/types'
import { describirLinaje } from '@/lib/format'

/**
 * De qué sale la decisión vigente. La consola no decide: aquí sólo se cuenta
 * qué norma, qué fecha de corte y qué fuentes se cruzaron.
 */
export function Linaje({ decision }: { decision: Decision | null }) {
  return (
    <div className="mt-3 rounded-xl border border-[#dfe4de] bg-white p-4 text-[13px] leading-5 text-[#52605a]">
      {decision ? (
        <p>{describirLinaje(decision)}</p>
      ) : (
        <p>Todavía no hay decisión. Se tomará en el próximo procesamiento. Desde aquí solo se consulta.</p>
      )}
    </div>
  )
}
