"""Auditoría de entrega (E2, G1). Sólo LEE la BD, los PDF y los JSONL: no decide, no corrige, no escribe nada.

`package` la ejecuta después de validar los JSONL y antes de sustituir la entrega (`package.Auditor`): con un
ROJO, la entrega se niega. `scripts/auditoria_entrega.py` es su CLI (la usan `make publicar` y la skill /lote2).

Por qué existe (19/09, 01:30). El validador comprueba la FORMA de la entrega (conjunto exacto, NFC, enum), no
su CONTENIDO. Esa noche se colaron tres cosas que el validador daba por buenas:
- `PO-2026-0492`, facturado dos veces (1.512,50 € cada una, un único asiento PENDIENTE), estaba en PAGAR las dos
  veces: `marcar_duplicados` sólo corre dentro de `run` y la BD se había construido con pasos sueltos;
- `scan_025.pdf` escalaba con el motivo literal `el documento dice: "None"`: el modelo devolvió esa cadena en
  `texto_sospechoso` y se tomó por una instrucción;
- los 10 `L2-*` del lote simulado seguían en la BD y movieron 20 decisiones del lote 1 (duplicados de mentira).

Contrato con `package` (`InformeAuditoria`): `auditar(conn, {lote: dir_pdfs})` devuelve un `Informe` con `.ok`
(ningún ROJO; el ÁMBAR informa y no bloquea), `.rojos` (comprobación → file_id señalados) y `.texto()`.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from albertitos.core import db
from albertitos.core.contracts import (
    Aviso,
    ErpEntry,
    ErpSnapshot,
    InvoiceFacts,
    MasterSnapshot,
)
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.formatos import (
    CENT,
    normalizar_iban,
    normalizar_nif,
    sin_tildes,
)
from albertitos.pipeline.validar import listar_pdfs, validar_jsonl
from albertitos.sources import snapshot

ROJO, AMBAR, OK = "ROJO", "ÁMBAR", "OK"
MAX_EJEMPLOS = 8
UMBRAL_ESCALAR = 0.15
UMBRAL_NO_PAGAR = 0.05
ENTREGAS = {1: "outcomes.jsonl", 2: "outcomes_lote2.jsonl"}
# Avisos que no dicen nada malo de la factura: cómo se leyó (escaneada) o cómo se escribió la fecha.
AVISOS_BENIGNOS = {Aviso.SIN_TEXTO, Aviso.FECHA_EN_LETRA}
# La decisión de contingencia de `scripts/contingencia.py` (ADR-0009): su regla y su hash de hechos.
REGLA_CONTINGENCIA = "contingencia.C1"
SIN_HECHOS = "sin-hechos"
# Lo mismo que descarta `extract/llm.py::_fragmento_valido`: hay modelos que rellenan el campo con la palabra
# "None" en vez de dejarlo nulo. Un hecho guardado antes de ese filtro sigue llevándola (scan_025, 18/09).
NO_ES_FRAGMENTO = {
    "",
    "none",
    "null",
    "nulo",
    "n/a",
    "na",
    "-",
    "ninguno",
    "ninguna",
    "nada",
    "false",
}
# Cómo cita R6 la evidencia en el motivo (`rules/norma_v3.py::regla_6_anomalias`).
_CITA_R6 = re.compile(r'el documento dice: "(.*)"\Z', re.DOTALL)


# ----------------------------------------------------------------------------- modelo del informe


@dataclass
class Comprobacion:
    clave: str
    titulo: str
    nivel: str = OK
    n: int = 0
    ejemplos: list[str] = field(default_factory=list)
    que_hacer: str = ""
    ficheros: list[str] = field(default_factory=list)  # file_id señalados (package los anota)


@dataclass
class Informe:
    db: str
    lotes: list[int]
    comprobaciones: list[Comprobacion] = field(default_factory=list)
    distribucion: dict[int, dict[str, int]] = field(default_factory=dict)
    notas: list[str] = field(default_factory=list)

    @property
    def rojos(self) -> dict[str, list[str]]:
        """Comprobación en ROJO → file_id señalados (lista vacía si no es de un fichero concreto)."""
        return {c.clave: c.ficheros for c in self.comprobaciones if c.nivel == ROJO}

    @property
    def ok(self) -> bool:
        return not self.rojos

    def texto(self) -> str:
        return texto(self)

    def como_dict(self) -> dict[str, Any]:
        return {
            "db": self.db,
            "lotes": self.lotes,
            "veredicto": "VERDE" if self.ok else "ROJO",
            "rojos": list(self.rojos),
            "distribucion": {str(k): v for k, v in self.distribucion.items()},
            "notas": self.notas,
            "comprobaciones": [asdict(c) for c in self.comprobaciones],
        }


def _comprobacion(
    clave: str,
    titulo: str,
    hallazgos: list[str],
    nivel: str,
    que_hacer: str,
    ficheros: list[str] | None = None,
) -> Comprobacion:
    if not hallazgos:
        return Comprobacion(clave, titulo)
    return Comprobacion(
        clave,
        titulo,
        nivel,
        len(hallazgos),
        hallazgos[:MAX_EJEMPLOS],
        que_hacer,
        sorted(set(ficheros or [])),
    )


# ----------------------------------------------------------------------------- lectura de la BD


@dataclass
class Fila:
    """Un fichero de la BD con sus hechos (versión actual del extractor) y su decisión vigente."""

    file_id: str
    sha256: str
    lote: int
    tiene_texto: bool
    hechos: InvoiceFacts | None
    hechos_hash: str | None
    hechos_en: str | None
    decision: sqlite3.Row | None

    @property
    def resultado(self) -> str | None:
        return None if self.decision is None else str(self.decision["resultado"])


def cargar_filas(conn: sqlite3.Connection) -> list[Fila]:
    hechos = {
        r["sha256"]: r
        for r in conn.execute(
            "SELECT sha256, hechos_json, hechos_hash, creado_en FROM hechos WHERE extractor_version=?",
            (EXTRACTOR_VERSION,),
        )
    }
    decisiones = {r["sha256"]: r for r in conn.execute("SELECT * FROM decisiones WHERE vigente=1")}
    filas = []
    for f in conn.execute(
        "SELECT file_id, sha256, lote, tiene_texto FROM ficheros ORDER BY file_id"
    ):
        h = hechos.get(f["sha256"])
        filas.append(
            Fila(
                file_id=str(f["file_id"]),
                sha256=str(f["sha256"]),
                lote=int(f["lote"] or 1),
                tiene_texto=bool(f["tiene_texto"]),
                hechos=None if h is None else InvoiceFacts.model_validate_json(h["hechos_json"]),
                hechos_hash=None if h is None else str(h["hechos_hash"]),
                hechos_en=None if h is None else str(h["creado_en"]),
                decision=decisiones.get(f["sha256"]),
            )
        )
    # Un nombre extra (copia exacta, P0-1) es otra línea de la entrega con los hechos y la decisión de
    # su PDF: entra como una fila más, y así el conjunto, los fantasmas, el pago doble (dos nombres del
    # mismo pedido) y la entrega en disco lo miran sin comprobaciones nuevas.
    if db.hay_identidades(conn):
        por_sha = {f.sha256: f for f in filas}
        for i in conn.execute("SELECT file_id, lote, sha256 FROM identidades"):
            base = por_sha.get(i["sha256"])
            if base is not None:
                filas.append(replace(base, file_id=str(i["file_id"]), lote=int(i["lote"])))
        # P0-5: el nombre interno (`./X.pdf`) no es una línea: la suya es la de su nombre de entrega
        filas = sorted((f for f in filas if not db.es_interno(f.file_id)), key=lambda f: f.file_id)
    return filas


class Snapshots:
    """Maestro y ERP por versión, cargados una vez: cada decisión se audita contra los que la produjeron."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self._maestros: dict[str, MasterSnapshot | None] = {}
        self._erps: dict[str, tuple[ErpSnapshot, dict[str, list[ErpEntry]]] | None] = {}

    def maestro(self, version: str) -> MasterSnapshot | None:
        if version not in self._maestros:
            try:
                self._maestros[version] = snapshot.cargar_maestro_bd(self.conn, version)
            except LookupError:
                self._maestros[version] = None
        return self._maestros[version]

    def asientos(self, version: str, pedido: str | None) -> list[ErpEntry] | None:
        """Asientos del pedido en esa versión del ERP; None si el snapshot no está en la BD."""
        if version not in self._erps:
            try:
                e = snapshot.cargar_erp_bd(self.conn, version)
                self._erps[version] = (e, e.por_pedido())
            except LookupError:
                self._erps[version] = None
        par = self._erps[version]
        if par is None:
            return None
        return par[1].get(pedido or "", [])


# ----------------------------------------------------------------------------- comprobaciones


def comprobar_fantasmas(filas: list[Fila], dirs: dict[int, Path]) -> Comprobacion:
    """Ficheros de la BD que no están en el directorio real de su lote (los `L2-*` del simulado caen aquí)."""
    reales: dict[int, set[str]] = {
        lote: set(listar_pdfs(d)) for lote, d in dirs.items() if d.is_dir()
    }
    fantasmas = [f for f in filas if f.file_id not in reales.get(f.lote, set())]
    return _comprobacion(
        "fantasmas",
        "Ficheros en la BD que no existen en disco",
        [f"{f.file_id} (lote {f.lote})" for f in fantasmas],
        ROJO,
        "Son restos de un ensayo o de un intento anterior. Contaminan `marcar_duplicados` (anoche movieron 20 "
        "decisiones del lote 1) y `package` los metería en la entrega. `uv run python scripts/preflight_lote2.py` "
        "los lista con el DELETE listo; `--limpiar` los borra. Después, `albertitos reprocess --impacted`.",
        [f.file_id for f in fantasmas],
    )


def comprobar_conjunto(
    filas: list[Fila], lotes: list[int], dirs: dict[int, Path], notas: list[str]
) -> Comprobacion:
    """Cada PDF del directorio del lote tiene fichero en la BD y decisión vigente: si no, package se niega."""
    hallazgos: list[str] = []
    ficheros: list[str] = []
    for lote in lotes:
        directorio = dirs.get(lote)
        if directorio is None or not directorio.is_dir():
            notas.append(f"sin lote {lote}: no existe {directorio}")
            continue
        esperados = set(listar_pdfs(directorio))
        en_bd = {f.file_id: f for f in filas if f.lote == lote}
        for fid in sorted(esperados):
            f = en_bd.get(fid)
            if f is None:
                hallazgos.append(f"{fid}: no está ingerido (lote {lote})")
                ficheros.append(fid)
            elif f.decision is None:
                motivo = "sin hechos" if f.hechos is None else "sin decisión vigente"
                hallazgos.append(f"{fid}: {motivo}")
                ficheros.append(fid)
    return _comprobacion(
        "conjunto",
        "Cada PDF del lote tiene decisión vigente",
        hallazgos,
        ROJO,
        "Sin decisión no hay línea, y una línea que falta es NO APTO (`package` se niega). Sin ingerir: "
        "`albertitos ingest --dir <dir> --lote N`. Sin hechos: `albertitos extract --workers 4` (si queda "
        "PENDIENTE, mira el error en `albertitos trace`). Sin decisión: `albertitos reprocess --impacted`.",
        ficheros,
    )


def _grupos_duplicados(filas: list[Fila]) -> dict[str, list[Fila]]:
    """Las mismas claves que `pipeline.etapas.marcar_duplicados`: pedido, y (NIF, nº de factura)."""
    grupos: dict[str, list[Fila]] = {}
    for f in filas:
        h = f.hechos
        if h is None:
            continue
        if h.pedido:
            grupos.setdefault(f"pedido {h.pedido}", []).append(f)
        if h.nif_emisor and h.num_factura:
            grupos.setdefault(f"factura {h.nif_emisor}/{h.num_factura}", []).append(f)
    return {k: v for k, v in grupos.items() if len(v) > 1}


def _describe(clave: str, grupo: list[Fila]) -> str:
    return f"{clave}: " + ", ".join(f"{f.file_id}={f.resultado or 'sin decisión'}" for f in grupo)


def comprobar_duplicados(filas: list[Fila]) -> list[Comprobacion]:
    grupos = _grupos_duplicados(filas)
    doble = {k: g for k, g in grupos.items() if sum(f.resultado == "PAGAR" for f in g) > 1}
    sin_marca_rojo: dict[str, list[Fila]] = {}
    sin_marca_ambar: dict[str, list[Fila]] = {}
    for k, g in grupos.items():
        # la misma regla que marcar_duplicados (ADR-0021): se marca la que repite un pedido de su lote o de uno
        # anterior; la del lote anterior no. Pagar dos veces lo sigue cazando `pago_doble`, sea cual sea el lote.
        deben = [f for f in g if any(o is not f and o.lote <= f.lote for o in g)]
        if all(
            Aviso.DUPLICADO_SOSPECHOSO in f.hechos.avisos for f in deben if f.hechos is not None
        ):
            continue
        (sin_marca_rojo if any(f.resultado == "PAGAR" for f in deben) else sin_marca_ambar)[k] = g
    que_hacer = (
        "`marcar_duplicados` sólo corre dentro de `run` y de `reprocess`: con pasos sueltos (extract, "
        "hechos import, decide) no se ejecuta. Ejecuta `albertitos reprocess --impacted` (o `run` entero) y "
        "repite la auditoría. Si el grupo mezcla lotes, la política es de Mónica (ADR-0006)."
    )
    return [
        _comprobacion(
            "pago_doble",
            "Mismo pedido o misma factura en PAGAR más de una vez",
            [_describe(k, g) for k, g in doble.items()],
            ROJO,
            "La norma lo prohíbe por escrito: «Nunca pagar dos veces el mismo pedido». "
            + que_hacer,
            [f.file_id for g in doble.values() for f in g if f.resultado == "PAGAR"],
        ),
        _comprobacion(
            "duplicado_sin_marcar_pagar",
            "Duplicado sin marcar con alguna factura en PAGAR",
            [_describe(k, g) for k, g in sin_marca_rojo.items()],
            ROJO,
            que_hacer,
            [f.file_id for g in sin_marca_rojo.values() for f in g],
        ),
        _comprobacion(
            "duplicado_sin_marcar",
            "Duplicado sin marcar (ninguna en PAGAR)",
            [_describe(k, g) for k, g in sin_marca_ambar.items()],
            AMBAR,
            "No cambia ningún PAGAR hoy, pero indica pasos sueltos. " + que_hacer,
            [f.file_id for g in sin_marca_ambar.values() for f in g],
        ),
    ]


def _incoherencias_pagar(f: Fila, snaps: Snapshots) -> list[str]:
    """Lo que tiene que ser cierto de una factura que se paga, contra el maestro y el ERP con que se decidió."""
    h, d = f.hechos, f.decision
    if h is None:
        return ["PAGAR sin hechos"]
    m = snaps.maestro(str(d["maestro_version"]))
    if m is None:
        return [f"el maestro {d['maestro_version']} ya no está en la BD"]
    malos: list[str] = []
    pedido = m.pedidos.get(h.pedido or "")
    proveedor = m.proveedores.get(pedido.proveedor_id) if pedido else None
    if pedido is None:
        malos.append(f"pedido {h.pedido} no está en el Excel")
    elif proveedor is None:
        malos.append(f"el proveedor {pedido.proveedor_id} del pedido no está en el maestro")
    else:
        if normalizar_iban(h.iban or "") != normalizar_iban(proveedor.iban):
            malos.append(f"IBAN ≠ {proveedor.id}")
        if normalizar_nif(h.nif_emisor or "") != normalizar_nif(proveedor.nif):
            malos.append(f"NIF {h.nif_emisor} ≠ {proveedor.id} {proveedor.nif}")
        if h.total is None or abs(h.total - pedido.importe_total) > CENT:
            malos.append(f"total {h.total} ≠ pedido {pedido.importe_total}")
    asientos = snaps.asientos(str(d["erp_version"]), h.pedido)
    if asientos is None:
        malos.append(f"el ERP {d['erp_version']} ya no está en la BD")
    elif not asientos:
        malos.append(f"sin asiento en el ERP {d['erp_version']}")
    else:
        if any(a.estado == "PAGADA" for a in asientos):
            malos.append("el asiento ya figura PAGADA")
        if h.total is not None and all(abs(a.importe_esperado - h.total) > CENT for a in asientos):
            malos.append(f"el ERP espera {asientos[0].importe_esperado}")
    corte = str(d["fecha_corte"])
    if h.fecha is None:
        malos.append("sin fecha")
    elif h.fecha.isoformat() > corte:
        malos.append(f"fecha {h.fecha} posterior al corte {corte}")
    return malos


def comprobar_pagar(filas: list[Fila], lotes: list[int], snaps: Snapshots) -> Comprobacion:
    hallazgos, ficheros = [], []
    for f in filas:
        if f.lote in lotes and f.resultado == "PAGAR":
            malos = _incoherencias_pagar(f, snaps)
            if malos:
                hallazgos.append(f"{f.file_id}: " + " · ".join(malos))
                ficheros.append(f.file_id)
    return _comprobacion(
        "pagar_incoherente",
        "PAGAR que no cuadra con el maestro o el ERP",
        hallazgos,
        ROJO,
        "Una factura en PAGAR tiene que tener pedido en el Excel, IBAN y NIF del proveedor del pedido, el "
        "importe del pedido (±0,01), asiento en el ERP que no esté PAGADA y fecha no futura. Si no, o la "
        "decisión es vieja (hechos, maestro o ERP cambiaron: `albertitos reprocess --impacted`) o la norma "
        "tiene un hueco (a Mónica, con el file_id y `albertitos trace <file_id>`). No se corrige a mano.",
        ficheros,
    )


def comprobar_desfase(filas: list[Fila], lotes: list[int]) -> list[Comprobacion]:
    viejas: dict[str, str] = {}
    reescritas: dict[str, str] = {}
    for f in filas:
        if f.lote not in lotes or f.decision is None or f.hechos is None:
            continue
        if f.decision["hechos_hash"] == SIN_HECHOS:
            viejas[f.file_id] = (
                f"{f.file_id}: contingencia (ADR-0009) y ya hay hechos: se deshace con reprocess"
            )
        elif f.decision["hechos_hash"] != f.hechos_hash:
            viejas[f.file_id] = f"{f.file_id}: decidida con otros hechos ({f.resultado})"
        elif f.hechos_en and datetime.fromisoformat(f.hechos_en) > datetime.fromisoformat(
            str(f.decision["decidido_en"])
        ):
            reescritas[f.file_id] = f"{f.file_id}: hechos reescritos después de decidir"
    return [
        _comprobacion(
            "decision_vieja",
            "Decisión tomada con unos hechos que ya no son los de la BD",
            list(viejas.values()),
            ROJO,
            "Alguien reextrajo o importó hechos y no volvió a decidir: lo entregado no sale de lo que hay. "
            "`albertitos reprocess --impacted` (el linaje las detecta solo).",
            list(viejas),
        ),
        _comprobacion(
            "evidencia_reescrita",
            "Hechos reescritos después de decidir (mismo hash)",
            list(reescritas.values()),
            AMBAR,
            "El hash de los hechos no incluye la evidencia (`texto_sospechoso`), pero R6 la cita en el motivo: "
            "la traza puede estar citando un fragmento viejo. `albertitos reprocess --impacted` las redecide.",
            list(reescritas),
        ),
    ]


def _plano(texto: str) -> str:
    return " ".join(texto.split())


def _laxo(texto: str) -> str:
    return sin_tildes(_plano(texto)).lower()


def _texto_pdf(f: Fila, dirs: dict[int, Path]) -> str | None:
    from albertitos.extract import pdf

    ruta = dirs.get(f.lote, Path("/nonexistent")) / f.file_id
    if not ruta.is_file():
        return None
    return pdf.texto_de(ruta)


def comprobar_evidencia(
    filas: list[Fila], lotes: list[int], dirs: dict[int, Path]
) -> list[Comprobacion]:
    falsas: list[str] = []
    no_literales: list[str] = []
    ids_falsas: list[str] = []
    ids_no_literales: list[str] = []
    for f in filas:
        if f.lote not in lotes or f.hechos is None:
            continue
        n_falsas, n_no_literales = len(falsas), len(no_literales)
        fragmento = f.hechos.texto_sospechoso
        if fragmento is not None and fragmento.strip().lower().strip(".") in NO_ES_FRAGMENTO:
            falsas.append(f"{f.file_id}: texto_sospechoso = {fragmento!r} ({f.resultado})")
        elif fragmento and f.tiene_texto:
            # Sólo con capa de texto hay contra qué cotejar; en una escaneada la evidencia es de la imagen.
            texto = _texto_pdf(f, dirs)
            cita = fragmento.removesuffix("…").strip()
            if texto is None:
                no_literales.append(f"{f.file_id}: no encuentro el PDF para cotejar la evidencia")
            elif _plano(cita) not in _plano(texto):
                if _laxo(cita) in _laxo(texto):
                    no_literales.append(
                        f"{f.file_id}: la evidencia sólo casa sin tildes/mayúsculas"
                    )
                else:
                    falsas.append(f"{f.file_id}: la evidencia no está en el texto del PDF")
        if f.decision is not None:
            for m in json.loads(f.decision["motivos_json"]):
                if m["ok"] or not m["regla_id"].endswith("R6"):
                    continue
                cita_motivo = _CITA_R6.search(m["detalle"])
                if cita_motivo is None:
                    continue
                citado = cita_motivo.group(1)
                if citado.strip().lower().strip(".") in NO_ES_FRAGMENTO:
                    falsas.append(f"{f.file_id}: el motivo de R6 cita {citado!r}")
                elif citado != (fragmento or "")[:300]:
                    falsas.append(
                        f"{f.file_id}: el motivo de R6 cita una evidencia que ya no es la de los hechos"
                    )
        if len(falsas) > n_falsas:
            ids_falsas.append(f.file_id)
        if len(no_literales) > n_no_literales:
            ids_no_literales.append(f.file_id)
    return [
        _comprobacion(
            "evidencia_falsa",
            'Motivo o evidencia falsos ("None", cita que no está en el PDF, cita vieja)',
            falsas,
            ROJO,
            "La traza es lo que se enseña al tribunal y a Alberto: una evidencia falsa es un motivo falso, "
            "aunque el resultado sea prudente. Reextrae el fichero (`albertitos extract --no-solo-pendientes "
            "--fixture <lista>`; desde la caché cuesta 0) y `albertitos reprocess --impacted`. Si cambia el "
            "resultado, avisa a Mónica antes de entregar.",
            ids_falsas,
        ),
        _comprobacion(
            "evidencia_no_literal",
            "Evidencia que no es literal (tildes, mayúsculas o PDF ausente)",
            no_literales,
            AMBAR,
            "Suele ser el LLM normalizando tildes. Mira `albertitos trace <file_id>`; no bloquea la entrega.",
            ids_no_literales,
        ),
    ]


def comprobar_contingencia(filas: list[Fila], lotes: list[int]) -> Comprobacion:
    """ESCALAR de contingencia (ADR-0009, `scripts/contingencia.py`): salida prevista, no un error, pero quien
    entrega tiene que verla. Si después llegan los hechos, `decision_vieja` la marca en rojo."""
    hallazgos, ficheros = [], []
    for f in filas:
        if f.lote not in lotes or f.decision is None:
            continue
        for m in json.loads(f.decision["motivos_json"]):
            if m["regla_id"] == REGLA_CONTINGENCIA and not m["ok"]:
                ev = m.get("evidencia") or {}
                hallazgos.append(
                    f"{f.file_id}: {f.resultado} · último error {ev.get('ultimo_error')} · "
                    f"motivo: {ev.get('motivo')!r}"
                )
                ficheros.append(f.file_id)
    return _comprobacion(
        "contingencia",
        "Decisiones de contingencia (ESCALAR sin hechos, ADR-0009)",
        hallazgos,
        AMBAR,
        'Se entregan como ESCALAR con `"regla":"contingencia.C1"`: nadie pudo leer esas facturas a '
        "tiempo. No bloquea. Si el proveedor vuelve antes de entregar: `albertitos extract --workers 4` y "
        "`albertitos reprocess --impacted` las sustituyen por la decisión de la norma.",
        ficheros,
    )


def comprobar_avisos_en_pagar(filas: list[Fila], lotes: list[int]) -> Comprobacion:
    """PAGAR cuyos hechos traen algún aviso que no es benigno. D2 lo auditó a mano el 19/09 (0 de 443)."""
    hallazgos, ficheros = [], []
    for f in filas:
        if f.lote not in lotes or f.resultado != "PAGAR" or f.hechos is None:
            continue
        raros = [a.value for a in f.hechos.avisos if a not in AVISOS_BENIGNOS]
        if raros:
            hallazgos.append(f"{f.file_id}: {', '.join(raros)}")
            ficheros.append(f.file_id)
    return _comprobacion(
        "pagar_con_avisos",
        "PAGAR con un aviso del extractor que no es benigno",
        hallazgos,
        AMBAR,
        "La norma la paga aunque el extractor avisó de algo que ninguna regla mira. Caso conocido: "
        "`documento_superpuesto` mientras no esté en ANOMALIAS_HUMANO de rules/norma_v3.py (lo decide "
        "Mónica). Mira `albertitos trace <file_id>` y díselo a quien lleve la norma.",
        ficheros,
    )


def comprobar_distribucion(informe: Informe, filas: list[Fila], lotes: list[int]) -> Comprobacion:
    hallazgos = []
    for lote in lotes:
        cuenta: dict[str, int] = {}
        for f in filas:
            if f.lote == lote and f.resultado:
                cuenta[f.resultado] = cuenta.get(f.resultado, 0) + 1
        total = sum(cuenta.values())
        if not total:
            continue
        informe.distribucion[lote] = dict(sorted(cuenta.items()))
        if cuenta.get("ESCALAR", 0) / total > UMBRAL_ESCALAR:
            hallazgos.append(
                f"lote {lote}: ESCALAR {cuenta['ESCALAR']}/{total} > {UMBRAL_ESCALAR:.0%}"
            )
        if cuenta.get("NO_PAGAR", 0) / total > UMBRAL_NO_PAGAR:
            hallazgos.append(
                f"lote {lote}: NO_PAGAR {cuenta['NO_PAGAR']}/{total} > {UMBRAL_NO_PAGAR:.0%}"
            )
    return _comprobacion(
        "distribucion",
        "Reparto de resultados fuera de lo esperable",
        hallazgos,
        AMBAR,
        "No es un error por sí mismo. Compara con la referencia (lote 1 con v3 y ERP v1, tras ADR-0010/0011: 438 PAGAR · "
        "53 ESCALAR · 9 NO_PAGAR) y mira qué regla explica la diferencia.",
    )


def comprobar_confianza(filas: list[Fila], lotes: list[int]) -> Comprobacion:
    bajas = [
        f
        for f in filas
        if f.lote in lotes
        and f.resultado == "PAGAR"
        and f.hechos is not None
        and f.hechos.confianza is not None
        and f.hechos.confianza < 1
    ]
    return _comprobacion(
        "pagar_con_confianza_baja",
        "PAGAR con una lectura reconciliada con el maestro (confianza < 1)",
        [f"{f.file_id}: confianza {f.hechos.confianza}" for f in bajas if f.hechos is not None],
        AMBAR,
        "Son escaneadas cuyas dos lecturas discrepaban y se eligió la respaldada por el maestro y el pedido "
        "(ADR-0003). Es una política pendiente de Mónica (DECISIONES-NORMA, nº 2); se informa, no bloquea.",
        [f.file_id for f in bajas],
    )


def comprobar_entrega_en_disco(
    filas: list[Fila], lotes: list[int], dirs: dict[int, Path], entrega: Path, notas: list[str]
) -> list[Comprobacion]:
    invalidas: list[str] = []
    desfasadas: list[str] = []
    ids_desfasados: list[str] = []
    for lote in lotes:
        ruta = entrega / ENTREGAS[lote]
        if not ruta.is_file():
            notas.append(f"no hay {ruta}: nada que comparar")
            continue
        directorio = dirs.get(lote)
        esperados = listar_pdfs(directorio) if directorio and directorio.is_dir() else []
        inf = validar_jsonl(ruta, esperados, lote)
        if not inf.ok:
            invalidas.append(f"{ruta}: {len(inf.errores)} errores; el primero: {inf.errores[0]}")
            continue
        en_disco = {
            o["file_id"]: o["result"]
            for o in (json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines() if x)
        }
        en_bd = {f.file_id: f.resultado for f in filas if f.lote == lote and f.resultado}
        distintos = sorted(k for k in en_disco if en_disco[k] != en_bd.get(k))
        if distintos:
            desfasadas.append(
                f"{ruta}: {len(distintos)} líneas distintas de la BD, p. ej. "
                + ", ".join(f"{k} {en_disco[k]}→{en_bd.get(k)}" for k in distintos[:3])
            )
            ids_desfasados.extend(distintos)
    return [
        _comprobacion(
            "entrega_invalida",
            "La entrega que hay en disco no pasa el validador",
            invalidas,
            ROJO,
            "No la subas. `make package` la regenera desde la BD (todo o nada) y te dice qué falta o sobra.",
        ),
        _comprobacion(
            "entrega_desfasada",
            "La entrega en disco no es la de las decisiones vigentes",
            desfasadas,
            AMBAR,
            "Se decidió algo después del último `package`. `make package` antes de `/entrega`.",
            ids_desfasados,
        ),
    ]


# ----------------------------------------------------------------------------- orquestación y salida


def auditar(
    conn: sqlite3.Connection,
    dirs: dict[int, Path],
    *,
    lotes: list[int] | None = None,
    entrega: Path | None = None,
    ruta_db: str = "",
) -> Informe:
    """La firma de `package.Auditor`: `auditar(conn, {lote: dir_pdfs})`. Por defecto audita los lotes de `dirs`.

    Sin `entrega` no compara con los JSONL en disco: `package` llama antes de sustituirlos, y los viejos no
    cuentan. La CLI (`scripts/auditoria_entrega.py`) sí los compara.
    """
    lotes = sorted(dirs) if lotes is None else lotes
    informe = Informe(db=ruta_db, lotes=lotes)
    filas = cargar_filas(conn)
    snaps = Snapshots(conn)
    comps = informe.comprobaciones
    comps.append(comprobar_fantasmas(filas, dirs))
    comps.append(comprobar_conjunto(filas, lotes, dirs, informe.notas))
    comps.extend(comprobar_duplicados(filas))
    comps.append(comprobar_pagar(filas, lotes, snaps))
    comps.extend(comprobar_desfase(filas, lotes))
    comps.extend(comprobar_evidencia(filas, lotes, dirs))
    comps.append(comprobar_contingencia(filas, lotes))
    comps.append(comprobar_avisos_en_pagar(filas, lotes))
    comps.append(comprobar_distribucion(informe, filas, lotes))
    comps.append(comprobar_confianza(filas, lotes))
    if entrega is not None:
        comps.extend(comprobar_entrega_en_disco(filas, lotes, dirs, entrega, informe.notas))
    return informe


def texto(informe: Informe) -> str:
    lineas = [f"Auditoría de entrega · {informe.db} · lotes {informe.lotes}"]
    for lote, cuenta in informe.distribucion.items():
        lineas.append(f"  lote {lote}: {sum(cuenta.values())} decisiones · {cuenta}")
    lineas.append("")
    lineas.append(f"{'nivel':<6} {'n':>4}  comprobación")
    for c in informe.comprobaciones:
        lineas.append(f"{c.nivel:<6} {c.n:>4}  {c.titulo}")
    for c in informe.comprobaciones:
        if c.nivel == OK:
            continue
        lineas.append("")
        lineas.append(f"[{c.nivel}] {c.titulo} · {c.n}")
        lineas.extend(f"  - {e}" for e in c.ejemplos)
        if c.n > len(c.ejemplos):
            lineas.append(f"  … y {c.n - len(c.ejemplos)} más")
        lineas.append(f"  qué hacer: {c.que_hacer}")
    for n in informe.notas:
        lineas.append(f"nota: {n}")
    lineas.append("")
    lineas.append(
        "VEREDICTO: VERDE · se puede empaquetar"
        if informe.ok
        else f"VEREDICTO: ROJO · {len(informe.rojos)} comprobación(es) en rojo: NO entregar"
    )
    return "\n".join(lineas)
