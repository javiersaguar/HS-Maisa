"""Fixtures compartidas. Los tests que necesitan el ERP se saltan solos si no responde."""

from __future__ import annotations

import os
import urllib.request
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from albertitos.core import db
from albertitos.core.contracts import ErpEntry, ErpSnapshot, MasterSnapshot, Pedido, Proveedor

CAJA = Path("data/caja")


@pytest.fixture
def conn(tmp_path):
    c = db.conectar(tmp_path / "test.db")
    db.init_schema(c)
    yield c
    c.close()


@pytest.fixture(scope="session")
def erp_vivo() -> str:
    url = os.environ.get("ALBERTITOS_ERP_URL", "http://127.0.0.1:8009")
    try:
        urllib.request.urlopen(f"{url}/erp/estado", timeout=1.5)
    except Exception:
        pytest.skip("el ERP no responde: arranca `make erp-fast` en otra terminal")
    return url


@pytest.fixture(scope="session")
def caja() -> Path:
    if not (CAJA / "facturas").exists():
        pytest.skip("no está data/caja/facturas")
    return CAJA


@pytest.fixture
def maestro() -> MasterSnapshot:
    p1 = Proveedor(
        id="P001",
        razon_social="Suministros Levante S.L.",
        nif="B46102331",
        iban="ES2100491500051234567890",
        condiciones_dias=60,
    )
    p2 = Proveedor(
        id="P002",
        razon_social="Transportes Guadaira S.A.",
        nif="A41220987",
        iban="ES7621000813610123456789",
        condiciones_dias=45,
    )
    return MasterSnapshot(
        version="m-test",
        origen="test",
        proveedores={p1.id: p1, p2.id: p2},
        pedidos={
            "PO-2026-0001": Pedido(
                pedido="PO-2026-0001",
                proveedor_id="P001",
                nif="B46102331",
                importe_total=Decimal("3012.89"),
                estado="ABIERTO",
                fecha_pedido=date(2026, 1, 2),
            ),
            "PO-2026-0002": Pedido(
                pedido="PO-2026-0002",
                proveedor_id="P002",
                nif="A41220987",
                importe_total=Decimal("943.80"),
                estado="ABIERTO",
                fecha_pedido=date(2026, 3, 1),
            ),
            "PO-2026-0009": Pedido(
                pedido="PO-2026-0009",
                proveedor_id="P001",
                nif="B46102331",
                importe_total=Decimal("100.00"),
                estado="ABIERTO",
            ),
        },
        cargado_en=datetime.now(UTC),
    )


@pytest.fixture
def erp() -> ErpSnapshot:
    a = {
        "AS-00001": ErpEntry(
            asiento_id="AS-00001",
            fecha_registro=date(2026, 1, 5),
            proveedor_id="P001",
            nif="B46102331",
            pedido="PO-2026-0001",
            importe_esperado=Decimal("3012.89"),
            estado="PENDIENTE",
        ),
        "AS-00002": ErpEntry(
            asiento_id="AS-00002",
            fecha_registro=date(2026, 3, 2),
            proveedor_id="P002",
            nif="A41220987",
            pedido="PO-2026-0002",
            importe_esperado=Decimal("943.80"),
            estado="PENDIENTE",
        ),
        "AS-00009": ErpEntry(
            asiento_id="AS-00009",
            fecha_registro=date(2026, 2, 2),
            proveedor_id="P001",
            nif="B46102331",
            pedido="PO-2026-0009",
            importe_esperado=Decimal("100.00"),
            estado="PAGADA",
        ),
    }
    return ErpSnapshot(version="e-test", asientos=a, descargado_en=datetime.now(UTC))
