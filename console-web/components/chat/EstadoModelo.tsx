'use client'

import { Archive, CircleAlert, CircleCheck, LoaderCircle, Radio, Unplug } from 'lucide-react'
import { CHAT_URL, describirMotivo, type SaludChat } from '@/lib/api/chat'
import { ETIQUETA_GRABADA, GRABACION } from '@/lib/mock/chat'

/**
 * La línea de estado del chat, SIEMPRE visible: quien mira la pantalla tiene que saber si contesta el modelo en vivo o
 * no. Icono + texto (el color nunca es la única señal).
 */
export function EstadoModelo({ salud, grabado }: { salud: SaludChat | null; grabado: boolean }) {
  if (grabado) {
    return (
      <Linea tono="ambar" icono={<Archive className="size-3.5 shrink-0" aria-hidden="true" />}>
        Modo grabado: {ETIQUETA_GRABADA} ({GRABACION})
      </Linea>
    )
  }
  if (salud === null) {
    return (
      <Linea tono="gris" icono={<LoaderCircle className="size-3.5 shrink-0 animate-spin" aria-hidden="true" />}>
        Comprobando el chat…
      </Linea>
    )
  }
  if (!salud.ok) {
    return (
      <Linea tono="rojo" icono={<Unplug className="size-3.5 shrink-0" aria-hidden="true" />}>
        Sin conexión con el chat ({CHAT_URL.replace(/^https?:\/\//, '')}): arráncalo con make chat
      </Linea>
    )
  }
  const restantes =
    typeof salud.llamadas_restantes === 'number' ? ` · ${salud.llamadas_restantes} llamadas restantes` : ''
  if (salud.modelo_disponible === true) {
    return (
      <Linea tono="verde" icono={<Radio className="size-3.5 shrink-0" aria-hidden="true" />}>
        En vivo · {salud.modelo ?? 'modelo'}
        {restantes}
      </Linea>
    )
  }
  if (salud.modelo_disponible === false) {
    return (
      <Linea tono="ambar" icono={<CircleAlert className="size-3.5 shrink-0" aria-hidden="true" />}>
        Sin modelo: {describirMotivo(salud)}
        {restantes}
      </Linea>
    )
  }
  return (
    <Linea tono="gris" icono={<CircleCheck className="size-3.5 shrink-0" aria-hidden="true" />}>
      Chat conectado · disponibilidad del modelo desconocida (servidor anterior al contrato v2)
    </Linea>
  )
}

const TONOS = {
  verde: 'border-[#dcefe6] bg-[#eff8f3] text-[#176d59]',
  ambar: 'border-[#eee8bd] bg-[#fffbe8] text-[#8a7400]',
  rojo: 'border-[#f1dada] bg-[#fff0f0] text-[#bd3434]',
  gris: 'border-[#e1e7e2] bg-[#f7f8f5] text-[#68736d]',
} as const

function Linea({
  tono,
  icono,
  children,
}: {
  tono: keyof typeof TONOS
  icono: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <p
      role="status"
      aria-live="polite"
      className={`flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-[12px] font-medium ${TONOS[tono]}`}
    >
      {icono}
      <span>{children}</span>
    </p>
  )
}
