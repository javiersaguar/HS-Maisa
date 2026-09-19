'use client'

import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import type { Decision } from '@/lib/types'
import { REPROCESS_COMMAND } from '@/lib/config'
import { formatDate, formatDateTime, shortHash } from '@/lib/format'

/**
 * Sustituye a los botones Approve / Reject del prototipo. En Albertitos la consola no decide:
 * la decisión es de la norma como código, y cambiarla es cambiar norma, maestro o ERP y reprocesar.
 * Aquí sólo se enseña de qué versiones sale la decisión vigente.
 */
export function Linaje({ decision }: { decision: Decision | null }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(REPROCESS_COMMAND)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      /* sin permiso de portapapeles: el comando sigue visible */
    }
  }

  const rows: Array<[string, string]> = decision
    ? [
        ['Norma', decision.norma_version],
        ['Fecha de corte', formatDate(decision.fecha_corte)],
        ['Maestro', shortHash(decision.maestro_version, 12)],
        ['ERP', decision.erp_version],
        ['Hechos', shortHash(decision.hechos_hash, 12)],
        ['Decidido', formatDateTime(decision.decidido_en)],
      ]
    : []

  return (
    <div className="mt-3 rounded-xl border border-[#dfe4de] bg-white p-4 text-[13px]">
      <p className="leading-5 text-[#52605a]">
        {decision
          ? `La norma ${decision.norma_version} decide. Aquí sólo se consulta.`
          : 'Sin decisión vigente: se decidirá en el próximo run. Aquí sólo se consulta.'}
      </p>
      {rows.length > 0 && (
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-[#edf0ec] pt-3">
          {rows.map(([label, value]) => (
            <div key={label} className="min-w-0">
              <dt className="text-[11px] font-bold uppercase tracking-[0.1em] text-[#7b8981]">{label}</dt>
              <dd className="truncate font-mono text-[12px] text-[#304d43]" title={value}>
                {value}
              </dd>
            </div>
          ))}
        </dl>
      )}
      <div className="mt-3 flex items-center justify-between gap-2 rounded-lg bg-[#f5f7f3] px-3 py-2">
        <code className="min-w-0 truncate font-mono text-[12px] text-[#164f45]">{REPROCESS_COMMAND}</code>
        <button
          onClick={copy}
          aria-label="Copiar comando"
          className="flex size-7 min-h-0 shrink-0 items-center justify-center rounded-md text-[#315d53] transition hover:bg-[#e6efe9]"
        >
          {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
        </button>
      </div>
      <p className="mt-1.5 text-[12px] text-[#9aa39e]">Recalcula sólo lo afectado si cambia la norma, el maestro o el ERP.</p>
    </div>
  )
}
