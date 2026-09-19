"""Persistencia de fuentes y pedidos afectados por una actualización contable."""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from albertitos.core.contracts import ErpEntry, ErpSnapshot
from albertitos.sources.snapshot import (
    cargar_erp_bd,
    cargar_maestro_bd,
    diff_erp,
    guardar_erp,
    guardar_maestro,
    resumen_erp,
)


def _nuevo_asiento(numero: int) -> ErpEntry:
    return ErpEntry(
        asiento_id=f"AS-SIM-{numero:05d}",
        fecha_registro=date(2026, 9, 19),
        proveedor_id="P001",
        nif="B46102331",
        pedido=f"PO-SIM-{numero:04d}",
        importe_esperado=Decimal("123.45"),
        estado="PENDIENTE",
    )


def test_diff_lote2_tres_nuevos_dos_cambiados(erp):
    antes = erp.model_copy(update={"version": "v1"}, deep=True)
    despues = antes.model_copy(update={"version": "v2", "lote2_cargado": True}, deep=True)
    despues.asientos["AS-00001"].estado = "PAGADA"
    despues.asientos["AS-00002"].importe_esperado = Decimal("1000.00")
    for numero in (3, 1, 2):
        asiento = _nuevo_asiento(numero)
        despues.asientos[asiento.asiento_id] = asiento

    assert diff_erp(antes, despues) == {
        "de": "v1",
        "a": "v2",
        "nuevos": ["AS-SIM-00001", "AS-SIM-00002", "AS-SIM-00003"],
        "eliminados": [],
        "cambiados": {
            "AS-00001": {"estado": ("PENDIENTE", "PAGADA")},
            "AS-00002": {"importe_esperado": ("943.80", "1000.00")},
        },
        "pedidos_afectados": [
            "PO-2026-0001",
            "PO-2026-0002",
            "PO-SIM-0001",
            "PO-SIM-0002",
            "PO-SIM-0003",
        ],
    }
    assert antes.asientos["AS-00001"].estado == "PENDIENTE"
    assert len(antes.asientos) == 3


def test_diff_afecta_pedido_eliminado_y_ambos_de_asiento_reasignado(erp):
    despues = erp.model_copy(update={"version": "v2"}, deep=True)
    del despues.asientos["AS-00009"]
    despues.asientos["AS-00001"].pedido = "PO-2026-0002"

    delta = diff_erp(erp, despues)

    assert delta["eliminados"] == ["AS-00009"]
    assert delta["cambiados"] == {"AS-00001": {"pedido": ("PO-2026-0001", "PO-2026-0002")}}
    assert delta["pedidos_afectados"] == ["PO-2026-0001", "PO-2026-0002", "PO-2026-0009"]


def test_diff_solo_metadatos_no_afecta_pedidos(erp):
    despues = erp.model_copy(
        update={
            "version": "v2",
            "descargado_en": datetime(2026, 9, 19, tzinfo=UTC),
            "consultas": 35,
            "reintentos": 4,
            "lote2_cargado": True,
        }
    )

    assert diff_erp(erp, despues) == {
        "de": erp.version,
        "a": "v2",
        "nuevos": [],
        "eliminados": [],
        "cambiados": {},
        "pedidos_afectados": [],
    }


def test_diff_cambiados_ordenados_independientemente_del_orden_de_entrada(erp):
    despues = erp.model_copy(update={"version": "v2"}, deep=True)
    despues.asientos = dict(reversed(list(despues.asientos.items())))
    despues.asientos["AS-00002"].importe_esperado = Decimal("2.00")
    despues.asientos["AS-00001"].importe_esperado = Decimal("1.00")

    assert list(diff_erp(erp, despues)["cambiados"]) == ["AS-00001", "AS-00002"]


def test_snapshot_erp_conserva_tipos_y_versiones(conn, erp):
    guardar_erp(conn, erp)
    despues = erp.model_copy(update={"version": "v2"}, deep=True)
    despues.asientos["AS-00001"].estado = "PAGADA"
    guardar_erp(conn, despues)

    original = cargar_erp_bd(conn, erp.version)
    actualizado = cargar_erp_bd(conn, "v2")
    assert original == erp
    assert actualizado == despues
    assert isinstance(original.asientos["AS-00001"].importe_esperado, Decimal)
    assert isinstance(original.asientos["AS-00001"].fecha_registro, date)
    assert len(diff_erp(original, actualizado)["cambiados"]) == 1


def test_snapshot_maestro_conserva_avisos_y_tipos(conn, maestro):
    maestro.avisos_calidad.append("P007 duplicado idéntico")
    guardar_maestro(conn, maestro)

    assert cargar_maestro_bd(conn, maestro.version) == maestro
    assert cargar_maestro_bd(conn) == maestro
    assert isinstance(cargar_maestro_bd(conn).pedidos["PO-2026-0001"].importe_total, Decimal)


def test_guardar_misma_version_es_idempotente(conn, erp):
    guardar_erp(conn, erp)
    guardar_erp(conn, erp)

    assert conn.execute("SELECT count(*) FROM snapshots WHERE tipo='erp'").fetchone()[0] == 1
    assert cargar_erp_bd(conn) == erp


@pytest.mark.parametrize("cargar", [cargar_erp_bd, cargar_maestro_bd])
@pytest.mark.parametrize("version", [None, "inexistente"])
def test_snapshot_ausente_informa_como_crearlo(conn, cargar, version):
    with pytest.raises(LookupError, match="albertitos"):
        cargar(conn, version)


def test_diff_vacio_y_todos_eliminados(erp):
    vacio = ErpSnapshot(version="vacio", asientos={}, descargado_en=erp.descargado_en)

    assert diff_erp(vacio, erp)["nuevos"] == sorted(erp.asientos)
    delta = diff_erp(erp, vacio)
    assert delta["eliminados"] == sorted(erp.asientos)
    assert delta["pedidos_afectados"] == sorted(erp.por_pedido())


def _evento_erp(conn, ts, detalle, estado="ok", error=None, latencia=10):
    return conn.execute(
        "INSERT INTO eventos(ts,etapa,estado,error_codigo,latencia_ms,detalle) VALUES (?,'enrich',?,?,?,?)",
        (ts.isoformat(), estado, error, latencia, detalle),
    ).lastrowid


def test_resumen_historico_no_suma_otras_descargas(conn, erp):
    fin = datetime(2026, 9, 18, 19, 55, 36, 500000, tzinfo=UTC)
    s = erp.model_copy(update={"descargado_en": fin, "consultas": 4, "reintentos": 1})
    guardar_erp(conn, s)
    _evento_erp(conn, fin - timedelta(minutes=3), "GET /erp/estado", "retry", "ERP-429", 999)
    ids = [
        _evento_erp(conn, fin - timedelta(seconds=3), "POST /erp/login"),
        _evento_erp(
            conn,
            fin - timedelta(seconds=2),
            "GET /erp/asientos {'pagina': '1'}",
            "retry",
            "ORA-00600",
        ),
        _evento_erp(conn, fin - timedelta(seconds=1), "GET /erp/asientos {'pagina': '1'}"),
        _evento_erp(conn, fin - timedelta(milliseconds=1), "GET /erp/estado"),
    ]
    _evento_erp(conn, fin + timedelta(seconds=1), "POST /erp/login", "retry", "SES-401", 999)
    conn.commit()
    cambios = conn.total_changes
    conn.execute("PRAGMA query_only=ON")
    r = resumen_erp(conn, s.version)
    assert r == {
        "version": s.version,
        "descargado_en": fin.isoformat(),
        "asientos": len(s.asientos),
        "consultas": 4,
        "reintentos": 1,
        "errores_por_codigo": {"ORA-00600": 1},
        "latencia_total_ms": 40,
        "atribucion": "inferida_por_ventana",
        "eventos": ids,
    }
    assert conn.total_changes == cambios


def test_resumen_explicito_excluye_eventos_intercalados(conn, erp):
    s = erp.model_copy(update={"consultas": 2, "reintentos": 1})
    guardar_erp(conn, s)
    a = _evento_erp(conn, s.descargado_en, "GET /erp/estado", "retry", "ERP-429", 2)
    _evento_erp(conn, s.descargado_en, "POST /erp/login", "retry", "SES-401", 777)
    b = _evento_erp(conn, s.descargado_en, "GET /erp/estado", latencia=3)
    _evento_erp(
        conn,
        s.descargado_en,
        json.dumps(
            {
                "tipo": "erp_descarga",
                "version": s.version,
                "descargado_en": s.descargado_en.isoformat(),
                "eventos": [a, b],
            }
        ),
    )
    r = resumen_erp(conn, s.version)
    assert r["atribucion"] == "explicita"
    assert r["errores_por_codigo"] == {"ERP-429": 1}
    assert r["latencia_total_ms"] == 5 and r["eventos"] == [a, b]


def test_resumen_sin_eventos_no_inventa_ceros(conn, erp):
    guardar_erp(conn, erp)
    r = resumen_erp(conn, erp.version)
    assert r["errores_por_codigo"] is None and r["latencia_total_ms"] is None
    assert r["atribucion"] == "no_disponible"


def test_resumen_no_atribuye_ventana_incompleta(conn, erp):
    s = erp.model_copy(update={"consultas": 1})
    guardar_erp(conn, s)
    _evento_erp(conn, s.descargado_en, "GET /erp/estado")
    assert resumen_erp(conn, s.version)["atribucion"] == "no_disponible"


def test_resumen_version_inexistente_informa(conn):
    with pytest.raises(LookupError, match="no hay snapshot"):
        resumen_erp(conn, "inexistente")
