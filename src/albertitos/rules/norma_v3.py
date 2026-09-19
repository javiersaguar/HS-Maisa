"""NORMA DE PAGOS A PROVEEDORES (v3, vigente) — hoja Norma_Pagos_v3 del Excel, regla a regla.

1. Pagar solo si el NIF está en el maestro y el IBAN de la factura coincide con el maestro.
2. El pedido debe existir, pertenecer al proveedor y el importe de la factura debe ser igual al del pedido (±0,01).
3. El IVA debe estar bien calculado y el total debe ser base + IVA (±0,01).
4. La fecha debe ser válida y no futura.
5. Estado ERP del pedido: PENDIENTE. Nunca pagar dos veces el mismo pedido.
6. Cualquier anomalía que un humano deba ver: ESCALAR con motivo. Ante duda razonable, escalar antes que pagar.

Primera pasada (plataforma). Mónica la valida contra data/fixtures/esperado_muestra.csv y docs/trampas.md.
Hipótesis de frontera (pendiente de mentor): NO_PAGAR sólo cuando la violación es objetiva y comprobada en
el ERP (pedido ya PAGADA); todo lo demás que falla es ESCALAR.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from albertitos.core.contracts import (
    Aviso,
    ContextoDecision,
    Decision,
    ErpSnapshot,
    InvoiceFacts,
    MasterSnapshot,
    Motivo,
    Resultado,
)
from albertitos.formatos import CENT

VERSION = "v3"
IVA_GENERAL = Decimal("21")
# Una lectura por debajo de esto se reconcilió con el maestro en vez de leerse limpia: la ve una persona.
CONFIANZA_MINIMA = 1.0
ANOMALIAS_HUMANO = {
    Aviso.TEXTO_INSTRUCCION,
    Aviso.DUPLICADO_SOSPECHOSO,
    Aviso.PEDIDO_ANULADO_SEGUN_PDF,
    Aviso.DISCREPANCIA_EXTRACTORES,
    Aviso.EXTRACCION_PARCIAL,
    Aviso.NIF_INVALIDO,  # NIF con forma imposible: hoy 0 facturas, pero el lote 2 puede traerlos
    Aviso.DOCUMENTO_SUPERPUESTO,  # otro proveedor asomando en el documento: lo mira una persona
    Aviso.IMPORTE_AMBIGUO,
    # lote 2 (ADR-0020): algo escrito o tachado a mano no está en los campos; e18 corrige el total a mano y lo
    # impreso cuadra con el ERP. En el lote 1 no salta en ninguna factura: no cambia ninguna decisión.
    Aviso.ANOTACION_A_MANO,
}


def _ok(regla: str, detalle: str, **ev) -> Motivo:
    return Motivo(regla_id=f"{VERSION}.{regla}", ok=True, detalle=detalle, evidencia=ev)


def _ko(regla: str, detalle: str, **ev) -> Motivo:
    return Motivo(regla_id=f"{VERSION}.{regla}", ok=False, detalle=detalle, evidencia=ev)


def regla_1_proveedor(
    h: InvoiceFacts, maestro: MasterSnapshot, erp: ErpSnapshot, ctx: ContextoDecision
) -> Motivo:
    if not h.nif_emisor:
        return _ko("R1", "la factura no tiene NIF legible")
    p = maestro.proveedor_por_nif(h.nif_emisor)
    if p is None:
        return _ko(
            "R1", f"el NIF {h.nif_emisor} no está en el maestro de proveedores", nif=h.nif_emisor
        )
    if not h.iban:
        return _ko("R1", f"la factura de {p.id} no tiene IBAN legible", proveedor=p.id)
    if h.iban != p.iban:
        return _ko(
            "R1",
            f"el IBAN de la factura no coincide con el del maestro para {p.id}",
            proveedor=p.id,
            iban_factura=h.iban,
            iban_maestro=p.iban,
        )
    return _ok("R1", f"NIF y IBAN coinciden con {p.id} ({p.razon_social})", proveedor=p.id)


def regla_2_pedido(
    h: InvoiceFacts, maestro: MasterSnapshot, erp: ErpSnapshot, ctx: ContextoDecision
) -> Motivo:
    if not h.pedido:
        return _ko("R2", "la factura no referencia ningún pedido")
    pedido = maestro.pedidos.get(h.pedido)
    if pedido is None:
        return _ko("R2", f"el pedido {h.pedido} no existe en el maestro", pedido=h.pedido)
    if h.nif_emisor and pedido.nif != h.nif_emisor:
        return _ko(
            "R2",
            f"el pedido {h.pedido} pertenece a {pedido.proveedor_id} ({pedido.nif}), no al emisor {h.nif_emisor}",
            pedido=h.pedido,
            nif_pedido=pedido.nif,
            nif_factura=h.nif_emisor,
        )
    if h.total is None:
        return _ko("R2", "la factura no tiene total legible", pedido=h.pedido)
    if abs(h.total - pedido.importe_total) > CENT:
        return _ko(
            "R2",
            f"el total de la factura ({h.total}) no coincide con el pedido {h.pedido} ({pedido.importe_total})",
            pedido=h.pedido,
            total_factura=str(h.total),
            importe_pedido=str(pedido.importe_total),
        )
    return _ok(
        "R2",
        f"pedido {h.pedido} existe, es del proveedor y el importe coincide",
        pedido=h.pedido,
        importe=str(pedido.importe_total),
    )


def regla_3_iva(
    h: InvoiceFacts, maestro: MasterSnapshot, erp: ErpSnapshot, ctx: ContextoDecision
) -> Motivo:
    if h.base is None or h.iva is None or h.total is None:
        return _ko(
            "R3",
            "faltan base, IVA o total para comprobar el cálculo",
            base=str(h.base),
            iva=str(h.iva),
            total=str(h.total),
        )
    if abs(h.base + h.iva - h.total) > CENT:
        return _ko(
            "R3",
            f"base + IVA ({h.base} + {h.iva}) no es el total ({h.total})",
            base=str(h.base),
            iva=str(h.iva),
            total=str(h.total),
        )
    esperado = (h.base * IVA_GENERAL / 100).quantize(CENT)
    if abs(h.iva - esperado) > CENT:
        return _ko(
            "R3",
            f"el IVA ({h.iva}) no es el 21 % de la base ({esperado}); IVA reducido sin confirmar",
            iva=str(h.iva),
            esperado=str(esperado),
            iva_pct=str(h.iva_pct),
        )
    return _ok(
        "R3",
        "IVA al 21 % y total = base + IVA",
        base=str(h.base),
        iva=str(h.iva),
        total=str(h.total),
    )


def regla_4_fecha(
    h: InvoiceFacts, maestro: MasterSnapshot, erp: ErpSnapshot, ctx: ContextoDecision
) -> Motivo:
    if h.fecha is None:
        return _ko("R4", "la fecha de la factura no es válida o no se ha podido leer")
    if h.fecha > ctx.fecha_corte:
        return _ko(
            "R4",
            f"la fecha {h.fecha} es posterior a la fecha de corte {ctx.fecha_corte}",
            fecha=str(h.fecha),
            fecha_corte=str(ctx.fecha_corte),
        )
    return _ok(
        "R4",
        f"fecha {h.fecha} válida y no futura",
        fecha=str(h.fecha),
        fecha_corte=str(ctx.fecha_corte),
    )


def regla_5_erp(
    h: InvoiceFacts, maestro: MasterSnapshot, erp: ErpSnapshot, ctx: ContextoDecision
) -> Motivo:
    if not h.pedido:
        return _ko("R5", "sin pedido no se puede cruzar con el ERP")
    asientos = erp.por_pedido().get(h.pedido, [])
    if not asientos:
        return _ko(
            "R5",
            f"el pedido {h.pedido} no tiene asiento en el ERP",
            pedido=h.pedido,
            erp_version=erp.version,
        )
    pagados = [a for a in asientos if a.estado == "PAGADA"]
    if pagados:
        return _ko(
            "R5",
            f"el pedido {h.pedido} ya figura PAGADA en el ERP (asiento {pagados[0].asiento_id}): no pagar dos veces",
            pedido=h.pedido,
            asiento=pagados[0].asiento_id,
            no_pagar=True,
        )
    a = asientos[0]
    if a.estado != "PENDIENTE":
        return _ko(
            "R5",
            f"el asiento {a.asiento_id} está en estado {a.estado}, no PENDIENTE",
            asiento=a.asiento_id,
            estado=a.estado,
        )
    if h.total is not None and abs(a.importe_esperado - h.total) > CENT:
        return _ko(
            "R5",
            f"el ERP espera {a.importe_esperado} para {h.pedido} y la factura dice {h.total}",
            asiento=a.asiento_id,
            importe_erp=str(a.importe_esperado),
            total_factura=str(h.total),
        )
    if h.nif_emisor and a.nif != h.nif_emisor:
        return _ko(
            "R5",
            f"el asiento {a.asiento_id} es de {a.nif}, no del emisor {h.nif_emisor}",
            asiento=a.asiento_id,
            nif_erp=a.nif,
            nif_factura=h.nif_emisor,
        )
    return _ok(
        "R5",
        f"asiento {a.asiento_id} PENDIENTE con el importe esperado",
        asiento=a.asiento_id,
        importe_erp=str(a.importe_esperado),
    )


def regla_6_anomalias(
    h: InvoiceFacts, maestro: MasterSnapshot, erp: ErpSnapshot, ctx: ContextoDecision
) -> Motivo:
    graves = [a for a in h.avisos if a in ANOMALIAS_HUMANO]
    lectura_floja = h.confianza is not None and h.confianza < CONFIANZA_MINIMA
    if graves or lectura_floja:
        partes = []
        if graves:
            partes.append(
                "anomalía que debe ver una persona: " + ", ".join(a.value for a in graves)
            )
        if lectura_floja:
            partes.append(
                f"la lectura del documento no es firme (confianza {h.confianza}): se eligió "
                "reconciliándola con el maestro, no se leyó limpia"
            )
        detalle = " · ".join(partes)
        if h.texto_sospechoso:
            detalle += f' · el documento dice: "{h.texto_sospechoso[:300]}"'  # el tramo entero: a 120 se cortaba la orden
        evidencia = {"avisos": [a.value for a in graves], "texto_sospechoso": h.texto_sospechoso}
        if lectura_floja:
            evidencia["confianza"] = h.confianza
        return _ko("R6", detalle, **evidencia)
    return _ok(
        "R6", "sin anomalías que requieran revisión humana", avisos=[a.value for a in h.avisos]
    )


REGLAS = [
    regla_1_proveedor,
    regla_2_pedido,
    regla_3_iva,
    regla_4_fecha,
    regla_5_erp,
    regla_6_anomalias,
]


def decidir(
    h: InvoiceFacts, maestro: MasterSnapshot, erp: ErpSnapshot, ctx: ContextoDecision
) -> Decision:
    motivos = [regla(h, maestro, erp, ctx) for regla in REGLAS]
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
        decidido_en=datetime.now(UTC),
    )
