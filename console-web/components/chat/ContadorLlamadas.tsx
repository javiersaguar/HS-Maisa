'use client'

import { useEffect, useRef, useState } from 'react'
import { Gauge } from 'lucide-react'
import { describirMotivo, type SaludChat } from '@/lib/api/chat'

export function ContadorLlamadas({ salud }: { salud: SaludChat | null }) {
  const restantes = salud?.llamadas_restantes ?? null
  const primerTope = useRef<number | null>(null)
  const anterior = useRef<number | null>(null)
  const valor = useRef<number | null>(null)
  const [numero, setNumero] = useState<number | null>(restantes)
  const [delta, setDelta] = useState<{ n: number; id: number } | null>(null)
  useEffect(() => {
    if (primerTope.current === null && restantes !== null) primerTope.current = restantes
    const previo = anterior.current
    anterior.current = restantes
    const reducir = window.matchMedia('(prefers-reduced-motion: reduce)')
    let frame = 0
    let temporizador: ReturnType<typeof setTimeout> | undefined
    const terminar = () => { cancelAnimationFrame(frame); valor.current = restantes; setNumero(restantes); setDelta(null) }
    if (restantes === null || previo === null || restantes >= previo || reducir.matches) {
      terminar()
    } else {
      const desde = valor.current ?? previo
      const inicio = performance.now()
      setDelta({ n: previo - restantes, id: inicio })
      const paso = (ahora: number) => {
        const t = Math.min(1, (ahora - inicio) / 600)
        const n = Math.round(desde + (restantes - desde) * (1 - Math.pow(1 - t, 3)))
        valor.current = n
        setNumero(n)
        if (t < 1) frame = requestAnimationFrame(paso)
      }
      frame = requestAnimationFrame(paso)
      temporizador = setTimeout(() => setDelta(null), 650)
    }
    reducir.addEventListener('change', terminar)
    return () => { cancelAnimationFrame(frame); clearTimeout(temporizador); reducir.removeEventListener('change', terminar) }
  }, [restantes])

  if (restantes === null || !salud?.ok) return <p className="text-[11px] text-[#68736d]">Consultas: {salud?.ok ? describirMotivo(salud) : 'contador no disponible'}</p>
  const tope = salud.max_llamadas ?? primerTope.current ?? restantes
  const ratio = tope > 0 ? Math.max(0, Math.min(1, restantes / tope)) : 0
  const tono = ratio > .5 ? '#176d59' : ratio >= .2 ? '#947000' : '#bd3434'
  return (
    <div className="relative min-w-32 border border-[#e1e5df] bg-[#f7f8f5] px-2.5 py-1.5" style={{ color: tono }}>
      <span className="sr-only" role="status">{restantes} llamadas restantes</span>
      <div aria-hidden="true" className="flex items-center gap-1.5 text-[11px]">
        <Gauge className="size-3.5" /><strong className="tabular-nums text-sm">{numero ?? restantes}</strong><span>restantes</span>
        {delta ? <span key={delta.id} className="chat-delta absolute right-2 top-0 font-semibold">−{delta.n}</span> : null}
      </div>
      <div role="progressbar" aria-label="Llamadas disponibles" aria-valuenow={restantes} aria-valuemin={0} aria-valuemax={Math.max(restantes, tope)} className="mt-1 h-1 overflow-hidden bg-[#e1e5df]">
        <div className="chat-bar h-full origin-left" style={{ background: tono, transform: 'scaleX(' + ratio + ')' }} />
      </div>
      {salud.modelo_disponible === false ? <p className="mt-1 text-[10px]">{describirMotivo(salud)}</p> : null}
    </div>
  )
}

