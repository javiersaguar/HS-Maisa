"""Remesa sin red, sin escribir decisiones y sin aproximar dinero con float."""

import csv
import hashlib
import json
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from albertitos.bonus import calcular, exportar, semana_iso
from albertitos.core import db
from albertitos.core.contracts import Decision, InvoiceFacts

IBAN = "ES9121000418450200051332"


@pytest.fixture
def escenario(conn, maestro, tmp_path):
    maestro.proveedores["P001"].iban = IBAN
    maestro.proveedores["P001"].condiciones_dias = 30
    db.guardar_snapshot(conn, "maestro", maestro.version, maestro.model_dump_json())

    def agregar(
        nombre="a.pdf",
        resultado="PAGAR",
        total="10.10",
        referencia=None,
        lote=1,
        motivos=None,
        norma="v3",
        **campos,
    ):
        h = InvoiceFacts(
            file_id=nombre,
            sha256=nombre,
            num_factura=referencia or nombre,
            fecha=date(2026, 8, 19),
            nif_emisor="B46102331",
            iban=IBAN,
            pedido="PO-2026-0001",
            total=Decimal(total),
            metodo="plantilla",
            extractor_version="test",
        )
        h = h.model_copy(update=campos)
        db.guardar_fichero(
            conn, sha256=nombre, file_id=nombre, lote=lote, bytes_=1, paginas=1, tiene_texto=True
        )
        db.guardar_hechos(conn, h)
        db.guardar_decision(
            conn,
            Decision(
                file_id=nombre,
                sha256=nombre,
                resultado=resultado,
                motivos=motivos or [],
                norma_version=norma,
                fecha_corte=date(2026, 9, 18),
                hechos_hash=h.hash(),
                maestro_version=maestro.version,
                erp_version="v1",
            ),
        )
        conn.commit()
        return h

    return tmp_path / "test.db", agregar


def test_sumas_csv_semanas_y_solo_pagar(escenario, tmp_path):
    ruta, agregar = escenario
    agregar()
    agregar("b.pdf", total="0.20", fecha=date(2026, 8, 18))
    agregar("c.pdf", resultado="ESCALAR")
    agregar("d.pdf", resultado="NO_PAGAR")
    informe = calcular(ruta)
    assert informe.resumen()["remesa_total_eur"] == "10.30"
    assert informe.resumen()["decisiones_pagar"] == 2
    assert informe.resumen()["vencidos"] == 1
    assert informe.resumen()["vencen_semana_corte"] == 2
    assert informe.resumen()["semanas"] == {"2026-W38": {"numero": 2, "importe_eur": "10.30"}}
    assert all(p.fecha_ejecucion == date(2026, 9, 18) for p in informe.remesa)
    exportar(informe, tmp_path / "salida", ruta_bd=ruta)
    with (tmp_path / "salida/remesa.csv").open() as f:
        filas = list(csv.DictReader(f, delimiter=";"))
    assert {f["file_id"] for f in filas} == {"a.pdf", "b.pdf"}
    assert sum(Decimal(f["importe_eur"]) for f in filas) == Decimal("10.30")
    assert semana_iso(date(2027, 1, 1)) == "2026-W53"


@pytest.mark.parametrize(
    "campo,valor,codigo,en_calendario",
    [
        ("iban", "ES000000", "IBAN_INVALIDO", 1),
        ("condiciones_dias", None, "SIN_CONDICIONES", 0),
        ("condiciones_dias", -1, "SIN_CONDICIONES", 0),
    ],
)
def test_exclusiones_maestro(escenario, conn, maestro, campo, valor, codigo, en_calendario):
    ruta, agregar = escenario
    agregar()
    setattr(maestro.proveedores["P001"], campo, valor)
    db.guardar_snapshot(conn, "maestro", maestro.version, maestro.model_dump_json())
    conn.commit()
    informe = calcular(ruta)
    assert not informe.remesa
    assert len(informe.calendario) == en_calendario
    assert codigo in {a.codigo for a in informe.avisos}
    assert informe.resumen()["excluidos_remesa"] == 1


def test_usa_maestro_de_la_decision(escenario, conn, maestro):
    ruta, agregar = escenario
    agregar()
    maestro.version = "posterior"
    maestro.proveedores["P001"].iban = "ES00"
    db.guardar_snapshot(conn, "maestro", maestro.version, maestro.model_dump_json())
    conn.commit()
    assert calcular(ruta).remesa[0].iban == IBAN


@pytest.mark.parametrize(
    "campos,codigo",
    [
        ({"iban": "ES00"}, "IBAN_DISCREPANTE"),
        ({"nif_emisor": "OTRO"}, "PROVEEDOR_NO_IDENTIFICADO"),
        ({"fecha": None}, "FACTURA_INCOMPLETA"),
        ({"total": Decimal("-1")}, "IMPORTE_INVALIDO"),
        ({"total": Decimal("1.001")}, "IMPORTE_INVALIDO"),
    ],
)
def test_datos_no_pagables(escenario, campos, codigo):
    ruta, agregar = escenario
    agregar(**campos)
    informe = calcular(ruta)
    assert not informe.remesa
    assert informe.avisos[0].codigo == codigo


def test_hechos_cambiados_exigen_reprocesado(escenario, conn):
    ruta, agregar = escenario
    h = agregar()
    h.total = Decimal("999.00")
    db.guardar_hechos(conn, h)
    conn.commit()
    informe = calcular(ruta)
    assert not informe.remesa
    assert informe.avisos[0].codigo == "HECHOS_NO_VIGENTES"


def test_duplicados_no_se_preparan(escenario, conn):
    ruta, agregar = escenario
    agregar(referencia="R1")
    agregar("b.pdf", referencia="R1")
    agregar("c.pdf")
    db.guardar_identidad(conn, file_id="copia.pdf", lote=2, sha256="c.pdf")
    conn.commit()
    informe = calcular(ruta)
    assert not informe.remesa
    assert {a.codigo for a in informe.avisos} == {"REFERENCIA_DUPLICADA", "COPIA_EXACTA"}


def test_cli_solo_lectura_y_repetible(escenario, tmp_path):
    ruta, agregar = escenario
    agregar()
    antes = hashlib.sha256(ruta.read_bytes()).hexdigest()
    salida = tmp_path / "salida"
    cmd = [sys.executable, "-m", "albertitos.bonus", "--db", str(ruta), "--salida", str(salida)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    ficheros = {p.name: p.read_bytes() for p in salida.iterdir()}
    assert subprocess.run(cmd, capture_output=True).returncode == 0
    assert ficheros == {p.name: p.read_bytes() for p in salida.iterdir()}
    assert hashlib.sha256(ruta.read_bytes()).hexdigest() == antes
    assert json.loads((salida / "resumen.json").read_text())["remesa_numero"] == 1


def test_corte_explicito_si_bd_vacia(escenario):
    ruta, _ = escenario
    with pytest.raises(ValueError, match="fecha-corte"):
        calcular(ruta)
    assert calcular(ruta, date(2026, 9, 18)).resumen()["remesa_total_eur"] == "0.00"


def test_exportacion_no_interpreta_texto(escenario, tmp_path):
    ruta, agregar = escenario
    agregar(referencia="=1+2", razon_social="<script>alert(1)</script>")
    informe = calcular(ruta)
    informe.calendario[0].beneficiario = "<script>alert(1)</script>"
    salida = tmp_path / "salida"
    exportar(informe, salida, ruta_bd=ruta)
    assert "'=1+2" in (salida / "remesa.csv").read_text()
    assert "<script>" not in (salida / "calendario.html").read_text()


def test_no_sobrescribe_bd_ni_entrega(escenario, tmp_path):
    ruta, agregar = escenario
    agregar()
    informe = calcular(ruta)
    salida = tmp_path / "salida"
    salida.mkdir()
    try:
        (salida / "remesa.csv").symlink_to(ruta)
    except OSError:  # Windows sin modo desarrollador: crear un symlink pide privilegios
        pass
    else:
        with pytest.raises(ValueError, match="enlace"):
            exportar(informe, salida, ruta_bd=ruta)
    with pytest.raises(ValueError, match="oficial"):
        exportar(informe, Path("dist/entrega/bonus"), ruta_bd=ruta)


SINTETICO = "ES2100491500051234567890"  # el IBAN de P001 en la Caja: forma de IBAN, mod-97 falla


def _con_iban_sintetico(conn, maestro, agregar):
    maestro.proveedores["P001"].iban = SINTETICO
    db.guardar_snapshot(conn, "maestro", maestro.version, maestro.model_dump_json())
    agregar("a.pdf", iban=SINTETICO)
    agregar("b.pdf", iban=SINTETICO)


def test_iban_sintetico_de_la_caja_entra_marcado_y_avisa_una_vez(escenario, conn, maestro):
    """Los 11 IBAN del maestro de la Caja no pasan el mod-97. Excluirlos dejaba la remesa en 0 pagos
    con 438 PAGAR: el bonus no enseñaba nada. Entran marcados, con un aviso por proveedor."""
    ruta, agregar = escenario
    _con_iban_sintetico(conn, maestro, agregar)
    informe = calcular(ruta)
    assert [p.file_id for p in informe.remesa] == ["a.pdf", "b.pdf"]
    assert not any(p.iban_control_ok for p in informe.remesa)
    assert [a.codigo for a in informe.avisos] == ["IBAN_SIN_CONTROL"]
    assert informe.resumen()["remesa_iban_sin_control"] == 2


def test_modo_estricto_excluye_lo_que_un_banco_rechazaria(escenario, conn, maestro):
    ruta, agregar = escenario
    _con_iban_sintetico(conn, maestro, agregar)
    informe = calcular(ruta, estricto=True)
    assert not informe.remesa
    assert {a.codigo for a in informe.avisos} == {"IBAN_INVALIDO"}


# --------------------------------------------------------------------- K1: tesorería, proveedores, rutas


def _informe_varios(escenario, conn):
    """Tres pagos de P001 a 30 días: `b` vencido (01/08 → 31/08); `a` vence justo el día de corte (19/08 →
    18/09: no está vencido) y `c`, del lote 2, en plazo (10/09 → 10/10)."""
    ruta, agregar = escenario
    agregar("a.pdf", total="100.00", referencia="F-1")
    agregar("b.pdf", total="250.50", referencia="F-2", fecha=date(2026, 8, 1))
    agregar("c.pdf", total="49.50", referencia="F-3", fecha=date(2026, 9, 10), lote=2)
    return ruta, calcular(ruta)


def test_cada_pago_dice_su_lote(escenario, conn):
    _, informe = _informe_varios(escenario, conn)
    assert {p.file_id: p.lote for p in informe.calendario} == {"a.pdf": 1, "b.pdf": 1, "c.pdf": 2}


def test_tesoreria_y_proveedores_cuadran_al_centimo(escenario, conn):
    from albertitos.bonus import tesoreria as tes

    _, informe = _informe_varios(escenario, conn)
    t = tes.tesoreria(informe)
    assert t["importe_eur"] == "400.00"
    assert sum(Decimal(s["importe_eur"]) for s in t["semanas"]) == Decimal("400.00")
    assert t["semanas"][-1]["acumulado_eur"] == "400.00"
    assert Decimal(t["vencido_importe_eur"]) + Decimal(t["en_plazo_importe_eur"]) == Decimal(
        "400.00"
    )
    assert (t["vencido_numero"], t["en_plazo_numero"]) == (1, 2)
    (p,) = tes.proveedores(informe)
    assert (p["proveedor_id"], p["numero"], p["importe_eur"], p["lotes"]) == (
        "P001",
        3,
        "400.00",
        [1, 2],
    )


def test_programa_respeta_el_tope_y_dice_cuanto_se_tarda(escenario, conn):
    from albertitos.bonus import tesoreria as tes

    _, informe = _informe_varios(escenario, conn)
    pr = tes.programa(informe, Decimal("260"))
    assert all(Decimal(s["importe_eur"]) <= 260 for s in pr["semanas"])
    assert pr["sin_programar_numero"] == 0 and pr["semanas_para_ponerse_al_dia"] >= 1
    assert sum(s["numero"] for s in pr["semanas"]) == 3
    # un pago mayor que el tope sale solo, marcado, y no se trocea
    grande = tes.programa(informe, Decimal("200"))
    assert any(s["supera_tope"] and s["numero"] == 1 for s in grande["semanas"])
    assert grande["sin_programar_numero"] == 0
    with pytest.raises(ValueError):
        tes.programa(informe, Decimal("0"))


def test_rutas_por_el_puente_de_la_consola(escenario, conn, monkeypatch):
    """Lo que hará Alejandro con una línea (RUTAS.update(bonus.rutas())), probado sin tocar su fichero."""
    from albertitos import bonus
    from albertitos.console import api

    ruta, _ = _informe_varios(escenario, conn)
    for path, handler in bonus.rutas().items():
        monkeypatch.setitem(api.RUTAS, path, handler)
    ro = db.conectar(ruta, solo_lectura=True)
    try:
        st, body = api.despachar("GET", "/bonus/resumen", {}, ro)
        assert st == 200 and body["decisiones_pagar"] == 3 and body["lotes"] == [1, 2]
        st, body = api.despachar("GET", "/bonus/calendario", {"lote": ["2"]}, ro)
        assert st == 200 and [p["file_id"] for p in body["pagos"]] == ["c.pdf"]
        assert (
            body["pagos"][0]["importe_eur"] == "49.50"
        )  # Decimal como string, sin perder céntimos
        st, body = api.despachar(
            "GET", "/bonus/calendario", {"vencido": ["true"], "limite": ["1"]}, ro
        )
        assert (st, body["total"], body["mostrados"]) == (200, 1, 1)
        st, body = api.despachar("GET", "/bonus/tesoreria", {"tope": ["260"]}, ro)
        assert st == 200 and body["programa"]["tope_semanal_eur"] == "260.00"
        for path in ("/bonus/proveedores", "/bonus/remesa", "/bonus/avisos"):
            assert api.despachar("GET", path, {}, ro)[0] == 200
        assert api.despachar("GET", "/bonus/tesoreria", {"tope": ["-5"]}, ro)[0] == 400
        assert api.despachar("GET", "/bonus/calendario", {"vencido": ["quizá"]}, ro)[0] == 400
        assert (
            api.despachar("POST", "/bonus/resumen", {}, ro)[0] == 405
        )  # el puente sigue siendo GET
        assert (
            not ro.in_transaction
        )  # la lectura no deja transacciones abiertas en la conexión del puente
    finally:
        ro.close()


def test_rutas_con_bd_sin_decisiones_dicen_por_que(tmp_path, monkeypatch):
    from albertitos import bonus

    vacia = tmp_path / "vacia.db"
    c = db.conectar(vacia)
    db.init_schema(c)
    c.close()
    ro = db.conectar(vacia, solo_lectura=True)
    try:
        st, body = bonus.rutas()["/bonus/resumen"](ro, {})
        assert st == 409 and "corte" in body["error"]
    finally:
        ro.close()


def test_exporta_tesoreria_y_proveedores(escenario, conn, tmp_path):
    ruta, informe = _informe_varios(escenario, conn)
    salida = tmp_path / "bonus"
    exportar(informe, salida, ruta_bd=ruta, tope_semanal=Decimal("260"))
    teso = json.loads((salida / "tesoreria.json").read_text(encoding="utf-8"))
    assert teso["importe_eur"] == "400.00" and "programa" in teso
    filas = list(csv.DictReader((salida / "proveedores.csv").open(encoding="utf-8"), delimiter=";"))
    assert [(f["proveedor_id"], f["importe_eur"]) for f in filas] == [("P001", "400.00")]
    html = (salida / "calendario.html").read_text(encoding="utf-8")
    assert "<h2>Tesorería</h2>" in html and "260.00 € por semana" in html


BD_REAL = Path("dist/albertitos.db")


@pytest.mark.skipif(not BD_REAL.exists(), reason="sin la BD real (dist/albertitos.db)")
def test_el_bonus_no_cambia_la_entrega_ni_la_bd(tmp_path, monkeypatch):
    """Regla 5 del PLAN-11: con el bonus ejecutado entero (calendario, tesorería, rutas y exportación)
    sobre una copia de la BD real, la BD no cambia ni un byte y `package` da el mismo outcomes.jsonl."""
    import sqlite3

    from albertitos import bonus
    from albertitos.bonus import tesoreria as tes

    copia = tmp_path / "copia.db"
    origen = sqlite3.connect(f"file:{BD_REAL}?mode=ro", uri=True)
    destino = sqlite3.connect(copia)
    origen.backup(destino)
    destino.close()
    origen.close()

    def package(salida: Path) -> str:
        # El lote 1 solo: con el material del lote 2 en data/lote2 y sin decidir, `albertitos package`
        # se niega (falta una decisión), y aquí se compara outcomes.jsonl, que es lo que el bonus podría tocar.
        from albertitos.pipeline import package as pk

        conn = db.conectar(copia)
        try:
            pk.empaquetar(conn, salida, Path("data/caja"), None, con_traza=True)
        finally:
            conn.close()
        return hashlib.sha256((salida / "outcomes.jsonl").read_bytes()).hexdigest()

    antes = package(tmp_path / "antes")
    huella_bd = hashlib.sha256(copia.read_bytes()).hexdigest()
    informe = calcular(copia)
    tes.tesoreria(informe)
    tes.proveedores(informe)
    tes.programa(informe, Decimal("150000"))
    ro = db.conectar(copia, solo_lectura=True)
    try:
        for handler in bonus.rutas().values():
            handler(ro, {"tope": ["150000"]})
    finally:
        ro.close()
    exportar(informe, tmp_path / "bonus", ruta_bd=copia, tope_semanal=Decimal("150000"))
    assert hashlib.sha256(copia.read_bytes()).hexdigest() == huella_bd
    assert package(tmp_path / "despues") == antes


def test_confianza_opcional_en_el_calendario(escenario, conn, monkeypatch):
    """Con K3 presente, cada pago lleva su confianza tal cual; sin K3, `null` y una nota. Nunca falla."""
    import types

    from albertitos import bonus

    ruta, _ = _informe_varios(escenario, conn)
    ro = db.conectar(ruta, solo_lectura=True)
    try:
        calendario = bonus.rutas()["/bonus/calendario"]
        monkeypatch.setitem(sys.modules, "albertitos.confianza", None)  # sin K3: el import falla
        st, body = calendario(ro, {"con_confianza": ["true"]})
        assert st == 200 and all(p["confianza"] is None for p in body["pagos"])
        assert "no disponible" in body["confianza_nota"]
        falso = types.ModuleType("albertitos.confianza")

        def puntuar(conn, file_id):
            if file_id == "b.pdf":
                raise RuntimeError("una factura rara")
            return {"puntuacion": 90, "banda": "alta"}

        falso.puntuar = puntuar
        monkeypatch.setitem(sys.modules, "albertitos.confianza", falso)
        st, body = calendario(ro, {"con_confianza": ["true"]})
        por_id = {p["file_id"]: p["confianza"] for p in body["pagos"]}
        assert st == 200 and por_id == {
            "a.pdf": {"puntuacion": 90, "banda": "alta"},
            "b.pdf": None,
            "c.pdf": {"puntuacion": 90, "banda": "alta"},
        }
        assert body["confianza_nota"] == "confianza de K3 en 2 de 3 pagos"
        assert (
            "confianza_nota" not in calendario(ro, {})[1]
        )  # sin pedirla, el calendario no la toca
    finally:
        ro.close()


def _conversion(moneda, tipo, total_eur, **extra):
    return {
        "regla_id": "v4.R7",
        "ok": True,
        "detalle": "Conversión registrada",
        "evidencia": {"moneda": moneda, "tipo": tipo, "total_eur": total_eur, **extra},
    }


@pytest.mark.parametrize(
    "moneda,total,tipo,euros",
    [
        ("USD", "2450.00", "0.92", "2254.00"),
        ("JPY", "10000", "0.00617", "61.70"),
    ],
)
def test_divisas_con_conversion_guardada_en_calendario_chat_y_remesa(
    escenario, conn, tmp_path, moneda, total, tipo, euros
):
    from albertitos.bonus import rutas, tesoreria
    from albertitos.chat.herramientas import Herramientas

    ruta, agregar = escenario
    agregar("eur.pdf", total="10.10")
    agregar(
        "divisa.pdf",
        moneda=moneda,
        total=total,
        motivos=[_conversion(moneda, tipo, euros)],
        norma="v4",
    )
    antes = [tuple(f) for f in conn.execute("SELECT * FROM decisiones")]
    cambios = conn.total_changes
    informe = calcular(ruta)
    pago = next(p for p in informe.calendario if p.file_id == "divisa.pdf")
    assert (pago.importe_original, pago.moneda, pago.importe_eur, pago.tipo_cambio) == (
        Decimal(total),
        moneda,
        Decimal(euros),
        Decimal(tipo),
    )
    esperado = Decimal("10.10") + Decimal(euros)
    assert Decimal(informe.resumen()["calendario_total_eur"]) == esperado
    assert Decimal(tesoreria.tesoreria(informe)["importe_eur"]) == esperado
    assert Decimal(tesoreria.proveedores(informe)[0]["importe_eur"]) == esperado
    status, calendario = rutas()["/bonus/calendario"](conn, {})
    assert status == 200
    assert next(p for p in calendario["pagos"] if p["file_id"] == "divisa.pdf")["moneda"] == moneda
    chat = Herramientas(ruta).ejecutar("pagos", {})
    assert Decimal(chat["importe_eur"]) == esperado
    assert next(p for p in chat["items"] if p["file_id"] == "divisa.pdf")[
        "importe_original"
    ] == str(Decimal(total))
    exportar(informe, tmp_path / "divisas", ruta_bd=ruta)
    with (tmp_path / "divisas/remesa.csv").open() as f:
        filas = list(csv.DictReader(f, delimiter=";"))
    assert sum(Decimal(f["importe_eur"]) for f in filas) == esperado
    assert next(f for f in filas if f["file_id"] == "divisa.pdf")["moneda"] == moneda
    assert [tuple(f) for f in conn.execute("SELECT * FROM decisiones")] == antes
    assert conn.total_changes == cambios


@pytest.mark.parametrize("moneda", ["USD", "JPY"])
def test_divisas_sin_conversion_no_se_suman_como_euros(escenario, conn, moneda):
    from albertitos.bonus import rutas
    from albertitos.chat.herramientas import Herramientas

    ruta, agregar = escenario
    agregar("eur.pdf")
    agregar("divisa.pdf", moneda=moneda, total="2450.00")
    informe = calcular(ruta)
    assert [p.file_id for p in informe.calendario] == ["eur.pdf"]
    assert [p.file_id for p in informe.remesa] == ["eur.pdf"]
    assert informe.resumen()["calendario_total_eur"] == "10.10"
    status, resumen = rutas()["/bonus/resumen"](conn, {})
    assert status == 200
    assert resumen["excluidos_moneda"] == 1
    assert resumen["sin_vencimiento_calculable"] == 0
    (aviso,) = resumen["avisos_divisas"]
    assert aviso["file_id"] == "divisa.pdf"
    assert "2450.00 " + moneda in aviso["detalle"]
    chat = Herramientas(ruta).ejecutar("pagos", {})
    assert chat["importe_eur"] == "10.10"
    assert chat["avisos_divisas"] == resumen["avisos_divisas"]


@pytest.mark.parametrize(
    "motivo",
    [
        _conversion("USD", "0.92", "999.00"),
        _conversion("JPY", "0.92", "2254.00"),
        _conversion("USD", "NaN", "2254.00"),
        _conversion("USD", "-1", "2254.00"),
        {**_conversion("USD", "0.92", "2254.00"), "ok": False},
        {**_conversion("USD", "0.92", "2254.00"), "regla_id": "v3.R7"},
    ],
)
def test_conversion_incoherente_no_entra_en_remesa(escenario, motivo):
    ruta, agregar = escenario
    agregar(moneda="USD", total="2450.00", motivos=[motivo], norma="v4")
    informe = calcular(ruta)
    assert not informe.calendario and not informe.remesa
    assert informe.resumen()["avisos_divisas"][0]["codigo"] == "CONVERSION_NO_VERIFICABLE"
