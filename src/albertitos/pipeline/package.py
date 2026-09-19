"""Empaquetado de la entrega: BD → dist/entrega/*.jsonl, siempre pasando por el validador.

Después de validar todos los lotes y antes de sustituir nada, la auditoría de entrega (E2,
docs/agentes/AUDITORIA-ENTREGA.md: ningún PAGAR que no toque, ningún duplicado sin marcar) mira la BD;
si sale roja, la entrega se niega igual que con un JSONL inválido.

Eventos (etapa emit): uno por intento y lote (sin file_id: OK con nº de líneas y si hubo auditoría, o
ERROR con los errores) y, por fichero, uno cuando cambia lo entregado o cuando no se puede entregar
(PENDIENTE: sin decisión vigente o señalado por la auditoría, la entrega se niega).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from albertitos.core import db
from albertitos.core.contracts import EstadoEvento, Etapa, Event, Outcome, Resultado
from albertitos.pipeline.etapas import registrar_transicion
from albertitos.pipeline.validar import InformeValidacion, listar_pdfs, validar_jsonl

log = logging.getLogger(__name__)


class InformeAuditoria(Protocol):
    """Lo que `empaquetar` necesita de la auditoría. `ok` = ningún ROJO (el ÁMBAR informa, no bloquea)."""

    @property
    def ok(self) -> bool: ...

    @property
    def rojos(self) -> dict[str, list[str]]: ...  # comprobación → file_id señalados

    def texto(self) -> str: ...


# conn en la BD de la entrega, {lote: directorio de sus PDF}; sólo lee
Auditor = Callable[[sqlite3.Connection, dict[int, Path]], InformeAuditoria]


def auditor_de_entrega() -> Auditor | None:
    """`pipeline.auditoria.auditar` (E2) si ya existe; None si todavía no. Quien empaqueta de verdad
    (CLI `package` y `run`) lo pasa a `empaquetar`: en cuanto llegue, se aplica sin tocar nada más."""
    try:
        from albertitos.pipeline.auditoria import auditar
    except ModuleNotFoundError as e:
        if e.name != "albertitos.pipeline.auditoria":
            raise  # existe pero le falta algo: que se vea, no que se salte
        return None
    return auditar


@dataclass
class _AuditoriaFallida:
    """La auditoría lanzó una excepción: sin auditoría no hay entrega (se niega, no se salta)."""

    error: str
    rojos: dict[str, list[str]] = field(default_factory=dict)
    ok: bool = False

    def texto(self) -> str:
        return f"NO APTO · la auditoría de entrega falló: {self.error}"


class EntregaInvalida(Exception):
    def __init__(self, informe: InformeValidacion | InformeAuditoria) -> None:
        super().__init__(informe.texto())
        self.informe = informe


def empaquetar(
    conn,
    salida: Path,
    caja_dir: Path,
    lote2_dir: Path | None = None,
    con_traza: bool = False,
    auditar: Auditor | None = None,
    aceptar_rojo: str | None = None,
) -> list[tuple[Path, InformeValidacion]]:
    """`aceptar_rojo` = motivo para entregar aunque la auditoría salga ROJA (como `make publicar
    --aceptar-rojo`): queda en un evento emit AUDITORIA-ROJA-ACEPTADA. Una auditoría que falla no se
    acepta nunca, ni un JSONL inválido."""
    if aceptar_rojo is not None and not aceptar_rojo.strip():
        raise ValueError("aceptar_rojo exige un motivo no vacío")
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    lotes = [(1, "outcomes.jsonl", Path(caja_dir) / "facturas")]
    if lote2_dir and (Path(lote2_dir) / "facturas").exists():
        lotes.append((2, "outcomes_lote2.jsonl", Path(lote2_dir) / "facturas"))
    # Todo o nada: se escribe a .tmp, se validan todos los lotes y sólo entonces se sustituyen.
    # Una entrega inválida nunca pisa la última válida de dist/entrega/.
    generados: list[tuple[Path, InformeValidacion]] = []
    temporales: list[tuple[Path, Path]] = []
    entregados: list[tuple[int, str, list[sqlite3.Row]]] = []
    # Un PDF con más de un nombre (copia exacta, P0-1): una línea por nombre, con la decisión de su
    # sha256, y el motivo nombra a los demás. Sin copias (lote 1 de la Caja) no cambia nada.
    copias = db.nombres_por_sha(conn)
    try:
        for lote, nombre, directorio in lotes:
            esperados = listar_pdfs(directorio)
            # un nombre interno de P0-5 (`./X.pdf`) nunca sale: su línea es la de su nombre de entrega
            filas = [
                f
                for f in db.decisiones_vigentes(conn, lote=lote)
                if not db.es_interno(f["fichero_id"])
            ]
            extras = db.identidades_vigentes(conn, lote)
            if extras:
                filas = sorted([*filas, *extras], key=lambda x: str(x["file_id"]))
            outcomes: list[Outcome] = []
            for fila in filas:
                extra: dict[str, str] = {}
                if con_traza:
                    motivos = json.loads(fila["motivos_json"])
                    fallo = next((m for m in motivos if not m["ok"]), None)
                    motivo = fallo["detalle"] if fallo else "todas las reglas cumplidas"
                    otros = [
                        f"{fid} (lote {lt})"
                        for fid, lt in copias.get(fila["sha256"], [])
                        if (fid, lt) != (fila["file_id"], lote)
                    ]
                    if otros:
                        motivo += " · el mismo PDF que " + ", ".join(otros)
                    extra = {"norma_version": fila["norma_version"], "motivo": motivo}
                    if fallo:
                        extra["regla"] = fallo["regla_id"]
                outcomes.append(
                    Outcome(file_id=fila["file_id"], result=Resultado(fila["resultado"]), **extra)
                )
            destino = salida / nombre
            tmp = destino.with_name(nombre + ".tmp")
            temporales.append((tmp, destino))
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                for o in outcomes:
                    f.write(o.linea() + "\n")
            informe = validar_jsonl(tmp, esperados, lote)
            informe.ruta = str(destino)
            if not informe.ok:
                sin_decision = sorted(set(esperados) - {str(x["file_id"]) for x in filas})
                _eventos_rechazo(
                    conn,
                    "ENTREGA-INVALIDA",
                    {
                        "lote": lote,
                        "entrega": nombre,
                        "n_errores": len(informe.errores),
                        "errores": informe.errores[:5],
                    },
                    {fid: "sin decisión vigente: package se niega" for fid in sin_decision},
                )
                raise EntregaInvalida(informe)
            generados.append((destino, informe))
            entregados.append((lote, nombre, filas))
        auditoria = "no ejecutada"
        if auditar is not None:
            auditoria = _auditar(
                conn,
                auditar,
                {lote: d for lote, _, d in lotes},
                [n for _, n, _ in lotes],
                aceptar_rojo,
            )
        for tmp, destino in temporales:
            tmp.replace(destino)
    finally:
        for tmp, _ in temporales:
            tmp.unlink(missing_ok=True)
    _eventos_entrega(conn, entregados, auditoria)
    return generados


def _auditar(
    conn,
    auditar: Auditor,
    dirs: dict[int, Path],
    nombres: list[str],
    aceptar_rojo: str | None = None,
) -> str:
    """Todos los lotes ya son válidos; si la auditoría sale roja (o falla), EntregaInvalida. Un rojo
    con `aceptar_rojo` se entrega y queda registrado. Devuelve lo que dice el evento emit."""
    try:
        informe = auditar(conn, dirs)
    except Exception as e:  # noqa: BLE001 — un fallo de la auditoría niega la entrega, no la salta
        log.exception("la auditoría de entrega falló")
        informe = _AuditoriaFallida(error=f"{type(e).__name__}: {e}")
    if informe.ok:
        return "verde"
    rojos = {c: fids for c, fids in informe.rojos.items() if fids}
    if aceptar_rojo and not isinstance(informe, _AuditoriaFallida):
        try:
            db.registrar_evento(
                conn,
                Event(
                    etapa=Etapa.EMIT,
                    estado=EstadoEvento.OK,
                    error_codigo="AUDITORIA-ROJA-ACEPTADA",
                    detalle=json.dumps(
                        {
                            "entrega": nombres,
                            "motivo": aceptar_rojo,
                            "rojos": {c: fids[:5] for c, fids in rojos.items()},
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
            conn.commit()
        except sqlite3.Error as e:
            log.warning("no se pudo registrar el rojo aceptado: %s", e)
        log.warning("auditoría ROJA aceptada (%s):\n%s", aceptar_rojo, informe.texto())
        return f"roja aceptada: {aceptar_rojo}"
    _eventos_rechazo(
        conn,
        "AUDITORIA-ERROR" if isinstance(informe, _AuditoriaFallida) else "AUDITORIA-ROJA",
        {
            "entrega": nombres,
            "rojos": {c: fids[:5] for c, fids in rojos.items()},
            "informe": informe.texto()[:1000],
        },
        {fid: f"auditoría de entrega: {c}" for c, fids in rojos.items() for fid in fids},
    )
    raise EntregaInvalida(informe)


def _eventos_rechazo(conn, codigo: str, detalle: dict, pendientes: dict[str, str]) -> None:
    """Un emit/error por intento y un emit/pendiente por fichero que impide la entrega."""
    try:
        db.registrar_evento(
            conn,
            Event(
                etapa=Etapa.EMIT,
                estado=EstadoEvento.ERROR,
                error_codigo=codigo,
                detalle=json.dumps(detalle, ensure_ascii=False),
            ),
        )
        entrega = detalle.get("entrega")
        ids = {
            r["file_id"]: r["sha256"] for r in conn.execute("SELECT file_id, sha256 FROM ficheros")
        }
        for sha, nombres in db.nombres_por_sha(conn).items():  # los nombres extra, también
            ids.update({fid: sha for fid, _ in nombres[1:]})
        for fid, porque in pendientes.items():
            registrar_transicion(
                conn,
                Event(
                    file_id=fid,
                    sha256=ids.get(fid),
                    etapa=Etapa.EMIT,
                    estado=EstadoEvento.PENDIENTE,
                    detalle=json.dumps(
                        {"entrega": entrega, "pendiente": porque}, ensure_ascii=False
                    ),
                ),
            )
        conn.commit()
    except sqlite3.Error as e:  # la traza nunca bloquea (ni desbloquea) una entrega
        log.warning("no se pudieron registrar los eventos de emit: %s", e)


def _eventos_entrega(
    conn, entregados: list[tuple[int, str, list[sqlite3.Row]]], auditoria: str
) -> None:
    try:
        for lote, nombre, filas in entregados:
            db.registrar_evento(
                conn,
                Event(
                    etapa=Etapa.EMIT,
                    estado=EstadoEvento.OK,
                    detalle=json.dumps(
                        {
                            "lote": lote,
                            "entrega": nombre,
                            "lineas": len(filas),
                            "auditoria": auditoria,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
            for fila in filas:
                registrar_transicion(
                    conn,
                    Event(
                        file_id=fila["file_id"],
                        sha256=fila["sha256"],
                        etapa=Etapa.EMIT,
                        estado=EstadoEvento.OK,
                        version=fila["norma_version"],
                        detalle=json.dumps(  # sin id de decisión: run redecide todo cada vez
                            {"entrega": nombre, "result": fila["resultado"]}, ensure_ascii=False
                        ),
                    ),
                )
        conn.commit()
    except sqlite3.Error as e:
        log.warning("no se pudieron registrar los eventos de emit: %s", e)
