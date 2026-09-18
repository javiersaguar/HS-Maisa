"""Validador del JSONL de entrega: replica lo que hará el verificador privado, y algo más."""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from albertitos.core.contracts import Outcome


@dataclass
class InformeValidacion:
    ruta: str
    lote: int
    n_lineas: int = 0
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    distribucion: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errores

    def texto(self) -> str:
        cab = f"{'APTO' if self.ok else 'NO APTO'} · {self.ruta} · lote {self.lote} · {self.n_lineas} líneas · {self.distribucion}"
        cuerpo = [f"  ✗ {e}" for e in self.errores[:40]] + [f"  ! {a}" for a in self.avisos[:20]]
        if len(self.errores) > 40:
            cuerpo.append(f"  … y {len(self.errores) - 40} errores más")
        return "\n".join([cab, *cuerpo])


def listar_pdfs(directorio: Path) -> list[str]:
    """Nombres exactos de los PDF de un lote, en NFC (lo que el verificador espera como file_id)."""
    return sorted(
        unicodedata.normalize("NFC", p.name)
        for p in Path(directorio).iterdir()
        if p.suffix.lower() == ".pdf"
    )


def validar_jsonl(ruta: Path, esperados: list[str], lote: int) -> InformeValidacion:
    inf = InformeValidacion(ruta=str(ruta), lote=lote)
    ruta = Path(ruta)
    if not ruta.exists():
        inf.errores.append("el fichero no existe")
        return inf
    crudo = ruta.read_bytes()
    if crudo.startswith(b"\xef\xbb\xbf"):
        inf.errores.append("empieza con BOM UTF-8")
        crudo = crudo[3:]
    try:
        texto = crudo.decode("utf-8")
    except UnicodeDecodeError as e:
        inf.errores.append(f"no es UTF-8: {e}")
        return inf
    if "\r" in texto:
        inf.avisos.append("hay retornos de carro (CRLF); mejor LF")
    lineas = texto.split("\n")
    if lineas and lineas[-1] == "":
        lineas.pop()
    vistos: dict[str, int] = {}
    for i, linea in enumerate(lineas, 1):
        if not linea.strip():
            inf.errores.append(f"línea {i} vacía")
            continue
        try:
            obj = json.loads(linea)
        except json.JSONDecodeError as e:
            inf.errores.append(f"línea {i}: JSON inválido ({e.msg})")
            continue
        try:
            o = Outcome.model_validate(obj)
        except ValidationError as e:
            inf.errores.append(f"línea {i}: {e.errors()[0]['msg']} → {linea[:80]}")
            continue
        inf.n_lineas += 1
        if o.file_id in vistos:
            inf.errores.append(
                f"file_id duplicado {o.file_id!r} (líneas {vistos[o.file_id]} y {i})"
            )
        vistos[o.file_id] = i
        inf.distribucion[o.result.value] = inf.distribucion.get(o.result.value, 0) + 1
    esperados_set = set(esperados)
    faltan = sorted(esperados_set - vistos.keys())
    sobran = sorted(vistos.keys() - esperados_set)
    for f in faltan:
        inf.errores.append(f"falta {f!r}")
    for s in sobran:
        pista = ""
        nfd = unicodedata.normalize("NFD", s)
        if nfd != s and unicodedata.normalize("NFC", s) in esperados_set:
            pista = " (¿NFD? el nombre existe en NFC)"
        inf.errores.append(f"sobra {s!r}{pista}")
    if not esperados:
        inf.errores.append("no hay PDFs esperados: ¿directorio del lote vacío?")
    return inf
