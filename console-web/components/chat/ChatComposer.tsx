'use client'

import { useEffect, useId, useState, type RefObject } from 'react'
import { SendHorizontal } from 'lucide-react'
import { MAX_MENSAJE } from '@/lib/api/chat'

const ATAJOS = ['Factura', 'Pedido', 'Proveedor', 'Semana', 'Confianza'] as const
type Atajo = typeof ATAJOS[number]
function pregunta(tipo: Atajo, valor: string) {
  const v = valor.trim()
  if (!v && tipo !== 'Semana') return ''
  switch (tipo) {
    case 'Factura': return '¿Qué decisión tiene la factura ' + v + ' y por qué?'
    case 'Pedido': return '¿Qué facturas llevan el pedido ' + v + '?'
    case 'Proveedor': return 'Busca las facturas del proveedor ' + v + '.'
    case 'Semana': return v ? '¿Cuánto vence en la semana ' + v + '?' : '¿Cuánto vence esta semana?'
    case 'Confianza': return '¿Qué confianza tiene la clasificación de ' + v + ' y por qué?'
  }
}

export function ChatComposer({ entrada, cambiar, enviar, enviando, campo }: {
  entrada: string; cambiar: (s: string) => void; enviar: (s: string) => void; enviando: boolean
  campo: RefObject<HTMLTextAreaElement | null>
}) {
  const id = useId()
  const [atajo, setAtajo] = useState<Atajo | null>(null)
  const [valor, setValor] = useState('')
  const prevista = atajo ? pregunta(atajo, valor) : ''
  useEffect(() => {
    if (!campo.current) return
    campo.current.style.height = 'auto'
    campo.current.style.height = Math.min(112, campo.current.scrollHeight) + 'px'
  }, [entrada, campo])
  return (
    <div className="border-t border-[#e1e5df] bg-white px-4 py-3">
      <div className="mb-2 flex flex-wrap gap-1" aria-label="Atajos de pregunta">
        {ATAJOS.map(tipo => <button key={tipo} type="button" aria-pressed={atajo === tipo} onClick={() => { setAtajo(atajo === tipo ? null : tipo); setValor('') }} className="rounded-full border border-[#e1e5df] px-2 text-[11px] text-[#164f45] aria-pressed:bg-[#eff8f3]">{tipo}</button>)}
      </div>
      {atajo ? <div className="mb-2 rounded-lg bg-[#f7f8f5] p-2 text-xs">
        <label htmlFor={id + '-atajo'}>{atajo === 'Semana' ? 'Semana ISO (vacío: esta semana)' : 'Identificador de ' + atajo.toLowerCase()}</label>
        <div className="mt-1 flex gap-2">
          <input id={id + '-atajo'} value={valor} onChange={e => setValor(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && prevista) { e.preventDefault(); cambiar(prevista); setAtajo(null); campo.current?.focus() } }} className="min-w-0 flex-1 rounded border border-[#e1e5df] bg-white px-2 py-1" />
          <button type="button" disabled={!prevista} onClick={() => { cambiar(prevista); setAtajo(null); campo.current?.focus() }} className="font-semibold text-[#164f45] disabled:opacity-40">Usar</button>
        </div>
        {prevista ? <p className="mt-2 break-words">Se preguntará: «{prevista}»</p> : null}
      </div> : null}
      <form onSubmit={e => { e.preventDefault(); enviar(entrada) }} className="flex items-end gap-2">
        <label className="sr-only" htmlFor={id}>Tu pregunta a AlbertitosAI</label>
        <textarea id={id} ref={campo} value={entrada} onChange={e => cambiar(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); enviar(entrada) } }} rows={2} placeholder="Pregunta lo que necesitas saber…" className="min-h-14 max-h-28 min-w-0 flex-1 resize-none rounded-xl border border-[#e1e5df] px-3 py-2 text-[13px] leading-6 text-[#17211e]" />
        <button type="submit" disabled={enviando || !entrada.trim() || entrada.trim().length > MAX_MENSAJE} aria-label="Enviar la pregunta" className="chat-press flex size-11 shrink-0 items-center justify-center rounded-xl bg-[#164f45] text-white disabled:opacity-40"><SendHorizontal className="size-4" /></button>
      </form>
      <p className="mt-1 text-[10px] text-[#68736d]">Enter envía · Shift+Enter añade una línea</p>
      {entrada.trim().length > MAX_MENSAJE - 500 ? <p className="text-right text-xs">{entrada.trim().length}/{MAX_MENSAJE}</p> : null}
    </div>
  )
}

