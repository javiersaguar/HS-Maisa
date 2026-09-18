"""Contra el bridge real (make erp-fast). Se saltan si no responde."""

import pytest

from albertitos.sources.erp import ClienteERP, ErrorERP

pytestmark = pytest.mark.erp


def test_descarga_completa_con_reintentos(erp_vivo, conn):
    c = ClienteERP(erp_vivo, conn=conn, rps=9)
    s = c.descargar_todo("test")
    est = c.estado()
    assert len(s.asientos) == int(est["asientos"])
    assert s.consultas >= 27  # 26 páginas + estado (+ login)
    assert s.reintentos >= 2  # ORA-00600 cada 10ª consulta autenticada
    a = next(iter(s.asientos.values()))
    assert a.importe_esperado.as_tuple().exponent == -2 and a.fecha_registro.year == 2026
    n_retry = conn.execute(
        "SELECT count(*) n FROM eventos WHERE estado='retry' AND error_codigo='ORA-00600'"
    ).fetchone()["n"]
    assert n_retry == s.reintentos


def test_token_caducado_se_renueva_solo(erp_vivo):
    c = ClienteERP(erp_vivo, rps=9)
    c.login()
    c.token = "token-invalido"
    c.usos = 0
    asientos, paginas, total = c.pagina(1)
    assert paginas >= 1 and len(asientos) == 20


def test_pagina_fuera_de_rango(erp_vivo):
    c = ClienteERP(erp_vivo, rps=9)
    with pytest.raises(ErrorERP) as e:
        c.pagina(999)
    assert e.value.codigo == "ERP-400"
