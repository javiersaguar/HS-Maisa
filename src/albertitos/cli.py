"""CLI de Albertitos. Cada verbo es una etapa o una operación; la lógica vive en los módulos."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unicodedata
from datetime import date
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich import print as rprint
from rich.table import Table

load_dotenv()

app = typer.Typer(
    no_args_is_help=True, help="Albertitos · el LLM extrae, la norma decide, la BD recuerda."
)
db_app = typer.Typer(help="Base de datos SQLite")
caja_app = typer.Typer(help="La Caja de Alberto (datos de entrada)")
erp_app = typer.Typer(help="ERP 2009: snapshots")
app.add_typer(db_app, name="db")
app.add_typer(caja_app, name="caja")
app.add_typer(erp_app, name="erp")

CAJA = Path("data/caja")
LOTE2 = Path("data/lote2")
MANIFIESTO = Path("data/caja.sha256")
ENTREGA = Path("dist/entrega")


def _conn(solo_lectura: bool = False):
    from albertitos.core import db

    ruta = Path(os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"))
    if solo_lectura and not ruta.exists():
        rprint(
            f"[red]No existe {ruta}.[/red] Crea la BD con `make db` e ingiere con `albertitos ingest`."
        )
        raise typer.Exit(1)
    conn = db.conectar(ruta, solo_lectura=solo_lectura)
    if not solo_lectura:
        db.init_schema(conn)
    return conn


def _fecha_corte(valor: str | None) -> date:
    crudo = valor or os.environ.get("ALBERTITOS_FECHA_CORTE")
    if not crudo:
        rprint(
            "[red]Falta la fecha de corte[/red]: --fecha-corte AAAA-MM-DD o ALBERTITOS_FECHA_CORTE en .env. Nunca date.today()."
        )
        raise typer.Exit(2)
    return date.fromisoformat(crudo)


# ----------------------------------------------------------------------------- db / caja


@db_app.command("init")
def db_init() -> None:
    """Crea o actualiza el esquema (idempotente)."""
    conn = _conn()
    rprint(f"[green]esquema OK[/green] en {os.environ.get('ALBERTITOS_DB', 'dist/albertitos.db')}")
    conn.close()


@caja_app.command("verify")
def caja_verify(lote: int = typer.Option(1, help="1 = Caja, 2 = lote sorpresa")) -> None:
    """Comprueba nº de PDFs, nombres en NFC y (lote 1) hashes frente a data/caja.sha256."""
    directorio = (CAJA if lote == 1 else LOTE2) / "facturas"
    if not directorio.exists():
        rprint(f"[red]{directorio} no existe[/red]")
        raise typer.Exit(1)
    pdfs = sorted(p for p in directorio.iterdir() if p.suffix.lower() == ".pdf")
    problemas: list[str] = []
    for p in pdfs:
        if not unicodedata.is_normalized("NFC", p.name):
            problemas.append(
                f"nombre en NFD (no NFC): {p.name!r} → renómbralo; el file_id debe ser NFC"
            )
    esperado = 500 if lote == 1 else None
    if esperado and len(pdfs) != esperado:
        problemas.append(f"hay {len(pdfs)} PDFs, se esperaban {esperado}")
    if lote == 1 and MANIFIESTO.exists():
        manifiesto = dict(
            linea.split("  ", 1)[::-1]
            for linea in MANIFIESTO.read_text().splitlines()
            if "  " in linea
        )
        for p in pdfs:
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            rel = f"data/caja/facturas/{unicodedata.normalize('NFC', p.name)}"
            if rel not in manifiesto:
                problemas.append(f"no está en el manifiesto: {rel}")
            elif manifiesto[rel] != h:
                problemas.append(
                    f"hash distinto: {rel} (¿la Caja oficial de las 21:00 cambió este PDF?)"
                )
    elif lote == 1:
        problemas.append(
            "no hay data/caja.sha256: genera el manifiesto con `albertitos caja manifest` desde la Caja oficial"
        )
    con_tilde = sum(1 for p in pdfs if any(ord(c) > 127 for c in p.name))
    rprint(f"{len(pdfs)} PDFs en {directorio} · {con_tilde} con caracteres no ASCII")
    for x in problemas:
        rprint(f"  [red]✗[/red] {x}")
    if problemas:
        raise typer.Exit(1)
    rprint("[green]Caja OK[/green]")


@caja_app.command("manifest")
def caja_manifest() -> None:
    """Escribe data/caja.sha256 con el hash de cada fichero de la Caja (hazlo sólo desde la Caja oficial)."""
    lineas = []
    for p in sorted(CAJA.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            rel = unicodedata.normalize("NFC", str(p).replace(os.sep, "/"))
            lineas.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}")
    MANIFIESTO.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    rprint(f"[green]{len(lineas)} hashes[/green] en {MANIFIESTO}")


# ----------------------------------------------------------------------------- etapas


@app.command()
def ingest(directorio: Path = typer.Option(CAJA / "facturas", "--dir"), lote: int = 1) -> None:
    """PDFs → tabla ficheros (sha256, páginas, ¿tiene texto?). Idempotente."""
    from albertitos.pipeline import etapas

    n = etapas.ingest(_conn(), directorio, lote)
    rprint(f"[green]{n} ficheros[/green] ingeridos de {directorio} (lote {lote})")


@app.command()
def extract(
    solo_pendientes: bool = True,
    fixture: Path | None = typer.Option(None, help="lista de file_id (uno por línea)"),
) -> None:
    """PDF → hechos (plantilla o LLM). Pendiente: Alfonso."""
    from albertitos.pipeline import etapas

    try:
        n = etapas.extract(_conn(), solo_pendientes=solo_pendientes, fixture=fixture)
    except NotImplementedError as e:
        rprint(f"[yellow]{e}[/yellow]")
        raise typer.Exit(3) from None
    rprint(f"[green]{n} ficheros[/green] extraídos")


@app.command()
def maestro(ruta: Path = CAJA / "FINAL_v7_DEFINITIVO_ahorasi.xlsx") -> None:
    """Carga el Excel limpio como snapshot 'maestro' versionado por contenido."""
    from albertitos.sources import excel, snapshot

    m = excel.cargar_maestro(ruta)
    snapshot.guardar_maestro(_conn(), m)
    rprint(
        f"[green]maestro {m.version}[/green]: {len(m.proveedores)} proveedores · {len(m.pedidos)} pedidos"
    )
    for a in m.avisos_calidad:
        rprint(f"  ! {a}")


@erp_app.command("pull")
def erp_pull(tag: str = typer.Option("v1", help="v1 = viernes, v2 = tras el lote 2")) -> None:
    """Descarga completa del bridge (26 páginas, reintentos, renovación de token) → snapshot 'erp' <tag>."""
    from albertitos.sources import erp, snapshot

    conn = _conn()
    cliente = erp.ClienteERP(conn=conn)
    s = cliente.descargar_todo(tag)
    snapshot.guardar_erp(conn, s)
    rprint(
        f"[green]erp {s.version}[/green]: {len(s.asientos)} asientos · {s.consultas} consultas · {s.reintentos} reintentos · lote2={s.lote2_cargado}"
    )


@erp_app.command("diff")
def erp_diff(a: str, b: str) -> None:
    """Qué cambió entre dos snapshots del ERP (nuevos, cambiados, eliminados)."""
    from albertitos.sources import snapshot

    conn = _conn(solo_lectura=True)
    d = snapshot.diff_erp(snapshot.cargar_erp_bd(conn, a), snapshot.cargar_erp_bd(conn, b))
    rprint(json.dumps(d, ensure_ascii=False, indent=1, default=str))


@app.command()
def decide(norma: str = "v3", fecha_corte: str | None = None, erp: str | None = None) -> None:
    """Aplica la norma a todos los ficheros con hechos (usa el último maestro y el ERP indicado o el último)."""
    from albertitos.pipeline import etapas
    from albertitos.sources import snapshot

    conn = _conn()
    m = snapshot.cargar_maestro_bd(conn)
    e = snapshot.cargar_erp_bd(conn, erp)
    n = etapas.decide(
        conn, norma_version=norma, fecha_corte=_fecha_corte(fecha_corte), maestro=m, erp=e
    )
    rprint(f"[green]{n} decisiones[/green] con norma {norma}, maestro {m.version}, erp {e.version}")


@app.command()
def reprocess(
    impacted: bool = True,
    norma: str = "v3",
    fecha_corte: str | None = None,
    erp: str | None = None,
    lote: int | None = None,
) -> None:
    """Recalcula sólo lo impactado por un cambio de norma/maestro/ERP/hechos y muestra el diff."""
    from albertitos.core.versions import EXTRACTOR_VERSION
    from albertitos.pipeline import etapas, linaje
    from albertitos.sources import snapshot

    conn = _conn()
    m = snapshot.cargar_maestro_bd(conn)
    e = snapshot.cargar_erp_bd(conn, erp)
    objetivo = linaje.impactados(
        conn,
        norma_version=norma,
        maestro_version=m.version,
        erp_version=e.version,
        extractor_version=EXTRACTOR_VERSION,
        lote=lote,
    )
    total = conn.execute("SELECT count(*) n FROM ficheros").fetchone()["n"]
    rprint(f"impactados: [bold]{len(objetivo)}[/bold] de {total}")
    n = etapas.decide(
        conn,
        norma_version=norma,
        fecha_corte=_fecha_corte(fecha_corte),
        maestro=m,
        erp=e,
        solo=objetivo,
    )
    cambios = linaje.diff_decisiones(conn)
    rprint(f"[green]{n} recalculadas[/green] · {len(cambios)} cambian de resultado")
    for c in cambios[:30]:
        rprint(f"  {c['file_id']}: {c['antes']} → {c['despues']}")


@app.command()
def run(norma: str = "v3", fecha_corte: str | None = None) -> None:
    """ingest → maestro → erp pull (si no hay) → extract → duplicados → decide → package."""
    from albertitos.pipeline import etapas, package
    from albertitos.sources import excel, snapshot

    conn = _conn()
    etapas.ingest(conn, CAJA / "facturas", 1)
    if (LOTE2 / "facturas").exists():
        etapas.ingest(conn, LOTE2 / "facturas", 2)
    m = excel.cargar_maestro(CAJA / "FINAL_v7_DEFINITIVO_ahorasi.xlsx")
    snapshot.guardar_maestro(conn, m)
    try:
        e = snapshot.cargar_erp_bd(conn, None)
    except LookupError:
        from albertitos.sources import erp as erp_mod

        e = erp_mod.ClienteERP(conn=conn).descargar_todo("v1")
        snapshot.guardar_erp(conn, e)
    try:
        etapas.extract(conn)
    except NotImplementedError as ex:
        rprint(f"[yellow]{ex}[/yellow]")
        raise typer.Exit(3) from None
    etapas.marcar_duplicados(conn)
    etapas.decide(
        conn, norma_version=norma, fecha_corte=_fecha_corte(fecha_corte), maestro=m, erp=e
    )
    for ruta, inf in package.empaquetar(conn, ENTREGA, CAJA, LOTE2):
        rprint(inf.texto(), "→", ruta)


# ----------------------------------------------------------------------------- operación


@app.command()
def status() -> None:
    """Estado por lote, resultado y etapa; pendientes."""
    from albertitos.core import db

    r = db.resumen(_conn(solo_lectura=True))
    rprint(
        f"ficheros por lote: {r['ficheros']} · decisiones vigentes: {r['decisiones']} · caché LLM: {r['cache_llm']}"
    )
    t = Table("etapa", "estado", "n", "lat media ms", "EUR", "reintentos")
    for e in r["eventos"]:
        t.add_row(
            e["etapa"],
            e["estado"],
            str(e["n"]),
            str(e["lat_media_ms"]),
            str(e["coste_eur"]),
            str(e["reintentos"]),
        )
    rprint(t)
    p = r["pendientes"]
    rprint(
        f"sin decisión vigente: {len(p)}"
        + (f" → {p[:10]}{' …' if len(p) > 10 else ''}" if p else "")
    )


@app.command()
def trace(file_id: str) -> None:
    """Todo lo que sabemos de un fichero: hechos, decisión(es), eventos."""
    from albertitos.core import db

    t = db.traza(_conn(solo_lectura=True), unicodedata.normalize("NFC", file_id))
    if not t["fichero"]:
        rprint(f"[red]{file_id} no está en la BD[/red] (¿ingest? ¿nombre exacto?)")
        raise typer.Exit(1)
    rprint(json.dumps(t, ensure_ascii=False, indent=1, default=str))


@app.command()
def validate(ruta: Path, lote: int = 1) -> None:
    """Valida un JSONL de entrega contra los PDFs reales del lote."""
    from albertitos.pipeline.validar import listar_pdfs, validar_jsonl

    directorio = (CAJA if lote == 1 else LOTE2) / "facturas"
    inf = validar_jsonl(ruta, listar_pdfs(directorio) if directorio.exists() else [], lote)
    rprint(inf.texto())
    raise typer.Exit(0 if inf.ok else 1)


@app.command()
def package(con_traza: bool = False, salida: Path = ENTREGA) -> None:
    """BD → dist/entrega/outcomes*.jsonl, validados. Se niega si falta alguna decisión."""
    from albertitos.pipeline import package as pk

    try:
        for ruta, inf in pk.empaquetar(
            _conn(solo_lectura=True), salida, CAJA, LOTE2, con_traza=con_traza
        ):
            rprint(inf.texto(), "→", ruta)
    except pk.EntregaInvalida as e:
        rprint(f"[red]NO se escribe la entrega:[/red]\n{e}")
        raise typer.Exit(1) from None


@app.command()
def bench() -> None:
    """Cifras medidas desde el log de eventos (para docs/benchmark.md)."""
    from albertitos.pipeline import bench as b

    print(b.texto(b.medir(_conn(solo_lectura=True))))


@app.command()
def chaos(
    llm_down: bool = False, llm_429: bool = False, llm_invalid: bool = False, off: bool = False
) -> None:
    """Simula fallos del proveedor de LLM (lo lee extract/llm.py)."""
    from albertitos.sources import chaos as ch

    if off:
        ch.desactivar()
    elif llm_down:
        ch.activar("llm_down")
    elif llm_429:
        ch.activar("llm_429")
    elif llm_invalid:
        ch.activar("llm_invalid")
    rprint(f"modo caos: {ch.modo() or 'ninguno'}")


if __name__ == "__main__":  # pragma: no cover
    sys.exit(app())
