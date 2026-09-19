"""Busca formas obsoletas declaradas en CIFRAS.md; sólo informa, nunca corrige."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

OBJETIVOS = (
    "docs/plan/albertitos_plan.md",
    "docs/guion-defensa.md",
    "docs/agentes/KIT-DEFENSA.md",
    "docs/benchmark.md",
)


def cargar_reglas(catalogo: Path) -> list[dict]:
    texto = catalogo.read_text(encoding="utf-8")
    bloques = re.findall(r"<!-- cifras-obsoletas\s*\n(.*?)\n-->", texto, re.S)
    if len(bloques) != 1:
        raise ValueError("CIFRAS.md debe tener un único bloque <!-- cifras-obsoletas ... -->")
    reglas = json.loads(bloques[0])
    if not isinstance(reglas, list) or not reglas:
        raise ValueError("catálogo de formas obsoletas vacío o inválido")
    for r in reglas:
        if not isinstance(r, dict) or any(
            not isinstance(r.get(k), str) or not r[k].strip() for k in ("vigente", "fuente")
        ):
            raise ValueError("cada regla necesita vigente y fuente no vacías")
        if (
            not isinstance(r.get("formas"), list)
            or not r["formas"]
            or any(not isinstance(f, str) or not f.strip() for f in r["formas"])
        ):
            raise ValueError("cada regla necesita formas literales no vacías")
        for h in r.get("historicas", []):
            if not isinstance(h, dict) or any(
                not isinstance(h.get(k), str) or not h[k].strip() for k in ("fichero", "contiene")
            ):
                raise ValueError("cada excepción histórica necesita fichero y contiene no vacíos")
    return reglas


def es_historica(regla: dict, archivo: str, linea: str) -> bool:
    """Una mención revisada a mano que cuenta la cifra vieja COMO vieja (p. ej. "la que usábamos antes").

    Se reconoce por fichero y un trozo literal de la línea, no por número de línea: sobrevive a ediciones
    del documento, y si alguien reescribe esa frase, vuelve a saltar y hay que revisarla otra vez.
    """
    limpio = normalizar(linea)
    return any(
        h["fichero"] == archivo and normalizar(h["contiene"]) in limpio
        for h in regla.get("historicas", [])
    )


def normalizar(texto: str) -> str:
    # Tolera énfasis Markdown, punto decimal y espacios; no interpreta regex del catálogo.
    texto = re.sub(r"(?<=\d)\.(?=\d{1,2}(?!\d))", ",", texto)
    return " ".join(texto.replace("*", "").replace("`", "").casefold().split())


def comprobar(raiz: Path, catalogo: Path, archivos=OBJETIVOS) -> list[dict]:
    reglas = cargar_reglas(catalogo)
    hallazgos = []
    for archivo in archivos:
        for numero, linea in enumerate(
            (raiz / archivo).read_text(encoding="utf-8").splitlines(), 1
        ):
            limpio = normalizar(linea)
            for regla in reglas:
                for forma in regla["formas"]:
                    patron = r"(?<!\w)" + re.escape(normalizar(forma)) + r"(?!\w)"
                    if re.search(patron, limpio):
                        if es_historica(regla, str(archivo), linea):
                            break  # revisada: cuenta la cifra vieja como vieja
                        hallazgos.append(
                            {
                                "fichero": str(archivo),
                                "linea": numero,
                                "obsoleta": forma,
                                "vigente": regla["vigente"],
                                "fuente": regla["fuente"],
                            }
                        )
                        break  # una incidencia por regla y línea
    return hallazgos


def main(argv=None):
    # Windows sin PYTHONUTF8: la consola es cp1252 y «→», «€» o «ó» harían fallar el print.
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--catalogo", type=Path, default=Path("docs/CIFRAS.md"))
    args = ap.parse_args(argv)
    try:
        hallazgos = comprobar(args.raiz, args.raiz / args.catalogo)
    except (OSError, ValueError) as exc:
        print(f"ERROR: no se pudo comprobar el catálogo completo: {exc}", file=sys.stderr)
        return 2
    for h in hallazgos:
        print(
            f"{h['fichero']}:{h['linea']}: {h['obsoleta']} → {h['vigente']} · fuente: {h['fuente']}"
        )
    if hallazgos:
        print(
            f"{len(hallazgos)} coincidencia(s). Revisar el contexto; una mención histórica correcta se declara en `historicas` de CIFRAS.md. No se modifica ningún fichero."
        )
    else:
        print("OK: ninguna forma obsoleta del catálogo en los cuatro documentos.")
    return int(bool(hallazgos))


if __name__ == "__main__":
    sys.exit(main())
