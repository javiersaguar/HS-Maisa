"""Enlaces relativos de los .md: cuáles apuntan a un fichero que no existe.

Recorre docs/ y la raíz (CLAUDE.md, README.md). Ignora http(s)://, mailto: y los que están
dentro de bloques ```. Sale 1 si hay rotos. Sólo lee.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ENLACE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")
IGNORAR = ("http://", "https://", "mailto:")


def ficheros_md(raiz: Path) -> list[Path]:
    raiz = raiz.resolve()
    out = sorted((raiz / "docs").rglob("*.md")) if (raiz / "docs").is_dir() else []
    for nombre in ("CLAUDE.md", "README.md"):
        p = raiz / nombre
        if p.is_file():
            out.append(p)
    return out


def destinos(linea: str) -> list[str]:
    """Destinos de `[texto](ruta)` en una línea fuera de un bloque de código."""
    encontrados = []
    for m in ENLACE.finditer(linea):
        dest = m.group(2).strip().split()[0]  # descarta el "título" markdown
        dest = dest.strip("<>")
        if not dest or dest.startswith(("#", *IGNORAR)):
            continue
        if not _parece_ruta(dest):
            continue
        encontrados.append(dest)
    return encontrados


def _parece_ruta(dest: str) -> bool:
    """Descarta `rutas()["/bonus/x"](conn, …)`, que el markdown toma por enlace."""
    ruta = dest.split("#", 1)[0]
    if not ruta or any(c in ruta for c in ",;{}=\"'"):
        return False
    return "/" in ruta or Path(ruta).suffix in {
        ".md",
        ".py",
        ".json",
        ".txt",
        ".csv",
        ".html",
        ".ts",
        ".tsx",
        ".sh",
        ".pdf",
    }


def lineas_fuera_de_codigo(texto: str):
    dentro = False
    for n, linea in enumerate(texto.splitlines(), 1):
        if linea.lstrip().startswith("```"):
            dentro = not dentro
            continue
        if not dentro:
            yield n, linea


def comprobar(raiz: Path) -> list[tuple[str, int, str]]:
    """Lista (fichero, línea, destino) de enlaces relativos cuyo fichero no existe."""
    raiz = raiz.resolve()
    rotos: list[tuple[str, int, str]] = []
    for md in ficheros_md(raiz):
        texto = md.read_text(encoding="utf-8")
        rel_md = md.relative_to(raiz).as_posix()
        for n, linea in lineas_fuera_de_codigo(texto):
            for dest in destinos(linea):
                ruta = dest.split("#", 1)[0]
                if not ruta:
                    continue
                candidato = (md.parent / ruta).resolve()
                if not candidato.exists():
                    rotos.append((rel_md, n, dest))
    return rotos


def main(argv=None) -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args(argv)
    rotos = comprobar(args.raiz)
    for fichero, linea, dest in rotos:
        print(f"{fichero}:{linea} → {dest}")
    if rotos:
        print(f"{len(rotos)} enlace(s) roto(s). No se modifica ningún fichero.")
        return 1
    print("OK: ningún enlace relativo roto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
