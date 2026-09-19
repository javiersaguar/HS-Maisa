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

# En Windows la consola va en cp1252: sin esto, una tilde, una → o un ✗ tumban la CLI (también --help).
for _flujo in (sys.stdout, sys.stderr):
    if hasattr(_flujo, "reconfigure") and (_flujo.encoding or "").lower() not in ("utf-8", "utf8"):
        _flujo.reconfigure(encoding="utf-8", errors="replace")

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
RAICES = {1: CAJA, 2: LOTE2}
MANIFIESTOS = {1: MANIFIESTO, 2: Path("data/lote2.sha256")}
ESPERADOS = {1: 500, 2: 40}


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


AYUDA_SIN_AUDITORIA = "entrega sin la auditoría de entrega (queda 'no ejecutada' en el evento emit)"
AYUDA_ACEPTAR_ROJO = (
    "MOTIVO: entrega aunque la auditoría salga ROJA (nunca si falla o si el JSONL es inválido); "
    "el motivo queda en el evento emit AUDITORIA-ROJA-ACEPTADA"
)


def _aceptar_rojo(motivo: str | None) -> str | None:
    if motivo is not None and not motivo.strip():
        rprint('[red]--aceptar-rojo exige un motivo[/red]: --aceptar-rojo "<por qué>"')
        raise typer.Exit(2)
    return motivo


def _auditor(sin_auditoria: bool):
    """La auditoría de entrega si existe y no se ha saltado a mano; dice en voz alta si no corre."""
    from albertitos.pipeline import package as pk

    if sin_auditoria:
        rprint("[yellow]auditoría de entrega SALTADA a mano (--sin-auditoria)[/yellow]")
        return None
    auditar = pk.auditor_de_entrega()
    if auditar is None:
        rprint(
            "[yellow]auditoría de entrega no disponible todavía "
            "(falta albertitos.pipeline.auditoria.auditar, E2): sólo se valida el JSONL[/yellow]"
        )
    return auditar


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
def caja_verify(
    lote: int = typer.Option(1, help="1 = Caja, 2 = lote sorpresa"),
    carpeta: Path | None = typer.Option(
        None, "--dir", help="carpeta de PDFs a comprobar (por defecto data/caja|lote2/facturas)"
    ),
    esperados: int | None = typer.Option(
        None, help="nº de PDFs esperado (por defecto 500 | 40; con --dir, sin comprobar)"
    ),
) -> None:
    """Comprueba nº de PDFs, nombres en NFC y hashes frente al manifiesto del lote
    (data/caja.sha256 | data/lote2.sha256), comparando por nombre de fichero."""
    directorio = carpeta or RAICES[lote] / "facturas"
    if not directorio.exists():
        rprint(f"[red]{directorio} no existe[/red]")
        raise typer.Exit(1)
    pdfs = sorted(p for p in directorio.iterdir() if p.suffix.lower() == ".pdf")
    problemas: list[str] = []
    notas: list[str] = []
    for p in pdfs:
        if not unicodedata.is_normalized("NFC", p.name):
            problemas.append(
                f"nombre en NFD (no NFC): {p.name!r} → renómbralo; el file_id debe ser NFC"
            )
    esperado = esperados if esperados is not None else (None if carpeta else ESPERADOS[lote])
    if esperado and len(pdfs) != esperado:
        problemas.append(f"hay {len(pdfs)} PDFs, se esperaban {esperado}")
    ruta_manifiesto = MANIFIESTOS[lote]
    if ruta_manifiesto.exists():
        manifiesto = {  # nombre NFC del PDF → sha256, sólo lo que cuelga de facturas/
            ruta.rsplit("/", 1)[-1]: h
            for h, ruta in (
                linea.split("  ", 1)
                for linea in ruta_manifiesto.read_text(encoding="utf-8").splitlines()
                if "  " in linea
            )
            if "/facturas/" in ruta
        }
        vistos = set()
        for p in pdfs:
            nombre = unicodedata.normalize("NFC", p.name)
            vistos.add(nombre)
            if nombre not in manifiesto:
                problemas.append(f"no está en {ruta_manifiesto}: {nombre}")
            elif manifiesto[nombre] != hashlib.sha256(p.read_bytes()).hexdigest():
                problemas.append(f"hash distinto de {ruta_manifiesto}: {nombre}")
        faltan = sorted(set(manifiesto) - vistos)
        if faltan:
            problemas.append(
                f"faltan {len(faltan)} PDFs del manifiesto: {faltan[:5]}{' …' if len(faltan) > 5 else ''}"
            )
    elif lote == 1:
        problemas.append(
            "no hay data/caja.sha256: genera el manifiesto con `albertitos caja manifest` desde la Caja oficial"
        )
    else:
        notas.append(
            f"sin {ruta_manifiesto}: tras descomprimir el lote real, `albertitos caja manifest --lote {lote}`"
        )
    con_tilde = sum(1 for p in pdfs if any(ord(c) > 127 for c in p.name))
    rprint(f"{len(pdfs)} PDFs en {directorio} · {con_tilde} con caracteres no ASCII")
    for x in notas:
        rprint(f"  [yellow]·[/yellow] {x}")
    for x in problemas:
        rprint(f"  [red]✗[/red] {x}")
    if problemas:
        raise typer.Exit(1)
    rprint(f"[green]Lote {lote} OK[/green]")


@caja_app.command("manifest")
def caja_manifest(lote: int = typer.Option(1, help="1 = Caja, 2 = lote sorpresa")) -> None:
    """Escribe el manifiesto del lote (data/caja.sha256 | data/lote2.sha256) con el hash de cada
    fichero. Hazlo sólo desde el zip oficial, recién descomprimido."""
    raiz, destino = RAICES[lote], MANIFIESTOS[lote]
    if not raiz.exists():
        rprint(f"[red]{raiz} no existe[/red]")
        raise typer.Exit(1)
    lineas = []
    for p in sorted(raiz.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            rel = unicodedata.normalize("NFC", str(p).replace(os.sep, "/"))
            lineas.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}")
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    rprint(f"[green]{len(lineas)} hashes[/green] en {destino}")


# ----------------------------------------------------------------------------- etapas


@app.command()
def ingest(directorio: Path = typer.Option(CAJA / "facturas", "--dir"), lote: int = 1) -> None:
    """PDFs → tabla ficheros (sha256, páginas, ¿tiene texto?). Idempotente."""
    from albertitos.pipeline import etapas

    n = etapas.ingest(_conn(), directorio, lote)
    rprint(f"[green]{n} ficheros nuevos o cambiados[/green] en {directorio} (lote {lote})")


@app.command()
def extract(
    solo_pendientes: bool = True,
    fixture: Path | None = typer.Option(None, help="lista de file_id (uno por línea)"),
    workers: int = typer.Option(1, help="hilos en paralelo para el LLM (ALBERTITOS_WORKERS)"),
) -> None:
    """PDF → hechos (plantilla o LLM). Implementación: extract/etapa.py (Javier)."""
    from albertitos.extract.etapa import extraer

    try:
        r = extraer(_conn(), solo_pendientes=solo_pendientes, fixture=fixture, workers=workers)
    except NotImplementedError as e:
        rprint(f"[yellow]{e}[/yellow]")
        raise typer.Exit(3) from None
    rprint(r.texto())


hechos_app = typer.Typer(
    help="Hechos extraídos: exportar/importar fixtures (para trabajar sin LLM)"
)
app.add_typer(hechos_app, name="hechos")


@hechos_app.command("export")
def hechos_export(
    salida: Path = Path("data/fixtures/hechos_muestra.jsonl"),
    fixture: Path | None = typer.Option(None, help="sólo estos file_id (uno por línea)"),
) -> None:
    """BD → JSONL de InvoiceFacts (una línea por fichero) para que rules/ y pipeline/ trabajen sin LLM."""
    from albertitos.core.versions import EXTRACTOR_VERSION

    conn = _conn(solo_lectura=True)
    quiero = None
    if fixture:
        quiero = {
            unicodedata.normalize("NFC", x.strip())
            for x in fixture.read_text(encoding="utf-8").splitlines()
            if x.strip()
        }
    filas = conn.execute(
        "SELECT f.file_id, h.hechos_json FROM hechos h JOIN ficheros f ON f.sha256=h.sha256 WHERE h.extractor_version=? ORDER BY f.file_id",
        (EXTRACTOR_VERSION,),
    ).fetchall()
    salida.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(salida, "w", encoding="utf-8", newline="\n") as f:
        for fila in filas:
            if quiero is not None and fila["file_id"] not in quiero:
                continue
            f.write(fila["hechos_json"] + "\n")
            n += 1
    rprint(f"[green]{n} hechos[/green] → {salida}")


@hechos_app.command("import")
def hechos_import(ruta: Path) -> None:
    """JSONL de InvoiceFacts → BD (requiere que los ficheros estén ingeridos). Idempotente."""
    from albertitos.core import db
    from albertitos.core.contracts import EstadoEvento, Etapa, Event, InvoiceFacts

    conn = _conn()
    n = 0
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        h = InvoiceFacts.model_validate_json(linea)
        if conn.execute("SELECT 1 FROM ficheros WHERE sha256=?", (h.sha256,)).fetchone() is None:
            rprint(
                f"  [yellow]![/yellow] {h.file_id}: no está ingerido (sha256 desconocido); `albertitos ingest` primero"
            )
            continue
        db.guardar_hechos(conn, h)
        db.registrar_evento(
            conn,
            Event(
                file_id=h.file_id,
                sha256=h.sha256,
                etapa=Etapa.EXTRACT,
                estado=EstadoEvento.OK,
                version=h.extractor_version,
                detalle=f"import:{h.metodo.value}",
            ),
        )
        n += 1
    conn.commit()
    rprint(f"[green]{n} hechos[/green] importados de {ruta}")


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
    try:
        with erp.ClienteERP(conn=conn) as cliente:
            s = cliente.descargar_todo(tag)
    except erp.ErrorERP as exc:  # una línea útil, no 92 de traceback; el snapshot anterior sigue
        print(str(exc))
        raise typer.Exit(1) from None
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
    from albertitos.pipeline.run import porques
    from albertitos.sources import snapshot

    corte = _fecha_corte(fecha_corte)
    conn = _conn()
    m = snapshot.cargar_maestro_bd(conn)
    e = snapshot.cargar_erp_bd(conn, erp)
    por, por_defecto = porques(
        conn, norma_version=norma, fecha_corte=corte, maestro=m, erp=e, origen="decide"
    )
    n = etapas.decide(
        conn,
        norma_version=norma,
        fecha_corte=corte,
        maestro=m,
        erp=e,
        por=por,
        por_defecto=por_defecto,
    )
    rprint(f"[green]{n} decisiones[/green] con norma {norma}, maestro {m.version}, erp {e.version}")


@app.command()
def reprocess(
    impacted: bool = typer.Option(
        True, "--impacted/--no-impacted", help="sólo lo impactado (por defecto)"
    ),
    todo: bool = typer.Option(False, "--todo", help="recalcula todo sin mirar el linaje"),
    norma: str = "v3",
    fecha_corte: str | None = None,
    erp: str | None = None,
    lote: int | None = None,
) -> None:
    """Recalcula sólo lo impactado (hechos, norma, fecha de corte, o el diff de maestro/ERP toca su
    pedido o su NIF) y muestra qué cambia en esta pasada."""
    from albertitos.pipeline.run import reprocesar
    from albertitos.sources import snapshot

    corte = _fecha_corte(fecha_corte)
    conn = _conn()
    r = reprocesar(
        conn,
        norma_version=norma,
        fecha_corte=corte,
        maestro=snapshot.cargar_maestro_bd(conn),
        erp=snapshot.cargar_erp_bd(conn, erp),
        lote=lote,
        todo=todo or not impacted,
    )
    rprint(r.texto())


@app.command()
def run(
    norma: str = "v3",
    fecha_corte: str | None = None,
    extraer: bool = typer.Option(
        True, "--extraer/--sin-extraer", help="--sin-extraer: sólo hechos ya en la BD, sin LLM"
    ),
    con_traza: bool = typer.Option(
        True, "--con-traza/--sin-traza", help="motivo, regla y norma_version en cada línea"
    ),
    salida: Path = typer.Option(ENTREGA, help="carpeta de la entrega (ensayos y demo: otra)"),
    sin_auditoria: bool = typer.Option(False, "--sin-auditoria", help=AYUDA_SIN_AUDITORIA),
    aceptar_rojo: str | None = typer.Option(None, "--aceptar-rojo", help=AYUDA_ACEPTAR_ROJO),
    erp: str | None = typer.Option(
        None,
        help="snapshot del ERP (v1, v2…; tiene que estar en la BD). Sin él, el último descargado",
    ),
) -> None:
    """ingest → maestro → erp pull (si no hay) → extract → duplicados → decide → package."""
    from albertitos.pipeline.run import correr

    corte = _fecha_corte(fecha_corte)  # antes de trabajar: sin fecha de corte no se decide
    aceptar_rojo = _aceptar_rojo(aceptar_rojo)
    if erp is not None:
        from albertitos.sources import snapshot

        try:
            snapshot.cargar_erp_bd(_conn(solo_lectura=True), erp)
        except LookupError as e:
            rprint(f"[red]{e}[/red]")
            raise typer.Exit(1) from None
    r = correr(
        _conn(),
        caja=CAJA,
        lote2=LOTE2,
        entrega=salida,
        norma_version=norma,
        fecha_corte=corte,
        extraer=extraer,
        workers=int(os.environ.get("ALBERTITOS_WORKERS", "1")),
        con_traza=con_traza,
        auditar=_auditor(sin_auditoria),
        aceptar_rojo=aceptar_rojo,
        erp_version=erp,
    )
    rprint(r.texto())
    if not r.ok:
        raise typer.Exit(1)


# ----------------------------------------------------------------------------- operación


@app.command()
def status(
    historico: bool = typer.Option(
        False,
        "--historico",
        help="el log entero (ensayos, fallos ya resueltos, EUR registrados) en vez del estado actual",
    ),
) -> None:
    """Estado por lote, resultado y etapa (el último evento de cada fichero); ERP; pendientes."""
    from albertitos.core import db
    from albertitos.pipeline import traza
    from albertitos.sources import snapshot

    conn = _conn(solo_lectura=True)
    r = db.resumen(conn)
    rprint(
        f"ficheros por lote: {r['ficheros']} · decisiones vigentes: {r['decisiones']} · caché LLM: {r['cache_llm']}"
    )
    if historico:
        t = Table(
            "etapa", "estado", "eventos", "lat media ms", "EUR", "reintentos", title="histórico"
        )
        for e in r["eventos"]:
            t.add_row(
                e["etapa"],
                e["estado"],
                str(e["n"]),
                str(e["lat_media_ms"]),
                str(e["coste_eur"]),
                str(e["reintentos"]),
            )
    else:
        t = Table(
            "etapa", "estado", "ficheros", "lat media ms", title="estado actual (último evento)"
        )
        for e in r["estado_actual"]:
            t.add_row(e["etapa"], e["estado"], str(e["n"]), str(e["lat_media_ms"]))
    rprint(t)
    try:
        ultimo = snapshot.cargar_erp_bd(conn, None).version
        print(traza.linea_erp(snapshot.resumen_erp(conn, ultimo)) + " (el que usa run sin --erp)")
    except LookupError:
        print("ERP: ningún snapshot en la BD (`albertitos erp pull --tag v1`)")
    if not historico:
        h = r["historico"]
        print(
            f"histórico: {h['n']} eventos desde {traza.hora(h['desde'])} · "
            f"{h['reintentos'] or 0} reintentos (`status --historico`)"
        )
    p = r["pendientes"]
    rprint(
        f"sin decisión vigente: {len(p)}"
        + (f" → {p[:10]}{' …' if len(p) > 10 else ''}" if p else "")
    )


@app.command()
def trace(
    file_id: str,
    legible: bool = typer.Option(
        True,
        "--legible/--json",
        help="--legible (por defecto): hechos → maestro → ERP → reglas → resultado, un paso por "
        "bloque · --json: todo lo que hay en la BD, tal cual",
    ),
) -> None:
    """Todo lo que sabemos de un fichero: hechos, maestro, ERP, duplicados, decisión(es), eventos."""
    from albertitos.core import db
    from albertitos.pipeline import traza

    conn = _conn(solo_lectura=True)
    fid = unicodedata.normalize("NFC", file_id)
    t = db.traza(conn, fid)
    if not t["fichero"]:
        rprint(f"[red]{file_id} no está en la BD[/red] (¿ingest? ¿nombre exacto?)")
        raise typer.Exit(1)
    if legible:
        print(traza.legible(conn, fid))  # print: los corchetes de los avisos no son markup de rich
        return
    vigente = next((d for d in t["decisiones"] if d["vigente"]), None)
    t["duplicado_con"] = traza.duplicado_con(conn, t["fichero"]["sha256"])
    t["erp"] = traza.resumen_erp_o_nada(conn, vigente["erp_version"]) if vigente else None
    print(json.dumps(t, ensure_ascii=False, indent=1, default=str))


@app.command()
def validate(ruta: Path, lote: int = 1) -> None:
    """Valida un JSONL de entrega contra los PDFs reales del lote."""
    from albertitos.pipeline.validar import listar_pdfs, validar_jsonl

    directorio = (CAJA if lote == 1 else LOTE2) / "facturas"
    inf = validar_jsonl(ruta, listar_pdfs(directorio) if directorio.exists() else [], lote)
    rprint(inf.texto())
    raise typer.Exit(0 if inf.ok else 1)


@app.command()
def package(
    con_traza: bool = typer.Option(
        True, "--con-traza/--sin-traza", help="motivo, regla y norma_version en cada línea"
    ),
    salida: Path = ENTREGA,
    sin_auditoria: bool = typer.Option(False, "--sin-auditoria", help=AYUDA_SIN_AUDITORIA),
    aceptar_rojo: str | None = typer.Option(None, "--aceptar-rojo", help=AYUDA_ACEPTAR_ROJO),
) -> None:
    """BD → dist/entrega/outcomes*.jsonl, validados y auditados. Se niega si falta alguna decisión o
    si la auditoría de entrega sale roja (salvo --aceptar-rojo "<motivo>"). Sólo escribe en la BD
    eventos de emit (la traza de lo entregado)."""
    from albertitos.pipeline import package as pk

    aceptar_rojo = _aceptar_rojo(aceptar_rojo)
    auditar = _auditor(sin_auditoria)
    try:
        for ruta, inf in pk.empaquetar(
            _conn(),
            salida,
            CAJA,
            LOTE2,
            con_traza=con_traza,
            auditar=auditar,
            aceptar_rojo=aceptar_rojo,
        ):
            rprint(inf.texto(), "→", ruta)
    except pk.EntregaInvalida as e:
        rprint(f"[red]NO se escribe la entrega:[/red]\n{e}")
        raise typer.Exit(1) from None


@app.command()
def bench(
    desde: str | None = typer.Option(
        None, help="sólo eventos con ts >= este ISO (UTC), p. ej. el inicio de un run"
    ),
) -> None:
    """Cifras medidas desde el log de eventos (para docs/benchmark.md)."""
    from albertitos.pipeline import bench as b

    print(b.texto(b.medir(_conn(solo_lectura=True), desde=desde)))


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
