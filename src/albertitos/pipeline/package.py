"""Empaquetado de la entrega: BD → dist/entrega/*.jsonl, siempre pasando por el validador."""

from __future__ import annotations

import json
from pathlib import Path

from albertitos.core import db
from albertitos.core.contracts import Outcome, Resultado
from albertitos.pipeline.validar import InformeValidacion, listar_pdfs, validar_jsonl


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
    generados: list[tuple[Path, InformeValidacion]] = []
    for lote, nombre, directorio in lotes:
        esperados = listar_pdfs(directorio)
        outcomes: list[Outcome] = []
        for fila in db.decisiones_vigentes(conn, lote=lote):
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
        with open(destino, "w", encoding="utf-8", newline="\n") as f:
            for o in outcomes:
                f.write(o.linea() + "\n")
        informe = validar_jsonl(destino, esperados, lote)
        if not informe.ok:
            raise EntregaInvalida(informe)
        generados.append((destino, informe))
    return generados
