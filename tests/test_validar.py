from pathlib import Path

from albertitos.pipeline.validar import listar_pdfs, validar_jsonl


def _lote(tmp_path: Path) -> Path:
    d = tmp_path / "facturas"
    d.mkdir()
    for n in ("a.pdf", "b.pdf", "FA-1_ofimática.pdf"):
        (d / n).write_bytes(b"%PDF")
    return d


def _jsonl(tmp_path: Path, contenido: str) -> Path:
    p = tmp_path / "outcomes.jsonl"
    p.write_bytes(contenido.encode("utf-8"))
    return p


def test_ok(tmp_path):
    esperados = listar_pdfs(_lote(tmp_path))
    assert esperados == ["FA-1_ofimática.pdf", "a.pdf", "b.pdf"]
    inf = validar_jsonl(
        _jsonl(
            tmp_path,
            '{"file_id":"a.pdf","result":"PAGAR"}\n{"file_id":"b.pdf","result":"ESCALAR"}\n{"file_id":"FA-1_ofimática.pdf","result":"NO_PAGAR"}\n',
        ),
        esperados,
        1,
    )
    assert inf.ok, inf.texto()
    assert inf.distribucion == {"PAGAR": 1, "ESCALAR": 1, "NO_PAGAR": 1}


def test_falta_sobra_duplicado_y_enum(tmp_path):
    esperados = listar_pdfs(_lote(tmp_path))
    inf = validar_jsonl(
        _jsonl(
            tmp_path,
            '{"file_id":"a.pdf","result":"PAGAR"}\n{"file_id":"a.pdf","result":"PAGAR"}\n{"file_id":"z.pdf","result":"PAGAR"}\n{"file_id":"b.pdf","result":"pagar"}\n',
        ),
        esperados,
        1,
    )
    texto = inf.texto()
    assert not inf.ok
    assert (
        "duplicado" in texto
        and "sobra 'z.pdf'" in texto
        and "falta 'FA-1_ofimática.pdf'" in texto
        and "falta 'b.pdf'" in texto
    )


def test_nfd_se_detecta_con_pista(tmp_path):
    esperados = listar_pdfs(_lote(tmp_path))
    nfd = "FA-1_ofimática.pdf"
    inf = validar_jsonl(
        _jsonl(
            tmp_path,
            '{"file_id":"a.pdf","result":"PAGAR"}\n{"file_id":"b.pdf","result":"PAGAR"}\n'
            + '{"file_id":"'
            + nfd
            + '","result":"PAGAR"}\n',
        ),
        esperados,
        1,
    )
    assert not inf.ok
    assert any("NFC" in e for e in inf.errores)


def test_bom_y_linea_vacia(tmp_path):
    esperados = listar_pdfs(_lote(tmp_path))
    inf = validar_jsonl(
        _jsonl(
            tmp_path,
            '﻿{"file_id":"a.pdf","result":"PAGAR"}\n\n{"file_id":"b.pdf","result":"PAGAR"}\n{"file_id":"FA-1_ofimática.pdf","result":"PAGAR"}\n',
        ),
        esperados,
        1,
    )
    assert any("BOM" in e for e in inf.errores) and any("vacía" in e for e in inf.errores)
