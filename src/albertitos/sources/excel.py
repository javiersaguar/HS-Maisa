"""El Excel de Alberto, limpio: sólo Proveedores, Pedidos_2026 y la norma. El resto son avisos."""

from __future__ import annotations

import re
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import openpyxl

from albertitos.core.contracts import MasterSnapshot, Pedido, Proveedor
from albertitos.core.hashing import hash_canonico
from albertitos.formatos import (
    CENT,
    normalizar_iban,
    normalizar_nif,
    normalizar_pedido,
    parse_fecha_es,
    parse_importe_es,
)

HOJAS_DATOS = {"Proveedores", "Pedidos_2026"}
HOJAS_NOTAS = (
    "notas_alberto",
    "pendiente_revisar",
    "Pedidos_2025_OLD",
    "NO_TOCAR",
    "backup_marzo",
    "MACROS_ROTAS",
)


def _txt(v: object) -> str:
    return "" if v is None else str(v).strip()


def cargar_maestro(ruta: Path | str) -> MasterSnapshot:
    with closing(openpyxl.load_workbook(ruta, data_only=True, read_only=True)) as wb:
        avisos: list[str] = []
        proveedores: dict[str, Proveedor] = {}
        pedidos: dict[str, Pedido] = {}

        filas = list(wb["Proveedores"].iter_rows(values_only=True))
        for fila in filas[1:]:
            if not fila or fila[0] is None:
                continue
            pid = _txt(fila[0]).upper()
            m = re.search(r"\d+", _txt(fila[5]))
            p = Proveedor(
                id=pid,
                razon_social=_txt(fila[1]),
                nif=normalizar_nif(_txt(fila[2])),
                iban=normalizar_iban(_txt(fila[3])),
                ciudad=_txt(fila[4]) or None,
                condiciones_dias=int(m.group()) if m else None,
            )
            if str(fila[1]) != _txt(fila[1]):
                avisos.append(
                    f"Proveedores: {pid} tiene espacios sobrantes en la razón social ({fila[1]!r})"
                )
            if pid in proveedores:
                igual = proveedores[pid] == p
                avisos.append(
                    f"Proveedores: {pid} duplicado "
                    + (
                        "(filas idénticas; se ignora la segunda)"
                        if igual
                        else f"CON DATOS DISTINTOS: {proveedores[pid]} vs {p}"
                    )
                )
                continue
            proveedores[pid] = p

        filas = list(wb["Pedidos_2026"].iter_rows(values_only=True))
        for fila in filas[1:]:
            if not fila or fila[0] is None:
                continue
            num = normalizar_pedido(_txt(fila[0]))
            importe = parse_importe_es(fila[3])
            if importe is None:
                avisos.append(f"Pedidos_2026: {num} sin importe legible ({fila[3]!r})")
                continue
            pedido = Pedido(
                pedido=num,
                proveedor_id=_txt(fila[1]).upper(),
                nif=normalizar_nif(_txt(fila[2])),
                importe_total=importe.quantize(CENT),
                estado=_txt(fila[4]).upper(),
                fecha_pedido=parse_fecha_es(_txt(fila[5])),
            )
            if num in pedidos:
                igual = pedidos[num] == pedido
                avisos.append(
                    f"Pedidos_2026: {num} duplicado "
                    + (
                        "(filas idénticas; se ignora la segunda)"
                        if igual
                        else f"CON DATOS DISTINTOS (se conserva la primera): {pedidos[num]} vs {pedido}"
                    )
                )
                continue
            pedidos[num] = pedido
            prov = proveedores.get(pedido.proveedor_id)
            if not pedidos[num].nif:
                avisos.append(
                    f"Pedidos_2026: {num} sin NIF en el Excel ({pedidos[num].proveedor_id} tiene {prov.nif if prov else '?'})"
                )
            elif prov and prov.nif != pedidos[num].nif:
                avisos.append(
                    f"Pedidos_2026: {num} lleva NIF {pedidos[num].nif} pero {prov.id} tiene {prov.nif}"
                )
            if prov is None:
                avisos.append(
                    f"Pedidos_2026: {num} referencia un proveedor que no está en el maestro ({pedidos[num].proveedor_id})"
                )

        for hoja in HOJAS_NOTAS:
            if hoja in wb.sheetnames:
                for fila in wb[hoja].iter_rows(values_only=True):
                    texto = " | ".join(_txt(c) for c in fila if c is not None)
                    if texto:
                        avisos.append(f"{hoja}: {texto}")
        ignoradas = sorted(set(wb.sheetnames) - HOJAS_DATOS - set(HOJAS_NOTAS) - {"Norma_Pagos_v3"})
        if ignoradas:
            avisos.append(f"hojas ignoradas: {ignoradas}")

        version = hash_canonico(
            {
                "p": {k: v.model_dump(mode="json") for k, v in proveedores.items()},
                "o": {k: v.model_dump(mode="json") for k, v in pedidos.items()},
            }
        )[:12]
        return MasterSnapshot(
            version=version,
            origen=str(ruta),
            proveedores=proveedores,
            pedidos=pedidos,
            avisos_calidad=avisos,
            cargado_en=datetime.now(UTC),
        )


def leer_norma(ruta: Path | str, hoja: str = "Norma_Pagos_v3") -> list[str]:
    """Texto literal de la norma, para docs y para comparar con la v4 del sábado."""
    with closing(openpyxl.load_workbook(ruta, data_only=True, read_only=True)) as wb:
        return [_txt(f[0]) for f in wb[hoja].iter_rows(values_only=True) if f and f[0]]
