"""Copias del Excel real con otra FORMA o otro CONTENIDO, para ensayar el sábado a las 18:00.

El Excel de la Caja es inmutable: aquí sólo se lee y se escriben copias en el destino que se pida.
Los `.xlsx` no se guardan en git (son 10 copias de ~90 KB del mismo fichero): se generan al vuelo,
los tests los piden en `tmp_path` y a mano se sacan a `dist/ensayo/j2/maestro_cambiado/`.

    uv run python data/fixtures/maestro_cambiado/generar.py dist/ensayo/j2/maestro_cambiado

Las variantes de FORMA tienen que dar la misma versión de maestro que el original (80911e429c6c);
las de CONTENIDO, una distinta. `tests/test_excel.py` lo comprueba una por una.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import openpyxl

CAJA = Path("data/caja/FINAL_v7_DEFINITIVO_ahorasi.xlsx")
PROVEEDORES = "Proveedores"
PEDIDOS = "Pedidos_2026"


def _filas(wb: openpyxl.Workbook, hoja: str) -> list[list[Any]]:
    return [list(f) for f in wb[hoja].iter_rows(values_only=True)]


def _reescribir(wb: openpyxl.Workbook, hoja: str, filas: list[list[Any]]) -> None:
    """Sustituye la hoja por otra con las mismas filas, en el mismo sitio del libro."""
    i = wb.sheetnames.index(hoja)
    del wb[hoja]
    nueva = wb.create_sheet(hoja, i)
    for fila in filas:
        nueva.append(fila)


def _fila_de(filas: list[list[Any]], col: int, valor: str) -> list[Any]:
    return next(f for f in filas[1:] if str(f[col]).strip().upper() == valor)


# --- Variantes de FORMA: cambia el envoltorio, no el dato. Misma versión de maestro. ---


def columnas_reordenadas(wb: openpyxl.Workbook) -> str:
    """Alberto arrastra columnas: el IBAN antes que el NIF, la fecha antes del importe."""
    for hoja, orden in ((PROVEEDORES, [0, 3, 2, 1, 5, 4]), (PEDIDOS, [0, 2, 1, 5, 4, 3])):
        filas = _filas(wb, hoja)
        _reescribir(wb, hoja, [[f[j] if j < len(f) else None for j in orden] for f in filas])
    return "columnas en otro orden en las dos hojas"


def columna_nueva(wb: openpyxl.Workbook) -> str:
    """Una columna que no existía, y encima en medio: con lectura por posición lo desplaza todo."""
    for hoja, etiqueta in ((PROVEEDORES, "Centro_Coste"), (PEDIDOS, "Observaciones_2026")):
        filas = _filas(wb, hoja)
        nuevas = [
            [*f[:2], etiqueta if i == 0 else f"{etiqueta}-{i}", *f[2:]] for i, f in enumerate(filas)
        ]
        _reescribir(wb, hoja, nuevas)
    return "una columna desconocida insertada en la posición 3 de cada hoja"


def cabeceras_distintas(wb: openpyxl.Workbook) -> str:
    """Mayúsculas, tildes y guiones bajos donde antes había espacios."""
    renombres = {
        PROVEEDORES: [
            "CÓDIGO",
            "RAZÓN_SOCIAL",
            "N.I.F.",
            "IBAN ",
            "Población",
            "Condiciones de pago",
        ],
        PEDIDOS: ["N.º Pedido", "ID PROVEEDOR", "C.I.F.", "IMPORTE TOTAL", "SITUACIÓN", "Fecha"],
    }
    for hoja, cabecera in renombres.items():
        filas = _filas(wb, hoja)
        filas[0] = cabecera
        _reescribir(wb, hoja, filas)
    return "cabeceras con tildes, puntos, mayúsculas y otros nombres"


def filas_vacias(wb: openpyxl.Workbook) -> str:
    """Huecos intercalados, y una fila con datos pero sin identificador."""
    for hoja in (PROVEEDORES, PEDIDOS):
        filas = _filas(wb, hoja)
        ancho = len(filas[0])
        huerfana = [None, *([""] * (ancho - 2)), "sobra"]
        _reescribir(wb, hoja, [filas[0], [None] * ancho, *filas[1:3], huerfana, *filas[3:]])
    return "filas vacías intercaladas y una fila sin identificador"


def titulo_encima(wb: openpyxl.Workbook) -> str:
    """La cabecera baja a la fila 3 porque alguien puso un título y una fila en blanco."""
    for hoja in (PROVEEDORES, PEDIDOS):
        filas = _filas(wb, hoja)
        ancho = len(filas[0])
        titulo = [f"MAESTRO {hoja.upper()} · v7 DEFINITIVO (no borrar)", *([None] * (ancho - 1))]
        _reescribir(wb, hoja, [titulo, [None] * ancho, *filas])
    return "un título y una fila en blanco encima de la cabecera"


def hoja_renombrada(wb: openpyxl.Workbook) -> str:
    """`Pedidos_2026` pasa a llamarse `PEDIDOS 2026`, que para Excel es otra hoja."""
    wb[PEDIDOS].title = "PEDIDOS 2026"
    wb[PROVEEDORES].title = "Maestro Proveedores"
    return "hojas renombradas (mayúsculas, espacios y «Maestro Proveedores»)"


def importes_como_texto(wb: openpyxl.Workbook) -> str:
    """Los importes llegan como texto español y las fechas en dd/mm/aaaa."""
    filas = _filas(wb, PEDIDOS)
    for f in filas[1:]:
        f[3] = f"{f[3]:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".") + " EUR"
        a, m, d = str(f[5]).split("-")
        f[5] = f"{d}/{m}/{a}"
    _reescribir(wb, PEDIDOS, filas)
    return "importes como texto ('9.221,75 EUR') y fechas dd/mm/aaaa"


def hoja_norma_v4(wb: openpyxl.Workbook) -> str:
    """La regla nueva del sábado, escondida en una hoja más. Tiene que avisar con su nombre."""
    hoja = wb.create_sheet("Norma_Pagos_v4")
    for linea in (
        "NORMA DE PAGOS A PROVEEDORES (v4, vigente desde el 19/09/2026)",
        "1. Las seis reglas de la v3 siguen valiendo.",
        "7. No pagar ninguna factura de mas de 10.000 EUR sin firma del director financiero.",
    ):
        hoja.append([linea])
    return "una hoja nueva «Norma_Pagos_v4» que parece la regla del sábado"


# --- Variantes de CONTENIDO: el dato cambia de verdad. Versión de maestro distinta. ---


def proveedor_nuevo(wb: openpyxl.Workbook) -> str:
    """Un proveedor que antes no estaba, con un pedido suyo."""
    wb[PROVEEDORES].append(
        [
            "P099",
            "Reformas Altabix S.L.",
            "B03998812",
            "ES91 2100 0418 4502 0005 1332",
            "Elche",
            "30 dias",
        ]
    )
    wb[PEDIDOS].append(["PO-2026-0999", "P099", "B03998812", 4321.0, "ABIERTO", "2026-09-19"])
    return "proveedor P099 nuevo con su pedido PO-2026-0999"


def iban_cambiado(wb: openpyxl.Workbook) -> str:
    """P001 cambia de banco: sus facturas ya no cuadran con la R1."""
    filas = _filas(wb, PROVEEDORES)
    _fila_de(filas, 0, "P001")[3] = "ES91 2100 0418 4502 0005 1332"
    _reescribir(wb, PROVEEDORES, filas)
    return "el IBAN de P001 pasa a ES9121000418450200051332"


def pedido_anulado(wb: openpyxl.Workbook) -> str:
    """Un pedido pasa a ANULADO en el Excel."""
    filas = _filas(wb, PEDIDOS)
    _fila_de(filas, 0, "PO-2026-0001")[4] = "ANULADO"
    _reescribir(wb, PEDIDOS, filas)
    return "PO-2026-0001 pasa a estado ANULADO"


def importe_cambiado(wb: openpyxl.Workbook) -> str:
    """El importe de un pedido se corrige: la R2 dejará de cuadrar."""
    filas = _filas(wb, PEDIDOS)
    _fila_de(filas, 0, "PO-2026-0002")[3] = 10449.35
    _reescribir(wb, PEDIDOS, filas)
    return "PO-2026-0002 pasa de 10325,90 a 10449,35 (el importe que da el ERP del lote 2)"


FORMA: dict[str, Callable[[openpyxl.Workbook], str]] = {
    "columnas_reordenadas": columnas_reordenadas,
    "columna_nueva": columna_nueva,
    "cabeceras_distintas": cabeceras_distintas,
    "filas_vacias": filas_vacias,
    "titulo_encima": titulo_encima,
    "hoja_renombrada": hoja_renombrada,
    "importes_como_texto": importes_como_texto,
    "hoja_norma_v4": hoja_norma_v4,
}
CONTENIDO: dict[str, Callable[[openpyxl.Workbook], str]] = {
    "proveedor_nuevo": proveedor_nuevo,
    "iban_cambiado": iban_cambiado,
    "pedido_anulado": pedido_anulado,
    "importe_cambiado": importe_cambiado,
}
VARIANTES = FORMA | CONTENIDO


def generar(nombre: str, destino: Path, origen: Path = CAJA) -> Path:
    """Escribe `destino/<nombre>.xlsx` a partir del Excel real y devuelve su ruta."""
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / f"{nombre}.xlsx"
    if nombre == "original":
        shutil.copyfile(origen, ruta)
        return ruta
    wb = openpyxl.load_workbook(origen)
    try:
        VARIANTES[nombre](wb)
        wb.save(ruta)
    finally:
        wb.close()
    return ruta


def main(argv: list[str]) -> int:
    destino = Path(argv[1] if len(argv) > 1 else "dist/ensayo/j2/maestro_cambiado")
    generar("original", destino)
    for nombre, hacer in VARIANTES.items():
        generar(nombre, destino)
        clase = "FORMA" if nombre in FORMA else "CONTENIDO"
        print(f"{nombre:22} {clase:9} {(hacer.__doc__ or '').splitlines()[0]}")  # noqa: T201
    print(f"\n{len(VARIANTES)} variantes en {destino}")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
