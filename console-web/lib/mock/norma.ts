/**
 * Réplica de `src/albertitos/rules/norma_v3.py` SOLO para generar el mock.
 *
 * El mock hace de backend: sus decisiones tienen que salir de la norma y no de un número puesto a mano,
 * o la demo enseñaría motivos que no cuadran con los hechos. La UI nunca importa este fichero:
 * en la consola real la decisión viene hecha de la BD.
 */

import type { Aviso, Decision, ErpEntry, InvoiceFacts, Motivo, Pedido, Proveedor, Resultado } from '../types'

export const NORMA_VERSION = 'v3'

const ANOMALIAS_HUMANO: Aviso[] = [
  'texto_instruccion',
  'duplicado_sospechoso',
  'pedido_anulado_segun_pdf',
  'discrepancia_extractores',
  'extraccion_parcial',
  'nif_invalido',
  'importe_ambiguo',
]

export interface Contexto {
  norma_version: string
  fecha_corte: string
  maestro_version: string
  erp_version: string
  proveedores: Proveedor[]
  pedidos: Map<string, Pedido>
  asientosPorPedido: Map<string, ErpEntry[]>
}

const CENT = 0.01
const eur = (value: number) => value.toFixed(2)
const differs = (a: number, b: number) => Math.abs(a - b) > CENT + 1e-9
const ok = (regla: string, detalle: string, evidencia: Record<string, unknown> = {}): Motivo => ({
  regla_id: `${NORMA_VERSION}.${regla}`,
  ok: true,
  detalle,
  evidencia,
})
const ko = (regla: string, detalle: string, evidencia: Record<string, unknown> = {}): Motivo => ({
  regla_id: `${NORMA_VERSION}.${regla}`,
  ok: false,
  detalle,
  evidencia,
})

const cleanNif = (nif: string) => nif.replace(/[\s-]/g, '').toUpperCase()

export function proveedorPorNif(ctx: Contexto, nif: string | null): Proveedor | null {
  if (!nif) return null
  return ctx.proveedores.find((p) => cleanNif(p.nif) === cleanNif(nif)) ?? null
}

function r1(h: InvoiceFacts, ctx: Contexto): Motivo {
  if (!h.nif_emisor) return ko('R1', 'la factura no tiene NIF legible')
  const p = proveedorPorNif(ctx, h.nif_emisor)
  if (!p) return ko('R1', `el NIF ${h.nif_emisor} no está en el maestro de proveedores`, { nif: h.nif_emisor })
  if (!h.iban) return ko('R1', `la factura de ${p.id} no tiene IBAN legible`, { proveedor: p.id })
  if (h.iban !== p.iban)
    return ko('R1', `el IBAN de la factura no coincide con el del maestro para ${p.id}`, {
      proveedor: p.id,
      iban_factura: h.iban,
      iban_maestro: p.iban,
    })
  return ok('R1', `NIF y IBAN coinciden con ${p.id} (${p.razon_social})`, { proveedor: p.id })
}

function r2(h: InvoiceFacts, ctx: Contexto): Motivo {
  if (!h.pedido) return ko('R2', 'la factura no referencia ningún pedido')
  const pedido = ctx.pedidos.get(h.pedido)
  if (!pedido) return ko('R2', `el pedido ${h.pedido} no existe en el maestro`, { pedido: h.pedido })
  if (h.nif_emisor && pedido.nif !== h.nif_emisor)
    return ko(
      'R2',
      `el pedido ${h.pedido} pertenece a ${pedido.proveedor_id} (${pedido.nif}), no al emisor ${h.nif_emisor}`,
      { pedido: h.pedido, nif_pedido: pedido.nif, nif_factura: h.nif_emisor },
    )
  if (h.total === null) return ko('R2', 'la factura no tiene total legible', { pedido: h.pedido })
  if (differs(h.total, pedido.importe_total))
    return ko(
      'R2',
      `el total de la factura (${eur(h.total)}) no coincide con el pedido ${h.pedido} (${eur(pedido.importe_total)})`,
      { pedido: h.pedido, total_factura: eur(h.total), importe_pedido: eur(pedido.importe_total) },
    )
  return ok('R2', `pedido ${h.pedido} existe, es del proveedor y el importe coincide`, {
    pedido: h.pedido,
    importe: eur(pedido.importe_total),
  })
}

function r3(h: InvoiceFacts): Motivo {
  if (h.base === null || h.iva === null || h.total === null)
    return ko('R3', 'faltan base, IVA o total para comprobar el cálculo', {
      base: String(h.base),
      iva: String(h.iva),
      total: String(h.total),
    })
  if (differs(h.base + h.iva, h.total))
    return ko('R3', `base + IVA (${eur(h.base)} + ${eur(h.iva)}) no es el total (${eur(h.total)})`, {
      base: eur(h.base),
      iva: eur(h.iva),
      total: eur(h.total),
    })
  const esperado = Math.round(h.base * 21) / 100
  if (differs(h.iva, esperado))
    return ko(
      'R3',
      `el IVA (${eur(h.iva)}) no es el 21 % de la base (${eur(esperado)}); IVA reducido sin confirmar`,
      { iva: eur(h.iva), esperado: eur(esperado), iva_pct: String(h.iva_pct) },
    )
  return ok('R3', 'IVA al 21 % y total = base + IVA', { base: eur(h.base), iva: eur(h.iva), total: eur(h.total) })
}

function r4(h: InvoiceFacts, ctx: Contexto): Motivo {
  if (!h.fecha) return ko('R4', 'la fecha de la factura no es válida o no se ha podido leer')
  if (h.fecha > ctx.fecha_corte)
    return ko('R4', `la fecha ${h.fecha} es posterior a la fecha de corte ${ctx.fecha_corte}`, {
      fecha: h.fecha,
      fecha_corte: ctx.fecha_corte,
    })
  return ok('R4', `fecha ${h.fecha} válida y no futura`, { fecha: h.fecha, fecha_corte: ctx.fecha_corte })
}

function r5(h: InvoiceFacts, ctx: Contexto): Motivo {
  if (!h.pedido) return ko('R5', 'sin pedido no se puede cruzar con el ERP')
  const asientos = ctx.asientosPorPedido.get(h.pedido) ?? []
  if (!asientos.length)
    return ko('R5', `el pedido ${h.pedido} no tiene asiento en el ERP`, {
      pedido: h.pedido,
      erp_version: ctx.erp_version,
    })
  const pagado = asientos.find((a) => a.estado === 'PAGADA')
  if (pagado)
    return ko(
      'R5',
      `el pedido ${h.pedido} ya figura PAGADA en el ERP (asiento ${pagado.asiento_id}): no pagar dos veces`,
      { pedido: h.pedido, asiento: pagado.asiento_id, no_pagar: true },
    )
  const a = asientos[0]
  if (h.total !== null && differs(a.importe_esperado, h.total))
    return ko('R5', `el ERP espera ${eur(a.importe_esperado)} para ${h.pedido} y la factura dice ${eur(h.total)}`, {
      asiento: a.asiento_id,
      importe_erp: eur(a.importe_esperado),
      total_factura: eur(h.total),
    })
  if (h.nif_emisor && a.nif !== h.nif_emisor)
    return ko('R5', `el asiento ${a.asiento_id} es de ${a.nif}, no del emisor ${h.nif_emisor}`, {
      asiento: a.asiento_id,
      nif_erp: a.nif,
      nif_factura: h.nif_emisor,
    })
  return ok('R5', `asiento ${a.asiento_id} PENDIENTE con el importe esperado`, {
    asiento: a.asiento_id,
    importe_erp: eur(a.importe_esperado),
  })
}

function r6(h: InvoiceFacts): Motivo {
  const graves = h.avisos.filter((aviso) => ANOMALIAS_HUMANO.includes(aviso))
  if (graves.length) {
    let detalle = `anomalía que debe ver una persona: ${graves.join(', ')}`
    if (h.texto_sospechoso) detalle += ` · el documento dice: "${h.texto_sospechoso.slice(0, 300)}"`
    return ko('R6', detalle, { avisos: graves, texto_sospechoso: h.texto_sospechoso })
  }
  return ok('R6', 'sin anomalías que requieran revisión humana', { avisos: h.avisos })
}

export function decidir(h: InvoiceFacts, ctx: Contexto, hechosHash: string, decididoEn: string): Decision {
  const motivos = [r1(h, ctx), r2(h, ctx), r3(h), r4(h, ctx), r5(h, ctx), r6(h)]
  const fallos = motivos.filter((motivo) => !motivo.ok)
  const resultado: Resultado = !fallos.length
    ? 'PAGAR'
    : fallos.some((motivo) => motivo.evidencia.no_pagar)
      ? 'NO_PAGAR'
      : 'ESCALAR'
  return {
    file_id: h.file_id,
    sha256: h.sha256,
    resultado,
    motivos,
    norma_version: ctx.norma_version,
    fecha_corte: ctx.fecha_corte,
    hechos_hash: hechosHash,
    maestro_version: ctx.maestro_version,
    erp_version: ctx.erp_version,
    decidido_en: decididoEn,
  }
}
