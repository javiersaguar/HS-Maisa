"""Empaquetado de la entrega: BD → dist/entrega/*.jsonl, siempre pasando por el validador.

Eventos (etapa emit): uno por intento y lote (sin file_id: OK con nº de líneas, o ERROR con los
errores) y, por fichero, uno cuando cambia lo entregado o cuando no se puede entregar (PENDIENTE:
sin decisión vigente, la entrega se niega).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from albertitos.core import db
from albertitos.core.contracts import EstadoEvento, Etapa, Event, Outcome, Resultado
from albertitos.pipeline.etapas import registrar_transicion
from albertitos.pipeline.validar import InformeValidacion, listar_pdfs, validar_jsonl

log = logging.getLogger(__name__)


class EntregaInvalida(Exception):
    def __init__(self, informe: InformeValidacion) -> None:
        super().__init__(informe.texto())
        self.informe = informe


def empaquetar(
    conn,
    salida: Path,
    caja_dir: Path,
    lote2_dir: Path | None = None,
    con_traza: bool = False,
) -> list[tuple[Path, InformeValidacion]]:
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
    try:
        for lote, nombre, directorio in lotes:
            esperados = listar_pdfs(directorio)
            filas = db.decisiones_vigentes(conn, lote=lote)
            outcomes: list[Outcome] = []
            for fila in filas:
                extra: dict[str, str] = {}
                if con_traza:
                    motivos = json.loads(fila["motivos_json"])
                    fallo = next((m for m in motivos if not m["ok"]), None)
                    extra = {
                        "norma_version": fila["norma_version"],
                        "motivo": fallo["detalle"] if fallo else "todas las reglas cumplidas",
                    }
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
                _eventos_rechazo(conn, lote, nombre, informe, sin_decision)
                raise EntregaInvalida(informe)
            generados.append((destino, informe))
            entregados.append((lote, nombre, filas))
        for tmp, destino in temporales:
            tmp.replace(destino)
    finally:
        for tmp, _ in temporales:
            tmp.unlink(missing_ok=True)
    _eventos_entrega(conn, entregados)
    return generados


def _eventos_rechazo(
    conn, lote: int, nombre: str, informe: InformeValidacion, sin_decision: list[str]
) -> None:
    try:
        db.registrar_evento(
            conn,
            Event(
                etapa=Etapa.EMIT,
                estado=EstadoEvento.ERROR,
                error_codigo="ENTREGA-INVALIDA",
                detalle=json.dumps(
                    {
                        "lote": lote,
                        "entrega": nombre,
                        "n_errores": len(informe.errores),
                        "errores": informe.errores[:5],
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        ids = {
            r["file_id"]: r["sha256"]
            for r in conn.execute(
                "SELECT file_id, sha256 FROM ficheros WHERE lote=?", (lote,)
            ).fetchall()
        }
        for fid in sin_decision:
            registrar_transicion(
                conn,
                Event(
                    file_id=fid,
                    sha256=ids.get(fid),
                    etapa=Etapa.EMIT,
                    estado=EstadoEvento.PENDIENTE,
                    detalle=json.dumps(
                        {"entrega": nombre, "pendiente": "sin decisión vigente: package se niega"},
                        ensure_ascii=False,
                    ),
                ),
            )
        conn.commit()
    except sqlite3.Error as e:  # la traza nunca bloquea (ni desbloquea) una entrega
        log.warning("no se pudieron registrar los eventos de emit: %s", e)


def _eventos_entrega(conn, entregados: list[tuple[int, str, list[sqlite3.Row]]]) -> None:
    try:
        for lote, nombre, filas in entregados:
            db.registrar_evento(
                conn,
                Event(
                    etapa=Etapa.EMIT,
                    estado=EstadoEvento.OK,
                    detalle=json.dumps(
                        {"lote": lote, "entrega": nombre, "lineas": len(filas)}, ensure_ascii=False
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
