"""Tesorería sobre el calendario: por semana, por proveedor y un programa de pagos con tope semanal.

Todo sale del `Informe` de `albertitos.bonus` (las decisiones PAGAR vigentes, en sólo lectura): aquí no se
abre la BD ni se decide nada. Importes con Decimal, cuadrando al céntimo con el calendario; los resultados
son dicts listos para JSON (importes como string con 2 decimales, fechas ISO).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal

from albertitos.bonus import Informe, Pago, semana_iso

CERO = Decimal("0.00")
MAX_SEMANAS = 520  # diez años: un tope ridículo no puede colgar la consola


def eur(x: Decimal) -> str:
    return str(x.quantize(Decimal("0.01")))


def lunes(fecha: date) -> date:
    return fecha - timedelta(days=fecha.weekday())


def _suma(pagos: Iterable[Pago]) -> Decimal:
    return sum((p.importe_eur for p in pagos), CERO)


def tesoreria(informe: Informe) -> dict:
    """Lo que se paga cada semana ISO (por vencimiento), lo acumulado y lo vencido a la fecha de corte."""
    semanas: dict[str, list[Pago]] = {}
    for p in sorted(informe.calendario, key=lambda p: (p.vencimiento, p.file_id)):
        semanas.setdefault(p.semana, []).append(p)
    filas, acumulado = [], CERO
    for semana, pagos in semanas.items():
        importe = _suma(pagos)
        acumulado += importe
        vencidos = [p for p in pagos if p.vencido]
        filas.append(
            {
                "semana": semana,
                "desde": lunes(pagos[0].vencimiento).isoformat(),
                "numero": len(pagos),
                "importe_eur": eur(importe),
                "acumulado_eur": eur(acumulado),
                "vencidos_numero": len(vencidos),
                "vencidos_importe_eur": eur(_suma(vencidos)),
                "en_remesa_numero": sum(p.apto_remesa for p in pagos),
            }
        )
    vencidos = [p for p in informe.calendario if p.vencido]
    total = _suma(informe.calendario)
    return {
        "fecha_corte": informe.fecha_corte.isoformat(),
        "semana_corte": semana_iso(informe.fecha_corte),
        "numero": len(informe.calendario),
        "importe_eur": eur(total),
        "vencido_numero": len(vencidos),
        "vencido_importe_eur": eur(_suma(vencidos)),
        "en_plazo_numero": len(informe.calendario) - len(vencidos),
        "en_plazo_importe_eur": eur(total - _suma(vencidos)),
        "semanas": filas,
    }


def proveedores(informe: Informe) -> list[dict]:
    """Una fila por proveedor: cuánto se le paga, cuándo y cuánto está vencido."""
    grupos: dict[str, list[Pago]] = {}
    for p in informe.calendario:
        grupos.setdefault(p.proveedor_id, []).append(p)
    filas = []
    for proveedor_id, pagos in grupos.items():
        vencidos = [p for p in pagos if p.vencido]
        filas.append(
            {
                "proveedor_id": proveedor_id,
                "beneficiario": pagos[0].beneficiario,
                "numero": len(pagos),
                "importe_eur": eur(_suma(pagos)),
                "vencidos_numero": len(vencidos),
                "vencidos_importe_eur": eur(_suma(vencidos)),
                "primera_ejecucion": min(p.fecha_ejecucion for p in pagos).isoformat(),
                "ultima_ejecucion": max(p.fecha_ejecucion for p in pagos).isoformat(),
                "lotes": sorted({p.lote for p in pagos}),
                "iban_control_ok": all(p.iban_control_ok for p in pagos),
                "en_remesa_numero": sum(p.apto_remesa for p in pagos),
            }
        )
    return sorted(filas, key=lambda f: (-Decimal(f["importe_eur"]), f["proveedor_id"]))


def programa(informe: Informe, tope_semanal: Decimal) -> dict:
    """Reparte los pagos preparables (la remesa) en semanas desde la del corte, sin pasar del tope.

    Cada semana se paga, por orden de vencimiento (lo más antiguo primero), lo que ya ha vencido o vence
    esa semana, mientras quepa en el tope; si uno no cabe, se prueba con los siguientes (más pequeños)
    y lo que no cabe se arrastra a la semana siguiente. Un pago que por sí solo supera el
    tope sale solo en su semana, marcado: no se trocea una factura. Dice cuántas semanas hacen falta
    para ponerse al día con lo vencido y para pagarlo todo."""
    if tope_semanal <= 0:
        raise ValueError("el tope semanal tiene que ser positivo")
    cola = sorted(informe.remesa, key=lambda p: (p.vencimiento, p.file_id))
    inicio = lunes(informe.fecha_corte)
    semanas: list[dict] = []
    hay_vencidos = any(p.vencimiento < informe.fecha_corte for p in cola)
    semanas_para_vencidos: int | None = None if hay_vencidos else 0
    for k in range(MAX_SEMANAS):
        if not cola:
            break
        desde = inicio + timedelta(weeks=k)
        hasta = desde + timedelta(days=6)
        pagados, gastado, supera = [], CERO, False
        for p in list(cola):
            if p.vencimiento > hasta:
                break  # la cola va por vencimiento: lo siguiente aún no toca
            if gastado + p.importe_eur <= tope_semanal:
                pagados.append(p)
                gastado += p.importe_eur
            elif not pagados and p.importe_eur > tope_semanal:
                pagados.append(p)  # no cabe nunca: sale solo, y se dice
                gastado += p.importe_eur
                supera = True
                break
        for p in pagados:
            cola.remove(p)
        pendientes_vencidos = [p for p in cola if p.vencimiento < informe.fecha_corte]
        if semanas_para_vencidos is None and not pendientes_vencidos:
            semanas_para_vencidos = k + 1
        semanas.append(
            {
                "semana": semana_iso(desde),
                "desde": desde.isoformat(),
                "numero": len(pagados),
                "importe_eur": eur(gastado),
                "supera_tope": supera,
                "arrastrado_numero": sum(p.vencimiento <= hasta for p in cola),
                "arrastrado_importe_eur": eur(_suma(p for p in cola if p.vencimiento <= hasta)),
            }
        )
    return {
        "tope_semanal_eur": eur(tope_semanal),
        "numero": len(informe.remesa),
        "importe_eur": eur(_suma(informe.remesa)),
        "semanas_para_ponerse_al_dia": semanas_para_vencidos,
        "semanas_para_pagarlo_todo": len(semanas) if not cola else None,
        "sin_programar_numero": len(cola),
        "semanas": [s for s in semanas if s["numero"] or s["arrastrado_numero"]],
    }
