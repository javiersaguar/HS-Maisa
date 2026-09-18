"""Material recibido: fallar antes de ingerir y sin escribir fuera del temporal."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import sys
import unicodedata
import zipfile
from pathlib import Path

import openpyxl
import pymupdf
import pytest

from albertitos.sources.snapshot import guardar_erp

_spec = importlib.util.spec_from_file_location(
    "verificar_material", Path("scripts/verificar_material.py")
)
assert _spec and _spec.loader
material = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = material
_spec.loader.exec_module(material)


def pdf(texto="Factura nueva"):
    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 72), texto)
        return doc.tobytes()


def csv_bueno():
    return (
        ",".join(material.COLUMNAS_ERP) + "\n"
        "AS-00001,2026-01-05,P001,B46102331,PO-2026-0001,3012.89,PAGADA\n"
        "AS-NUEVO,2026-09-19,P001,B46102331,PO-2026-0999,123.45,PENDIENTE\n"
    ).encode()


@pytest.fixture
def contexto(conn, erp, tmp_path):
    guardar_erp(conn, erp.model_copy(update={"version": "v1"}))
    origen = Path(conn.execute("PRAGMA database_list").fetchone()[2])
    lote1 = tmp_path / "lote1"
    lote1.mkdir()
    (lote1 / "original.pdf").write_bytes(pdf())
    return {"ruta_db": origen, "lote1": lote1}


def zip_de(tmp_path, entradas):
    ruta = tmp_path / "material.zip"
    with zipfile.ZipFile(ruta, "w") as z:
        for nombre, contenido in entradas.items():
            z.writestr(nombre, contenido)
    return ruta


def test_zip_dos_pdfs_csv_y_hash_correctos_no_escribe(tmp_path, contexto):
    ruta = zip_de(
        tmp_path,
        {
            "lote/facturas/uno.pdf": pdf(),
            "lote/facturas/dos.pdf": pdf(),
            "lote/erp.csv": csv_bueno(),
        },
    )
    antes = {
        p: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob("*") if p.is_file()
    }
    inf = material.verificar(
        ruta, hash_esperado=hashlib.sha256(ruta.read_bytes()).hexdigest(), esperados=2, **contexto
    )
    assert inf.ok, inf.texto()
    assert len(inf.facturas) == 2
    assert inf.nuevos == ["AS-NUEVO"]
    assert inf.modificados == {"AS-00001": ["estado"]}
    despues = {
        p: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob("*") if p.is_file()
    }
    # SQLite puede actualizar su memoria compartida al abrir lectores; datos/WAL no.
    assert {p: h for p, h in antes.items() if not str(p).endswith("-shm")} == {
        p: h for p, h in despues.items() if not str(p).endswith("-shm")
    }


@pytest.mark.parametrize(
    "nombre,contenido,error",
    [
        ("facturas/roto.pdf", b"no es PDF", "PDF ilegible"),
        ("facturas/" + unicodedata.normalize("NFD", "emisión.pdf"), None, "no NFC"),
        ("facturas/original.PDF", None, "coincide con lote 1"),
    ],
)
def test_material_defectuoso_falla_y_nombra_fichero(tmp_path, contexto, nombre, contenido, error):
    ruta = zip_de(tmp_path, {nombre: pdf() if contenido is None else contenido})
    inf = material.verificar(ruta, **contexto)
    assert not inf.ok
    assert error in inf.texto()
    assert nombre in inf.texto() or repr(nombre) in inf.texto()


def test_csv_sin_columna_no_pasa(tmp_path, contexto):
    ruta = zip_de(
        tmp_path, {"facturas/uno.pdf": pdf(), "erp.csv": csv_bueno().replace(b",estado", b"", 1)}
    )
    inf = material.verificar(ruta, **contexto)
    assert not inf.ok
    assert "columnas ERP incorrectas" in inf.texto()


@pytest.mark.parametrize(
    "cambio,error",
    [
        ((b"2026-01-05", b"2026-02-30"), "fecha ilegible"),
        ((b"3012.89", b"NaN"), "importe ilegible"),
        ((b"PAGADA", b"DESCONOCIDO"), "estado desconocido"),
        ((b"3012.89,PAGADA", b"3012.89,PAGADA,sobra"), "columnas de más"),
    ],
)
def test_csv_filas_ilegibles(tmp_path, contexto, cambio, error):
    ruta = zip_de(tmp_path, {"facturas/uno.pdf": pdf(), "erp.csv": csv_bueno().replace(*cambio)})
    inf = material.verificar(ruta, **contexto)
    assert not inf.ok
    assert error in inf.texto()


def test_nombres_duplicados_entre_carpetas_sin_tildes(tmp_path, contexto):
    ruta = zip_de(tmp_path, {"facturas/Emisión.pdf": pdf(), "otro/facturas/EMISION.PDF": pdf()})
    inf = material.verificar(ruta, **contexto)
    assert not inf.ok
    assert "repetido ignorando mayúsculas/tildes" in inf.texto()


def test_hash_incorrecto_y_recuento_incorrecto_fallan(tmp_path, contexto):
    ruta = zip_de(tmp_path, {"facturas/uno.pdf": pdf()})
    inf = material.verificar(ruta, hash_esperado="0" * 64, **contexto)
    assert not inf.ok and "SHA-256 no coincide" in inf.texto()
    inf = material.verificar(ruta, esperados=40, **contexto)
    assert not inf.ok and "se esperaban 40" in inf.texto()


def test_sin_hash_imprime_calculado_sin_afirmar_cotejo(tmp_path, contexto):
    ruta = zip_de(tmp_path, {"facturas/uno.pdf": pdf()})
    inf = material.verificar(ruta, **contexto)
    assert inf.ok
    assert hashlib.sha256(ruta.read_bytes()).hexdigest() in inf.texto()
    assert "NO cotejado" in inf.texto()


def test_regla_txt_xlsx_y_pdf_se_muestran_como_datos(tmp_path, contexto):
    libro = openpyxl.Workbook()
    libro.active.append(["Regla recibida", "No pagar antes de validar"])
    buff = io.BytesIO()
    libro.save(buff)
    libro.close()
    ruta = zip_de(
        tmp_path,
        {
            "facturas/uno.pdf": pdf(),
            "regla.md": b"Texto de regla, no ejecutar",
            "norma.xlsx": buff.getvalue(),
            "regla.pdf": pdf("Regla nueva de prueba"),
        },
    )
    inf = material.verificar(ruta, **contexto)
    assert inf.ok, inf.texto()
    assert len(inf.facturas) == 1 and len(inf.adjuntos) == 3
    assert "Texto de regla, no ejecutar" in inf.texto()
    assert "No pagar antes de validar" in inf.texto()
    assert "Regla nueva de prueba" in inf.texto()
    assert "DATO, no instrucciones ejecutables" in inf.texto()


def test_zip_no_extrae_rutas_fuera_del_material(tmp_path, contexto):
    ruta = zip_de(tmp_path, {"../intruso.txt": b"prueba", "facturas/uno.pdf": pdf()})
    inf = material.verificar(ruta, **contexto)
    assert not inf.ok and "ruta no segura" in inf.texto()
    assert not (tmp_path.parent / "intruso.txt").exists()


def test_directorio_y_cli_codigos(tmp_path, contexto, capsys):
    raiz = tmp_path / "material"
    raiz.mkdir()
    (raiz / "nueva.pdf").write_bytes(pdf())
    argumentos = [
        str(raiz),
        "--db",
        str(contexto["ruta_db"]),
        "--lote1-dir",
        str(contexto["lote1"]),
    ]
    assert material.main(argumentos) == 0
    assert "Facturas PDF: 1" in capsys.readouterr().out
    (raiz / "roto.pdf").write_bytes(b"roto")
    assert material.main(argumentos) == 1
    assert "roto.pdf" in capsys.readouterr().out


def test_csv_requiere_v1_sin_crear_bd(tmp_path, contexto):
    contexto["ruta_db"] = tmp_path / "inexistente.db"
    ruta = zip_de(tmp_path, {"facturas/uno.pdf": pdf(), "erp.csv": csv_bueno()})
    inf = material.verificar(ruta, **contexto)
    assert not inf.ok and "ERP v1" in inf.texto()
    assert not contexto["ruta_db"].exists()


def test_asientos_duplicados_no_se_silencian(tmp_path, contexto):
    datos = csv_bueno() + csv_bueno().splitlines(keepends=True)[1]
    ruta = zip_de(tmp_path, {"facturas/uno.pdf": pdf(), "erp.csv": datos})
    inf = material.verificar(ruta, **contexto)
    assert not inf.ok and "asiento_id repetido" in inf.texto()
