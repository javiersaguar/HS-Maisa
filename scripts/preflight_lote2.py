"""Comprobación de 10 segundos ANTES de tocar el lote 2. Sólo lee, salvo --limpiar/--respaldar.

Por qué existe: el 18/09 llegamos a tener en la BD 10 ficheros de un lote 2 SIMULADO. Nadie lo vio
(`status` decía "{1: 500, 2: 10}", que parece correcto) y costó dos errores: `marcar_duplicados`
marcó como duplicados a los originales del lote 1, y `package` habría metido en la entrega ficheros
que no existen en la Caja → NO APTO.

Uso:
    uv run python scripts/preflight_lote2.py                 # sólo mira; 0 = puedes seguir
    uv run python scripts/preflight_lote2.py --respaldar     # además copia la BD (API de backup)
    uv run python scripts/preflight_lote2.py --limpiar       # además borra los ficheros fantasma
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import time
import urllib.request
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from albertitos.core import db  # noqa: E402
from albertitos.core.contracts import InvoiceFacts  # noqa: E402
from albertitos.core.versions import PROMPT_VERSION  # noqa: E402
from albertitos.sources import chaos, estado_bd  # noqa: E402

ROJO, AMBAR, VERDE = "ROJO", "ÁMBAR", "VERDE"

# Variables que cambian el comportamiento del pipeline y que alguien puede dejarse puestas tras un
# ensayo o una demo. La de abajo es la que más daño haría: con el umbral del breaker en 2, una pasada
# real se cortaría a los dos fallos y dejaría cientos de ficheros PENDIENTE sin que nadie lo note.
ENTORNO_VIGILADO = {
    "ALBERTITOS_BREAKER_FALLOS": "5",
    "ALBERTITOS_BREAKER_SEGUNDOS": "60",
    "ALBERTITOS_LLM_TIMEOUT_S": "60",
    "ALBERTITOS_LLM_TIMEOUT_VISION_S": "90",
    "ALBERTITOS_VISION_DOBLE": "1",
    "ALBERTITOS_RECONCILIAR_MAESTRO": "1",
    "ALBERTITOS_DIR_CAJA": "data/caja/facturas",
    "ALBERTITOS_DIR_LOTE2": "data/lote2/facturas",
}
MIN_LIBRE_GB = 0.5
ANTIGUEDAD_COPIA_H = 3


@dataclass
class Check:
    nombre: str
    nivel: str
    detalle: str
    arreglo: str = ""


def url_viva(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except Exception:
        return False


def respaldar(origen: Path, destino: Path) -> None:
    """Copia coherente con la API de backup de SQLite. Nunca `cp`: con el WAL a medias, una copia
    por fichero puede quedar inconsistente (ADR-0008)."""
    with (
        closing(sqlite3.connect(f"file:{origen}?mode=ro", uri=True)) as src,
        closing(sqlite3.connect(destino)) as dst,
    ):
        src.backup(dst)


def comprobar(args) -> list[Check]:
    checks: list[Check] = []
    ruta_db = Path(args.db)
    if not ruta_db.exists():
        return [
            Check("base de datos", ROJO, f"no existe {ruta_db}", "make db && uv run albertitos run")
        ]

    with closing(db.conectar(ruta_db, solo_lectura=True)) as conn:
        e = estado_bd.resumen_estado(conn, args.dir_lote1, args.dir_lote2)

    # 1. ficheros fantasma: lo que provocó el incidente
    if e.fantasmas:
        ids = [f for f, _ in e.fantasmas]
        patron = "L2-%" if all(f.startswith("L2-") for f in ids) else ids[0]
        checks.append(
            Check(
                "ficheros fantasma",
                ROJO,
                f"{len(ids)} en la BD que no están en su directorio: {ids[:5]}{' …' if len(ids) > 5 else ''}",
                f"uv run python scripts/preflight_lote2.py --limpiar   (o borra a mano los que casen con '{patron}')",
            )
        )
    else:
        checks.append(
            Check("ficheros fantasma", VERDE, "ninguno: la BD sólo tiene ficheros reales")
        )

    # 2. hechos huérfanos
    if e.huerfanos:
        checks.append(
            Check(
                "hechos huérfanos",
                ROJO,
                f"{len(e.huerfanos)} hechos sin fichero (borrado a medias)",
                "uv run python scripts/preflight_lote2.py --limpiar",
            )
        )
    else:
        checks.append(Check("hechos huérfanos", VERDE, "ninguno"))

    # 3. caos apagado (el fichero es por BD: <db>.chaos.json)
    os.environ.setdefault("ALBERTITOS_DB", str(ruta_db))
    modo = chaos.modo()
    checks.append(
        Check(
            "interruptor de caos",
            ROJO if modo else VERDE,
            f"modo {modo}" if modo else f"apagado ({chaos.ruta().name})",
            "uv run albertitos chaos --off" if modo else "",
        )
    )

    # 4. ERP vivo
    checks.append(
        Check("ERP v1", VERDE, f"responde en {args.erp_url}")
        if url_viva(f"{args.erp_url}/erp/estado")
        else Check(
            "ERP v1", ROJO, f"no responde en {args.erp_url}", "make erp-fast   (en otra terminal)"
        )
    )
    if args.erp_lote2:
        checks.append(
            Check("ERP lote 2", VERDE, f"responde en {args.erp_lote2}")
            if url_viva(f"{args.erp_lote2}/erp/estado")
            else Check(
                "ERP lote 2",
                ROJO,
                f"no responde en {args.erp_lote2}",
                "python3 data/caja/alberto_erp.py --rapido --puerto 8011 --lote2 data/lote2/erp_export_lote2.csv &",
            )
        )

    # 5. qué ERP se usaría sin --erp: si el último es un simulado, decidiríamos contra datos inventados
    if e.erp_en_uso is None:
        checks.append(
            Check("snapshot del ERP", ROJO, "no hay ninguno", "uv run albertitos erp pull --tag v1")
        )
    elif e.erp_en_uso != args.erp_esperado:
        checks.append(
            Check(
                "snapshot del ERP",
                ROJO,
                f"el más reciente es '{e.erp_en_uso}': `decide`/`run` SIN --erp lo usarían",
                f"uv run albertitos erp pull --tag {args.erp_esperado}   (o pasa siempre --erp {args.erp_esperado})",
            )
        )
    else:
        checks.append(Check("snapshot del ERP", VERDE, f"el más reciente es '{e.erp_en_uso}'"))

    # 6. espacio en disco
    libre_gb = shutil.disk_usage(ruta_db.parent if ruta_db.parent.exists() else ".").free / 1e9
    checks.append(
        Check(
            "espacio libre",
            VERDE if libre_gb >= MIN_LIBRE_GB else ROJO,
            f"{libre_gb:.1f} GB en {ruta_db.parent}/",
            ""
            if libre_gb >= MIN_LIBRE_GB
            else "libera espacio: make clean borra la BD y los outcomes (la caché del LLM se pierde)",
        )
    )

    # 7. copia de seguridad de la BD
    copia = ruta_db.with_suffix(ruta_db.suffix + ".bak")
    if args.respaldar:
        respaldar(ruta_db, copia)
    if copia.exists():
        horas = (time.time() - copia.stat().st_mtime) / 3600
        checks.append(
            Check(
                "copia de la BD",
                VERDE if horas <= ANTIGUEDAD_COPIA_H else AMBAR,
                f"{copia.name}, de hace {horas:.1f} h",
                ""
                if horas <= ANTIGUEDAD_COPIA_H
                else "uv run python scripts/preflight_lote2.py --respaldar",
            )
        )
    else:
        checks.append(
            Check(
                "copia de la BD",
                AMBAR,
                "no hay copia",
                "uv run python scripts/preflight_lote2.py --respaldar",
            )
        )

    # 8. el directorio del lote 2 debería estar vacío antes de descomprimir el material real
    dir2 = Path(args.dir_lote2)
    previos = sorted(p.name for p in dir2.glob("*.pdf")) if dir2.is_dir() else []
    checks.append(
        Check(
            "data/lote2/facturas",
            VERDE if not previos else AMBAR,
            "vacío o inexistente"
            if not previos
            else f"{len(previos)} PDF de un intento anterior: {previos[:3]}",
            "" if not previos else "si no es el material bueno, muévelo antes de descomprimir",
        )
    )

    # 9. el fixture que reimportan Miguel y Mónica tiene que ser exactamente el lote 1
    fixture = Path(args.fixture)
    with closing(db.conectar(ruta_db, solo_lectura=True)) as conn:
        del_lote1 = {
            str(r["file_id"]) for r in conn.execute("SELECT file_id FROM ficheros WHERE lote=1")
        }
    if not fixture.exists():
        checks.append(
            Check(
                "fixture de hechos",
                AMBAR,
                f"no existe {fixture}",
                "uv run albertitos hechos export",
            )
        )
    else:
        en_fixture = {
            json.loads(linea)["file_id"]
            for linea in fixture.read_text(encoding="utf-8").splitlines()
            if linea.strip()
        }
        sobran, faltan = en_fixture - del_lote1, del_lote1 - en_fixture
        checks.append(
            Check(
                "fixture de hechos",
                VERDE if not (sobran or faltan) else ROJO,
                f"{len(en_fixture)} hechos, coinciden con el lote 1"
                if not (sobran or faltan)
                else f"sobran {len(sobran)} y faltan {len(faltan)} respecto al lote 1 ({sorted(sobran)[:3]})",
                ""
                if not (sobran or faltan)
                else "uv run albertitos hechos export   (con la lista del lote 1)",
            )
        )

    # 10. variables de entorno de un ensayo anterior que cambiarían una pasada real
    torcidas = {
        nombre: os.environ[nombre]
        for nombre, defecto in ENTORNO_VIGILADO.items()
        if os.environ.get(nombre) not in (None, defecto)
    }
    if torcidas:
        checks.append(
            Check(
                "entorno",
                ROJO,
                "variables de un ensayo aún exportadas: "
                + ", ".join(f"{k}={v}" for k, v in torcidas.items()),
                "unset " + " ".join(torcidas) + "   (o abre una terminal nueva)",
            )
        )
    else:
        checks.append(Check("entorno", VERDE, "sin variables de ensayo exportadas"))

    # 11. la caché del LLM tiene que ser de la versión de prompt en uso: si no, releer las
    #     escaneadas son minutos de visión (pasó al subir PROMPT_VERSION a p-0.2)
    with closing(db.conectar(ruta_db, solo_lectura=True)) as conn:
        versiones = {
            str(r[0]).split("|")[1]: int(r[1])
            for r in conn.execute(
                "SELECT clave, count(*) FROM cache_llm GROUP BY substr(clave, 66, 5)"
            )
        }
    viejas = {v: n for v, n in versiones.items() if v != PROMPT_VERSION}
    if viejas:
        checks.append(
            Check(
                "caché del LLM",
                AMBAR,
                f"{sum(viejas.values())} lecturas de otra versión de prompt ({viejas}); la actual es {PROMPT_VERSION}",
                "si el prompt no cambió, re-etiqueta: UPDATE cache_llm SET clave = replace(clave, '|<vieja>|', '|"
                + PROMPT_VERSION
                + "|')",
            )
        )
    elif versiones:
        checks.append(
            Check(
                "caché del LLM",
                VERDE,
                f"{sum(versiones.values())} lecturas, todas de {PROMPT_VERSION}",
            )
        )

    # 12. los hechos del fixture tienen que ser los de la BD: Miguel y Mónica importan ese fichero
    if fixture.exists():
        with closing(db.conectar(ruta_db, solo_lectura=True)) as conn:
            en_bd = {
                str(r["file_id"]): str(r["hechos_hash"])
                for r in conn.execute(
                    """SELECT f.file_id, h.hechos_hash FROM hechos h
                       JOIN ficheros f ON f.sha256 = h.sha256 WHERE f.lote = 1"""
                )
            }
        distintos: list[str] = []
        ilegibles = 0
        for linea in fixture.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            try:
                hechos = InvoiceFacts.model_validate_json(linea)
            except ValidationError:
                ilegibles += 1  # un fixture a medias se avisa, no revienta el preflight
                continue
            if en_bd.get(hechos.file_id) not in (None, hechos.hash()):
                distintos.append(hechos.file_id)
        if ilegibles:
            distintos.append(f"(+{ilegibles} líneas ilegibles)")
        checks.append(
            Check(
                "fixture vs BD",
                VERDE if not distintos else AMBAR,
                "los hechos del fixture son los de la BD"
                if not distintos
                else f"{len(distintos)} hechos distintos de los de la BD ({distintos[:3]}): el fixture está sin reexportar",
                ""
                if not distintos
                else "uv run albertitos hechos export --salida data/fixtures/hechos_caja.jsonl",
            )
        )

    # resumen informativo al final
    checks.append(
        Check(
            "estado",
            VERDE,
            f"ficheros {e.ficheros_por_lote} · decisiones {e.decisiones_por_resultado} · "
            f"métodos {e.hechos_por_metodo} · caché {e.lecturas_en_cache}",
        )
    )
    return checks


def limpiar(ruta_db: Path, dir_lote1: str, dir_lote2: str) -> tuple[int, int]:
    """Borra ficheros fantasma (y lo que cuelga de ellos) y hechos huérfanos. Sólo con --limpiar."""
    with closing(db.conectar(ruta_db)) as conn:
        fantasmas = [f for f, _ in estado_bd.ficheros_fantasma(conn, dir_lote1, dir_lote2)]
        for file_id in fantasmas:
            sha = conn.execute("SELECT sha256 FROM ficheros WHERE file_id=?", (file_id,)).fetchone()
            conn.execute("DELETE FROM eventos WHERE file_id=?", (file_id,))
            conn.execute("DELETE FROM decisiones WHERE file_id=?", (file_id,))
            if sha:
                conn.execute("DELETE FROM hechos WHERE sha256=?", (sha[0],))
            conn.execute("DELETE FROM ficheros WHERE file_id=?", (file_id,))
        huerfanos = estado_bd.hechos_huerfanos(conn)
        for sha in huerfanos:
            conn.execute("DELETE FROM hechos WHERE sha256=?", (sha,))
        conn.commit()
    return len(fantasmas), len(huerfanos)


def main() -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--db", default=os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"))
    ap.add_argument("--dir-lote1", default="data/caja/facturas")
    ap.add_argument(
        "--dir-lote2", default=os.environ.get("ALBERTITOS_DIR_LOTE2", "data/lote2/facturas")
    )
    ap.add_argument("--fixture", default="data/fixtures/hechos_caja.jsonl")
    ap.add_argument(
        "--erp-url", default=os.environ.get("ALBERTITOS_ERP_URL", "http://127.0.0.1:8009")
    )
    ap.add_argument("--erp-lote2", default="", help="url del segundo bridge, si ya está arrancado")
    ap.add_argument(
        "--erp-esperado", default="v1", help="snapshot que deben usar run/decide sin --erp"
    )
    ap.add_argument(
        "--limpiar", action="store_true", help="borra ficheros fantasma y hechos huérfanos"
    )
    ap.add_argument(
        "--respaldar", action="store_true", help="copia la BD a <db>.bak con la API de backup"
    )
    args = ap.parse_args()

    if args.limpiar:
        n_f, n_h = limpiar(Path(args.db), args.dir_lote1, args.dir_lote2)
        print(f"limpieza: {n_f} ficheros fantasma y {n_h} hechos huérfanos borrados\n")

    checks = comprobar(args)
    ancho = max(len(c.nombre) for c in checks)
    for c in checks:
        print(f"  [{c.nivel:^5}] {c.nombre:<{ancho}}  {c.detalle}")
        if c.arreglo:
            print(f"          {'':<{ancho}}  → {c.arreglo}")
    rojos = [c for c in checks if c.nivel == ROJO]
    ambares = [c for c in checks if c.nivel == AMBAR]
    print()
    if rojos:
        print(f"NO sigas con el lote 2: {len(rojos)} comprobación(es) en rojo.")
        return 1
    print(
        f"Puedes seguir con el lote 2. {len(ambares)} aviso(s) en ámbar."
        if ambares
        else "Todo en verde: puedes seguir con el lote 2."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
