import Link from 'next/link'
import { ChevronRight } from 'lucide-react'
import type { EtapaResumen } from '@/lib/types'
import { ETAPA_DESCRIPCIONES, ETAPA_GRANO, ETAPA_LABELS, formatEur, formatMs, formatNumber, formatRelative, tooltipCoberturaEtapa } from '@/lib/format'
import { Card } from '@/components/ui/Card'
import { ProgressRing } from '@/components/ui/ProgressRing'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { EtapaIcon, saludEtapa } from './EtapaIcon'

export function EtapaCard({ etapa, ficheros }: { etapa: EtapaResumen; ficheros: number }) {
  const salud = saludEtapa(etapa, ficheros)
  const conCoste = etapa.costeEur > 0
  const grano = ETAPA_GRANO[etapa.etapa]
  const ficherosOk = etapa.etapa === 'emit' && etapa.eventos === 0 && ficheros > 0 ? ficheros : etapa.ficherosOk
  const metrica =
    grano === 'lote' ? 'Peticiones' : grano === 'cambio' ? 'Marcados' : 'Ficheros OK'
  const valorMetrica =
    grano === 'lote' ? formatNumber(etapa.eventos) : `${formatNumber(ficherosOk)} / ${formatNumber(ficheros)}`
  return (
    <Card className="group w-[min(390px,calc(100vw-64px))] shrink-0 p-5 transition hover:-translate-y-0.5 hover:border-accent-line hover:shadow-[0_8px_24px_rgba(43,55,51,0.08)]">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center bg-accent-soft text-accent-dark transition-transform duration-300 group-hover:scale-105">
            <EtapaIcon etapa={etapa.etapa} />
          </div>
          <div>
            <h3 className="text-[14px] font-semibold">
              {ETAPA_LABELS[etapa.etapa]} <span className="font-mono text-[12px] font-normal text-muted">{etapa.etapa}</span>
            </h3>
            <div className="mt-1 flex items-center gap-2">
              <StatusBadge tone={salud.tone}>{salud.label}</StatusBadge>
            </div>
          </div>
        </div>
        <ProgressRing value={salud.cobertura} tooltip={tooltipCoberturaEtapa(etapa, ficheros, salud.cobertura)} />
      </div>
      <p className="mt-4 min-h-9 text-[14px] leading-5 text-ink-soft">{ETAPA_DESCRIPCIONES[etapa.etapa]}</p>
      <div className="mt-5 grid grid-cols-2 gap-y-3 border-t border-line-soft pt-4 text-[13px]">
        <div>
          <p className="text-muted">{metrica}</p>
          <p className="mt-1 font-semibold">{valorMetrica}</p>
        </div>
        <div>
          <p className="text-muted">Reintentos</p>
          <p className="mt-1 font-semibold">{formatNumber(etapa.reintentos)}</p>
        </div>
        <div>
          <p className="text-muted">Latencia media</p>
          <p className="mt-1 font-semibold">{formatMs(etapa.latenciaMediaMs)}</p>
        </div>
        <div>
          <p className="text-muted">{conCoste ? 'Coste' : 'Último evento'}</p>
          <p className="mt-1 font-semibold">{conCoste ? formatEur(etapa.costeEur, 2) : formatRelative(etapa.ultimoEventoEn)}</p>
        </div>
      </div>
      <Link
        href={`/workers/${etapa.etapa}`}
        className="mt-5 flex w-full items-center justify-center gap-1 border border-line py-2 text-[14px] font-semibold text-accent-dark transition hover:bg-accent-soft"
      >
        Ver eventos <ChevronRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
      </Link>
    </Card>
  )
}
