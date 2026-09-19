"""El maestro del lote 2: el Excel de siempre más `proveedores_nuevos.csv` y `pedidos_nuevos.csv`.

El lote 2 (19/09) trae 4 proveedores extranjeros (P012-P015) y 39 pedidos nuevos en CSV, no en el Excel. Sin ellos,
las facturas que los usan quedarían con el NIF o el pedido «fuera del maestro». Aquí se suman al maestro del Excel y
sale otra versión, versionada por contenido igual que `excel.cargar_maestro`, para que el linaje sepa qué cambia.

Las columnas se leen por nombre, con los mismos alias que el Excel. Lo que ya estaba en el Excel **no se pisa**: si un
CSV trae un proveedor o pedido que ya existe con otros datos, se conserva el del Excel y se avisa. Los datos raros
(IBAN que no pasa el control, pedido de un proveedor que no existe, NIF distinto del proveedor) van a
`avisos_calidad`, con una frase que se pueda leer en voz alta: decide la norma, no el loader.
"""

from __future__ import annotations

import csv
import re
from datetime import UTC, datetime
from pathlib import Path

from albertitos.core.contracts import MasterSnapshot, Pedido, Proveedor
from albertitos.core.hashing import hash_canonico
from albertitos.formatos import (
    CENT,
    iban_valido,
    normalizar_iban,
    normalizar_nif,
    normalizar_pedido,
    parse_fecha_es,
    parse_importe_es,
)
from albertitos.sources import excel
from albertitos.sources.excel import ALIAS_PEDIDO, ALIAS_PROVEEDOR, ErrorMaestro, _txt

PROVEEDORES_CSV = "proveedores_nuevos.csv"
PEDIDOS_CSV = "pedidos_nuevos.csv"


def _filas(ruta: Path) -> list[tuple[str, ...]]:
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return [tuple(fila) for fila in csv.reader(f)]


def _cabecera(ruta: Path, alias: dict, hoja: str, avisos: list[str]):
    filas = _filas(ruta)
    if not filas:
        raise ErrorMaestro(f"{ruta.name}: está vacío")
    idx, cols = excel._cabecera(filas, alias, hoja, avisos)
    return excel._datos(filas, idx), cols


def leer_proveedores(ruta: Path, avisos: list[str]) -> dict[str, Proveedor]:
    """Proveedores de un CSV con las cabeceras del Excel (ID, Razon Social, NIF, IBAN, Ciudad, Condiciones)."""
    datos, cols = _cabecera(ruta, ALIAS_PROVEEDOR, ruta.name, avisos)
    out: dict[str, Proveedor] = {}
    for n, fila in datos:
        pid = _txt(excel._celda(fila, cols, "id")).upper()
        if not pid:
            avisos.append(f"{ruta.name}: fila {n} sin ID, se ignora")
            continue
        m = re.search(r"\d+", _txt(excel._celda(fila, cols, "condiciones_dias")))
        p = Proveedor(
            id=pid,
            razon_social=_txt(excel._celda(fila, cols, "razon_social")),
            nif=normalizar_nif(_txt(excel._celda(fila, cols, "nif"))),
            iban=normalizar_iban(_txt(excel._celda(fila, cols, "iban"))),
            ciudad=_txt(excel._celda(fila, cols, "ciudad")) or None,
            condiciones_dias=int(m.group()) if m else None,
        )
        if pid in out:
            avisos.append(f"{ruta.name}: {pid} duplicado, se conserva la primera fila")
            continue
        out[pid] = p
    return out


def leer_pedidos(ruta: Path, avisos: list[str]) -> dict[str, Pedido]:
    """Pedidos de un CSV con las cabeceras del Excel (pedido, proveedor_id, nif, importe_total, estado, fecha)."""
    datos, cols = _cabecera(ruta, ALIAS_PEDIDO, ruta.name, avisos)
    out: dict[str, Pedido] = {}
    for n, fila in datos:
        num = normalizar_pedido(_txt(excel._celda(fila, cols, "pedido")))
        if not num:
            avisos.append(f"{ruta.name}: fila {n} sin número de pedido, se ignora")
            continue
        crudo = excel._celda(fila, cols, "importe_total")
        importe = parse_importe_es(crudo)
        if importe is None:
            avisos.append(f"{ruta.name}: {num} sin importe legible ({crudo!r}), se ignora")
            continue
        pedido = Pedido(
            pedido=num,
            proveedor_id=_txt(excel._celda(fila, cols, "proveedor_id")).upper(),
            nif=normalizar_nif(_txt(excel._celda(fila, cols, "nif"))),
            importe_total=importe.quantize(CENT),
            estado=_txt(excel._celda(fila, cols, "estado")).upper(),
            fecha_pedido=parse_fecha_es(_txt(excel._celda(fila, cols, "fecha_pedido"))),
        )
        if num in out:
            avisos.append(f"{ruta.name}: {num} duplicado, se conserva la primera fila")
            continue
        out[num] = pedido
    return out


def _version(proveedores: dict[str, Proveedor], pedidos: dict[str, Pedido]) -> str:
    # La misma fórmula que excel.cargar_maestro: mismo contenido, misma versión.
    return hash_canonico(
        {
            "p": {k: v.model_dump(mode="json") for k, v in proveedores.items()},
            "o": {k: v.model_dump(mode="json") for k, v in pedidos.items()},
        }
    )[:12]


def ampliar_maestro(
    base: MasterSnapshot, proveedores_csv: Path | None, pedidos_csv: Path | None
) -> MasterSnapshot:
    """El maestro `base` más los CSV del lote 2. Lo del Excel manda: nada se pisa en silencio."""
    avisos = list(base.avisos_calidad)
    proveedores = dict(base.proveedores)
    pedidos = dict(base.pedidos)
    origenes = [base.origen]

    if proveedores_csv is not None:
        origenes.append(str(proveedores_csv))
        nuevos = leer_proveedores(proveedores_csv, avisos)
        for pid, p in nuevos.items():
            if pid in proveedores:
                if proveedores[pid] != p:
                    avisos.append(
                        f"lote 2: {pid} ya está en el Excel CON DATOS DISTINTOS en {proveedores_csv.name}; "
                        f"se conserva el del Excel ({proveedores[pid]} vs {p})"
                    )
                continue
            proveedores[pid] = p
            if not iban_valido(p.iban):
                avisos.append(
                    f"lote 2: el IBAN de {pid} ({p.razon_social}, {p.iban}) no pasa el control del IBAN"
                    + (" (Japón no usa IBAN)" if p.iban.startswith("JP") else "")
                )
        avisos.append(f"lote 2: {len(nuevos)} proveedores en {proveedores_csv.name}")

    if pedidos_csv is not None:
        origenes.append(str(pedidos_csv))
        nuevos_ped = leer_pedidos(pedidos_csv, avisos)
        for num, ped in nuevos_ped.items():
            if num in pedidos:
                if pedidos[num] != ped:
                    avisos.append(
                        f"lote 2: {num} ya está en el Excel CON DATOS DISTINTOS en {pedidos_csv.name}; "
                        f"se conserva el del Excel ({pedidos[num]} vs {ped})"
                    )
                continue
            pedidos[num] = ped
            prov = proveedores.get(ped.proveedor_id)
            if prov is None:
                avisos.append(
                    f"lote 2: {num} referencia un proveedor que no está en el maestro ({ped.proveedor_id})"
                )
            elif ped.nif and prov.nif != ped.nif:
                avisos.append(f"lote 2: {num} lleva NIF {ped.nif} pero {prov.id} tiene {prov.nif}")
        avisos.append(f"lote 2: {len(nuevos_ped)} pedidos en {pedidos_csv.name}")

    return MasterSnapshot(
        version=_version(proveedores, pedidos),
        origen=" + ".join(origenes),
        proveedores=proveedores,
        pedidos=pedidos,
        avisos_calidad=avisos,
        cargado_en=datetime.now(UTC),
    )


def cargar_maestro_lote2(xlsx: Path | str, dir_lote2: Path | str) -> MasterSnapshot:
    """Excel + los CSV de `dir_lote2` que existan. Sin ninguno, avisa: no es un maestro del lote 2."""
    d = Path(dir_lote2)
    prov = d / PROVEEDORES_CSV
    ped = d / PEDIDOS_CSV
    if not prov.is_file() and not ped.is_file():
        raise ErrorMaestro(f"{d}: no hay {PROVEEDORES_CSV} ni {PEDIDOS_CSV}")
    return ampliar_maestro(
        excel.cargar_maestro(xlsx),
        prov if prov.is_file() else None,
        ped if ped.is_file() else None,
    )
