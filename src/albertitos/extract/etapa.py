"""Etapa extract: ficheros pendientes → InvoiceFacts en la BD, con eventos. Dueño: Javier (agente A1).

Firma CONGELADA (la llama pipeline/etapas.py y cli.py; no cambiarla sin avisar a Miguel):

    extraer(conn, *, solo_pendientes=True, fixture=None, workers=1) -> ResumenExtraccion

Algoritmo a implementar (A1):
1. Candidatos: filas de `ficheros` sin `hechos` para EXTRACTOR_VERSION (si solo_pendientes) o todas;
   si `fixture` es una lista de file_id (uno por línea), sólo esos.
2. Por fichero: `pdf.info` ya dice si tiene texto. Con texto → `pdf.texto_de`; sin texto → `pdf.imagen_png`.
3. Con texto: `plantillas.extraer_por_plantilla(texto, file_id=..., sha256=...)`. Si devuelve hechos completos,
   metodo=PLANTILLA y NO se llama al LLM (coste 0). Si no, `ClienteLLM.extraer(...)`.
   Si hay plantilla y LLM (modo de contraste, opcional), `validadores.discrepancias(a, b)` → Aviso.DISCREPANCIA_EXTRACTORES.
4. `h.avisos = validadores.validar(h)`; `db.guardar_hechos(conn, h)`; Event(EXTRACT, OK, latencia, tokens, coste, version, detalle=metodo).
5. `ErrorLLM` → Event(EXTRACT, PENDIENTE, error_codigo=e.codigo) y seguir. Nada revienta el lote.
6. `workers > 1`: ThreadPoolExecutor; cada hilo abre su propia conexión (`db.conectar()`), el LLM comparte cliente.
   Commit por fichero (WAL lo aguanta).
7. Devolver ResumenExtraccion con contadores y coste; cli.py lo imprime.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ResumenExtraccion:
    candidatos: int = 0
    ok: int = 0
    pendientes: int = 0
    por_metodo: dict[str, int] = field(
        default_factory=dict
    )  # plantilla | llm_texto | llm_vision | cache
    errores: dict[str, int] = field(default_factory=dict)  # error_codigo → n
    tokens_in: int = 0
    tokens_out: int = 0
    coste_eur: float = 0.0
    segundos: float = 0.0

    def texto(self) -> str:
        return (
            f"extract: {self.ok}/{self.candidatos} ok · {self.pendientes} pendientes · métodos {self.por_metodo} · "
            f"errores {self.errores} · tokens {self.tokens_in}/{self.tokens_out} · {self.coste_eur:.4f} EUR · {self.segundos:.1f} s"
        )


def extraer(
    conn: sqlite3.Connection,
    *,
    solo_pendientes: bool = True,
    fixture: Path | None = None,
    workers: int = 1,
) -> ResumenExtraccion:
    raise NotImplementedError(
        "extract pendiente: Javier / agente A1 (src/albertitos/extract/etapa.py, algoritmo en el docstring). "
        "Mientras tanto: `albertitos hechos import data/fixtures/hechos_muestra.jsonl` carga hechos ya extraídos."
    )
