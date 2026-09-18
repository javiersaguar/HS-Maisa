"""`caja manifest` / `caja verify` por lote: el paso 1 del sábado 18:00 (40 PDFs, NFC, hashes)."""

import unicodedata

from typer.testing import CliRunner

from albertitos import cli

runner = CliRunner()


def test_manifiesto_y_verificacion_del_lote_2(tmp_path, monkeypatch):
    raiz, manifiesto = tmp_path / "lote2", tmp_path / "lote2.sha256"
    (raiz / "facturas").mkdir(parents=True)
    for nombre in ("L2-0001_ofimática.pdf", "L2-0002.pdf"):
        (raiz / "facturas" / nombre).write_bytes(b"%PDF-1.4 " + nombre.encode())
    (raiz / "erp_export_lote2.csv").write_text("asiento;pedido\n", encoding="utf-8")
    monkeypatch.setattr(cli, "RAICES", {**cli.RAICES, 2: raiz})
    monkeypatch.setattr(cli, "MANIFIESTOS", {**cli.MANIFIESTOS, 2: manifiesto})

    def verificar(*args: str) -> tuple[int, str]:
        r = runner.invoke(cli.app, ["caja", "verify", "--lote", "2", *args])
        return r.exit_code, " ".join(r.output.split())  # rich parte las líneas a 80 columnas

    codigo, salida = verificar("--esperados", "2")
    assert codigo == 0 and "caja manifest --lote 2" in salida  # aún sin manifiesto: aviso

    assert runner.invoke(cli.app, ["caja", "manifest", "--lote", "2"]).exit_code == 0
    assert len(manifiesto.read_text(encoding="utf-8").splitlines()) == 3  # también el CSV del ERP
    assert verificar("--esperados", "2")[0] == 0
    codigo, salida = verificar()  # por defecto se esperan 40
    assert codigo == 1 and "se esperaban 40" in salida

    (raiz / "facturas" / "L2-0002.pdf").write_bytes(b"otro")  # un byte cambiado
    (raiz / "facturas" / "L2-0001_ofimática.pdf").unlink()  # uno que no se descomprimió
    otra = tmp_path / "otra"
    otra.mkdir()
    (otra / unicodedata.normalize("NFD", "L2-0003_ofimática.pdf")).write_bytes(b"x")
    codigo, salida = verificar("--esperados", "2")
    assert codigo == 1
    assert "hash distinto" in salida and "faltan 1 PDFs" in salida

    codigo, salida = verificar("--dir", str(otra))  # --dir: otra carpeta, mismo manifiesto
    assert codigo == 1
    assert "NFD" in salida and "no está en" in salida
