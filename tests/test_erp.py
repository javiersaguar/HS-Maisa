"""Contra el bridge real (make erp-fast). Se saltan si no responde."""

import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from albertitos.core import db
from albertitos.sources import erp
from albertitos.sources.erp import ClienteERP, ErrorERP
from albertitos.sources.snapshot import guardar_erp, resumen_erp

pytestmark = pytest.mark.erp


def test_descarga_completa_con_reintentos(erp_vivo, conn):
    with ClienteERP(erp_vivo, conn=conn, rps=9) as c:
        s = c.descargar_todo("test")
        est = c.estado()
    assert len(s.asientos) == int(est["asientos"])
    assert s.consultas >= 27  # 26 páginas + estado (+ login)
    assert s.reintentos >= 2  # ORA-00600 cada 10ª consulta autenticada
    a = next(iter(s.asientos.values()))
    assert a.importe_esperado.as_tuple().exponent == -2 and a.fecha_registro.year == 2026
    n_ora = conn.execute(
        "SELECT count(*) n FROM eventos WHERE estado='retry' AND error_codigo='ORA-00600'"
    ).fetchone()["n"]
    assert n_ora >= 2
    assert n_ora <= s.reintentos  # otro cliente puede provocar además ERP-429
    guardar_erp(conn, s)
    resumen = resumen_erp(conn, s.version)
    assert resumen["atribucion"] == "explicita"
    assert len(resumen["eventos"]) == s.consultas
    assert resumen["errores_por_codigo"]["ORA-00600"] == n_ora
    assert resumen["latencia_total_ms"] >= 0


def test_token_caducado_se_renueva_solo(erp_vivo, conn):
    with ClienteERP(erp_vivo, conn=conn, rps=9) as c:
        c.login()
        c.token = "token-invalido"
        c.usos = 0
        asientos, paginas, total = c.pagina(1)
        assert c.token and c.token != "token-invalido"
    assert paginas >= 1 and len(asientos) == 20 and total >= len(asientos)
    assert (
        conn.execute(
            "SELECT count(*) n FROM eventos WHERE error_codigo='SES-401' AND estado='retry'"
        ).fetchone()["n"]
        == 1
    )


@pytest.mark.parametrize("usos", [250, 300])
def test_renovacion_proactiva_por_usos(erp_vivo, conn, usos):
    with ClienteERP(erp_vivo, conn=conn, rps=9) as c:
        anterior = c.login()
        c.usos = usos
        asientos, _, _ = c.pagina(1)
        assert c.token != anterior
        assert len(asientos) == 20 and c.usos < usos
    assert (
        conn.execute("SELECT count(*) n FROM eventos WHERE error_codigo='SES-401'").fetchone()["n"]
        == 0
    )


def test_renovacion_proactiva_por_tiempo(erp_vivo, conn, monkeypatch):
    monkeypatch.setattr(erp, "RENOVAR_A_LOS_SEGUNDOS", 1)
    with ClienteERP(erp_vivo, conn=conn, rps=9) as c:
        anterior = c.login()
        time.sleep(1.05)
        asientos, _, _ = c.pagina(1)
        assert c.token != anterior and len(asientos) == 20
    assert (
        conn.execute("SELECT count(*) n FROM eventos WHERE error_codigo='SES-401'").fetchone()["n"]
        == 0
    )


def test_pagina_fuera_de_rango(erp_vivo, conn):
    with ClienteERP(erp_vivo, conn=conn, rps=9) as c:
        with pytest.raises(ErrorERP) as e:
            c.pagina(999)
    assert e.value.codigo == "ERP-400"
    evento = conn.execute("SELECT * FROM eventos ORDER BY id DESC LIMIT 1").fetchone()
    assert evento["estado"] == "error" and evento["error_codigo"] == "ERP-400"


def _saturar_bridge(url):
    """Provoca el 429 real sin alterar el bridge ni sustituir sus respuestas."""
    with httpx.Client(base_url=url, timeout=5) as http:
        for _ in range(30):
            if http.get("/erp/estado").status_code == 429:
                return
    pytest.fail("El bridge no aplicó su límite de 10 peticiones por segundo")


def test_login_reintenta_429_y_respeta_retry_after(erp_vivo, conn):
    with ClienteERP(erp_vivo, conn=conn, rps=9) as c:
        _saturar_bridge(erp_vivo)
        inicio = time.monotonic()
        assert c.login()
        duracion = time.monotonic() - inicio
        asientos, _, _ = c.pagina(1)
    assert len(asientos) == 20 and duracion >= 1
    codigos = {
        fila["error_codigo"]
        for fila in conn.execute("SELECT error_codigo FROM eventos WHERE estado='retry'")
    }
    assert "ERP-429" in codigos
    # En HTTP/1.1 el cuerpo no leído del login rechazado no debe contaminar otro request.
    assert codigos <= {"ERP-429", "ORA-00600"}


def test_429_agotado_emite_error_sin_reintento_ficticio(erp_vivo, conn):
    with ClienteERP(erp_vivo, conn=conn, max_intentos=1) as c:
        _saturar_bridge(erp_vivo)
        with pytest.raises(ErrorERP, match="ERP-429") as e:
            c.estado()
        assert e.value.codigo == "ERP-AGOTADO" and c.reintentos == 0
    evento = conn.execute("SELECT * FROM eventos ORDER BY id DESC LIMIT 1").fetchone()
    assert evento["estado"] == "error" and evento["error_codigo"] == "ERP-429"


def test_dos_clientes_concurrentes_completan_snapshot(erp_vivo, tmp_path):
    ruta = tmp_path / "clientes.db"
    inicial = db.conectar(ruta)
    db.init_schema(inicial)
    inicial.close()

    def descargar(indice):
        # Conexiones distintas escriben la misma BD, como dos procesos de la ingesta.
        conn = db.conectar(ruta)
        try:
            with ClienteERP(erp_vivo, conn=conn, rps=9) as cliente:
                snapshot = cliente.descargar_todo(f"concurrente-{indice}")
                total = int(cliente.estado()["asientos"])
            guardar_erp(conn, snapshot)
            resumen = resumen_erp(conn, snapshot.version)
            assert resumen["atribucion"] == "explicita"
            assert len(resumen["eventos"]) == snapshot.consultas
            assert sum(resumen["errores_por_codigo"].values()) == snapshot.reintentos
            errores = [
                fila["error_codigo"]
                for fila in conn.execute("SELECT error_codigo FROM eventos WHERE estado='retry'")
            ]
            return snapshot, total, errores
        finally:
            conn.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(descargar, (1, 2)))
    primero, segundo = resultados
    assert primero[0].asientos == segundo[0].asientos
    for snapshot, total, errores in resultados:
        assert len(snapshot.asientos) == total
        assert set(errores) <= {"ERP-429", "ORA-00600"}
    assert "ERP-429" in primero[2] + segundo[2]


def test_conexion_rechazada_se_registra_y_agota(conn):
    # Puerto reservado sin escuchar: fallo de transporte real, sin servidor ni mocks.
    with socket.socket() as reserva:
        reserva.bind(("127.0.0.1", 0))
        puerto = reserva.getsockname()[1]
        url = f"http://127.0.0.1:{puerto}"
        inicio = time.monotonic()
        with ClienteERP(url, conn=conn, max_intentos=2) as c:
            with pytest.raises(ErrorERP, match="ERP-RED") as e:
                c.estado()
            assert e.value.codigo == "ERP-NO-RESPONDE"
            mensaje = str(e.value)
            assert all(
                x in mensaje
                for x in (
                    url,
                    "make erp",
                    "make erp-fast",
                    "ALBERTITOS_ERP_URL",
                    "snapshot anterior",
                )
            )
            # En Windows, conectar a un puerto cerrado de localhost tarda ~1 s por intento (la pila
            # reintenta el SYN antes de dar "rechazada"); en Linux es inmediato. Lo que se prueba es
            # que no se cuelga, no los milisegundos.
            limite = 8 if sys.platform == "win32" else 2
            assert "\n" not in mensaje and time.monotonic() - inicio < limite
            assert c.consultas == 2 and c.reintentos == 1
    eventos = list(conn.execute("SELECT estado, error_codigo FROM eventos ORDER BY id"))
    assert [(fila["estado"], fila["error_codigo"]) for fila in eventos] == [
        ("retry", "ERP-RED"),
        ("error", "ERP-RED"),
    ]
    ruta = conn.execute("PRAGMA database_list").fetchone()["file"]
    lectura = db.conectar(ruta, solo_lectura=True)
    try:
        assert lectura.execute("SELECT count(*) FROM eventos").fetchone()[0] == 2
    finally:
        lectura.close()
