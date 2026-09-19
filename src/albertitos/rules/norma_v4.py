"""NORMA DE PAGOS v4 = la v3 + la regla nueva del lote 2 (sábado 19/09). Dueño: Miguel (M3); la revisa Mónica.

A las 21:00 la regla nueva no está publicada. Esta v4 lleva la hipótesis de divisas (`docs/agentes/lote2/HIPOTESIS.md`:
8 facturas en USD, GBP, CHF, BRL, MXN o JPY contra pedidos en EUR, con un tipo implícito fijo por moneda) detrás de
su propia regla, R7, para poder cambiarla sin tocar las demás cuando llegue el texto literal (ADR-0022):

7. Moneda. Una factura en EUR, o sin moneda (las plantillas de la Caja son en euros), no cambia nada. En otra moneda:
   si `TIPOS_CAMBIO` trae su tipo, R2 y R5 comparan el importe convertido a EUR con el pedido y con el ERP; si no lo
   trae, la factura escala con ese motivo: la conversión la valida una persona (regla 6: ante la duda, escalar).

Las reglas 1-6 son las de la v3, la misma implementación, con el identificador `v4.Rn`. `decidido_en` lo sella
`core.db` al guardar: aquí no se mira el reloj.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from albertitos.core.contracts import (
    ContextoDecision,
    Decision,
    ErpSnapshot,
    InvoiceFacts,
    MasterSnapshot,
    Motivo,
    Resultado,
)
from albertitos.formatos import CENT
from albertitos.rules import norma_v3

VERSION = "v4"
MONEDA_BASE = "EUR"
# EUR por unidad de moneda. Vacía hasta que la regla nueva diga cuáles valen: sin tipo, la factura escala. Los tipos
# implícitos del lote 2 (pedido en EUR / total en divisa) son USD 0,92 · GBP 1,17 · CHF 1,05 · BRL 0,1613 ·
# MXN 0,0469 · JPY 0,00617: si la regla los da, van aquí (y `reprocess --todo --lote 2 --norma v4`).
TIPOS_CAMBIO: dict[str, Decimal] = {}
# Al convertir, el redondeo del tipo mueve céntimos (15.500 BRL × 0,1613 = 2.500,15 frente a 2.500,00 del pedido):
# tolerancia relativa al importe, además de la de la casa (0,01).
TOLERANCIA_CONVERSION = Decimal("0.001")


def _en_otra_moneda(h: InvoiceFacts) -> bool:
    return h.moneda is not None and h.moneda != MONEDA_BASE


def _convertida(h: InvoiceFacts, tipo: Decimal) -> InvoiceFacts:
    """Los hechos con los importes en EUR, para comparar con el pedido y el ERP. Sólo para decidir: no se guardan."""

    def eur(x: Decimal | None) -> Decimal | None:
        return None if x is None else (x * tipo).quantize(CENT, rounding=ROUND_HALF_UP)

    return h.model_copy(
        update={
            "base": eur(h.base),
            "iva": eur(h.iva),
            "total": eur(h.total),
            "moneda": MONEDA_BASE,
        }
    )


def regla_7_moneda(
    h: InvoiceFacts, maestro: MasterSnapshot, erp: ErpSnapshot, ctx: ContextoDecision
) -> Motivo:
    if not _en_otra_moneda(h):
        return Motivo(
            regla_id=f"{VERSION}.R7",
            ok=True,
            detalle=f"importes en {h.moneda or MONEDA_BASE}",
            evidencia={"moneda": h.moneda},
        )
    tipo = TIPOS_CAMBIO.get(h.moneda or "")
    if tipo is None:
        pedido = maestro.pedidos.get(h.pedido or "")
        evidencia: dict[str, str | None] = {"moneda": h.moneda, "total": str(h.total)}
        implicito = ""
        if pedido is not None and h.total:
            evidencia["importe_pedido_eur"] = str(pedido.importe_total)
            evidencia["tipo_implicito"] = str(
                (pedido.importe_total / h.total).quantize(Decimal("0.00001"))
            )
            implicito = f" (el pedido {h.pedido} está en EUR: {pedido.importe_total})"
        return Motivo(
            regla_id=f"{VERSION}.R7",
            ok=False,
            detalle=f"factura en {h.moneda}{implicito}; sin tipo de cambio acordado, "
            "la conversión la valida una persona",
            evidencia=evidencia,
        )
    return Motivo(
        regla_id=f"{VERSION}.R7",
        ok=True,
        detalle=f"factura en {h.moneda}: se compara convertida a EUR al tipo {tipo}",
        evidencia={
            "moneda": h.moneda,
            "tipo": str(tipo),
            "total_eur": str(_convertida(h, tipo).total),
        },
    )


def _tolerante(m: Motivo, h: InvoiceFacts, total_eur: Decimal | None, referencia: str) -> Motivo:
    """R2 y R5 sobre el importe convertido admiten el redondeo del tipo (TOLERANCIA_CONVERSION): sólo cuando lo
    único que falla es el importe (su evidencia trae el de la factura y el de referencia, del pedido o del ERP)."""
    esperado = m.evidencia.get(referencia)
    if m.ok or total_eur is None or esperado is None or "total_factura" not in m.evidencia:
        return m
    esperado = Decimal(esperado)
    if abs(total_eur - esperado) <= esperado * TOLERANCIA_CONVERSION:
        return Motivo(
            regla_id=m.regla_id,
            ok=True,
            detalle=f"{h.total} {h.moneda} son {total_eur} EUR frente a {esperado}: "
            "dentro del redondeo del tipo",
            evidencia={**m.evidencia, "moneda": h.moneda},
        )
    return m


def decidir(
    h: InvoiceFacts, maestro: MasterSnapshot, erp: ErpSnapshot, ctx: ContextoDecision
) -> Decision:
    tipo = TIPOS_CAMBIO.get(h.moneda or "") if _en_otra_moneda(h) else None
    h_eur = _convertida(h, tipo) if tipo is not None else h
    r2 = norma_v3.regla_2_pedido(h_eur, maestro, erp, ctx)
    r5 = norma_v3.regla_5_erp(h_eur, maestro, erp, ctx)
    if tipo is not None:
        r2 = _tolerante(r2, h, h_eur.total, "importe_pedido")
        r5 = _tolerante(r5, h, h_eur.total, "importe_erp")
    # R7 va antes que R2: si la factura viene en divisa, ése es el motivo principal
    motivos = [
        norma_v3.regla_1_proveedor(h, maestro, erp, ctx),
        regla_7_moneda(h, maestro, erp, ctx),
        r2,
        norma_v3.regla_3_iva(h, maestro, erp, ctx),
        norma_v3.regla_4_fecha(h, maestro, erp, ctx),
        r5,
        norma_v3.regla_6_anomalias(h, maestro, erp, ctx),
    ]
    motivos = [
        m.model_copy(update={"regla_id": m.regla_id.replace("v3.", f"{VERSION}.", 1)})
        for m in motivos
    ]
    fallos = [m for m in motivos if not m.ok]
    if not fallos:
        resultado = Resultado.PAGAR
    elif any(m.evidencia.get("no_pagar") for m in fallos):
        resultado = Resultado.NO_PAGAR
    else:
        resultado = Resultado.ESCALAR
    return Decision(
        file_id=h.file_id,
        sha256=h.sha256,
        resultado=resultado,
        motivos=motivos,
        norma_version=ctx.norma_version,
        fecha_corte=ctx.fecha_corte,
        hechos_hash=h.hash(),
        maestro_version=ctx.maestro_version,
        erp_version=ctx.erp_version,
    )
