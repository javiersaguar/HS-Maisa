"""Consultas de sólo lectura para la consola (Streamlit y el puente HTTP).

Es el único sitio Python que conoce tablas y JSON de snapshots. Si el backend cambia (norma v4, ERP v2,
tabla `identidades`), se cambia aquí y, si hace falta, `console-web/lib/api/mappers.ts`; las páginas no.

No importa `rules/` ni `extract/`. Si un dato no está en la BD, se deja vacío; no se recalcula la norma.
Contrato JSON: snake_case (copia `core/contracts.py`); las colecciones llevan `api` (versión del contrato).
"""

from __future__ import annotations

import json
import sqlite3
import unicodedata
from datetime import datetime
from typing import Any

from albertitos.core import db
from albertitos.core.contracts import ErpSnapshot, Etapa, MasterSnapshot

#: Versión del contrato JSON del puente. Se sube si cambia un nombre o un tipo que el frontend ya lee.
API_VERSION = 1

ETAPAS = [e.value for e in Etapa]
ESTADOS_EVENTO = ("ok", "error", "pendiente", "retry", "skip")
RESULTADOS = ("PAGAR", "ESCALAR", "NO_PAGAR")
ESTADOS_FICHERO = (*RESULTADOS, "PENDIENTE")
PAGE_SIZE_DEFECTO = 15
TRAZA_GLOBAL_LIMITE = 200
RECIENTES_PANEL = 6
#: Dos eventos de ingest/extract separados por más de esto pertenecen a pasadas distintas.
HUECO_PASADA_S = 60.0

_HECHOS_ULTIMOS = """
hechos_ultimos AS (
  SELECT h.*
  FROM hechos h
  JOIN (
    SELECT sha256, MAX(creado_en) AS creado_en FROM hechos GROUP BY sha256
  ) u ON u.sha256 = h.sha256 AND u.creado_en = h.creado_en
)
"""


def nfc(valor: str) -> str:
    return unicodedata.normalize("NFC", valor)


def _json(valor: str | None) -> Any:
    if not valor:
        return None
    try:
        return json.loads(valor)
    except (json.JSONDecodeError, TypeError):
        return None


def _bool(valor: Any) -> bool | None:
    if valor is None:
        return None
    return bool(valor)


def _tabla_existe(conn: sqlite3.Connection, nombre: str) -> bool:
    """Detecta tablas aditivas del backend (hoy sólo `identidades`) sin exigirlas."""
    fila = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (nombre,)
    ).fetchone()
    return fila is not None


def _identidad(conn: sqlite3.Connection, file_id: str) -> dict[str, Any] | None:
    """Si existe `identidades(file_id, sha256, lote)` (P0-1), un `file_id` extra del mismo PDF.

    Devuelve `{"sha256", "lote"}` o None. Si la tabla no está, o tiene otras columnas, None:
    el camino por `ficheros.file_id` sigue valiendo.
    """
    if not _tabla_existe(conn, "identidades"):
        return None
    try:
        fila = conn.execute(
            "SELECT sha256, lote FROM identidades WHERE file_id = ? ORDER BY lote DESC LIMIT 1",
            (file_id,),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    if fila is None:
        return None
    return {"sha256": fila["sha256"], "lote": fila["lote"]}


def _evento(fila: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    d = dict(fila)
    return {
        "file_id": d.get("file_id"),
        "sha256": d.get("sha256"),
        "etapa": d.get("etapa"),
        "estado": d.get("estado"),
        "intento": d.get("intento") or 1,
        "latencia_ms": d.get("latencia_ms"),
        "tokens_in": d.get("tokens_in"),
        "tokens_out": d.get("tokens_out"),
        "coste_eur": d.get("coste_eur"),
        "error_codigo": d.get("error_codigo"),
        "detalle": d.get("detalle"),
        "version": d.get("version"),
        "ts": d.get("ts"),
    }


def _decision_de_fila(fila: sqlite3.Row | dict[str, Any]) -> dict[str, Any] | None:
    d = dict(fila)
    if not d.get("resultado"):
        return None
    return {
        "file_id": d.get("file_id"),
        "sha256": d.get("sha256"),
        "resultado": d["resultado"],
        "motivos": _json(d.get("motivos_json")) or [],
        "norma_version": d.get("norma_version"),
        "fecha_corte": d.get("fecha_corte"),
        "hechos_hash": d.get("hechos_hash"),
        "maestro_version": d.get("maestro_version"),
        "erp_version": d.get("erp_version"),
        "decidido_en": d.get("decidido_en"),
    }


def _fichero_de_fila(fila: sqlite3.Row) -> dict[str, Any]:
    d = dict(fila)
    return {
        "file_id": d["file_id"],
        "sha256": d["sha256"],
        "lote": d["lote"],
        "paginas": d.get("paginas"),
        "tiene_texto": _bool(d.get("tiene_texto")),
        "ingerido_en": d.get("ingerido_en"),
        "hechos": _json(d.get("hechos_json")),
        "decision": _decision_de_fila(d),
        "fuentes": None,
    }


def _where_ficheros(
    q: str | None,
    estado: str | None,
    regla: str | None,
    lote: int | None,
) -> tuple[str, list[Any]]:
    cláusulas: list[str] = []
    params: list[Any] = []
    if q:
        like = f"%{q}%"
        cláusulas.append(
            """(
              f.file_id LIKE ? COLLATE NOCASE
              OR coalesce(json_extract(h.hechos_json, '$.razon_social'), '') LIKE ? COLLATE NOCASE
              OR coalesce(json_extract(h.hechos_json, '$.num_factura'), '') LIKE ? COLLATE NOCASE
              OR coalesce(json_extract(h.hechos_json, '$.pedido'), '') LIKE ? COLLATE NOCASE
              OR coalesce(json_extract(h.hechos_json, '$.nif_emisor'), '') LIKE ? COLLATE NOCASE
            )"""
        )
        params.extend([like, like, like, like, like])
    if estado and estado != "all":
        if estado == "PENDIENTE":
            cláusulas.append("d.resultado IS NULL")
        else:
            cláusulas.append("d.resultado = ?")
            params.append(estado)
    if lote is not None:
        cláusulas.append("f.lote = ?")
        params.append(lote)
    if regla and regla != "all":
        # `regla_id` lleva la versión de la norma ("v3.R6", "v4.R6"): el filtro va sin ella.
        cláusulas.append(
            """EXISTS (
                 SELECT 1 FROM json_each(d.motivos_json) AS m
                 WHERE json_extract(m.value, '$.ok') = 0
                   AND json_extract(m.value, '$.regla_id') LIKE '%.' || ?
               )"""
        )
        params.append(regla)
    sql = (" WHERE " + " AND ".join(cláusulas)) if cláusulas else ""
    return sql, params


_WITH_HECHOS = f"WITH {_HECHOS_ULTIMOS}"

_FROM_FICHEROS = """
FROM ficheros f
LEFT JOIN hechos_ultimos h ON h.sha256 = f.sha256
LEFT JOIN decisiones d ON d.sha256 = f.sha256 AND d.vigente = 1
"""

_SELECT_FICHERO = """
SELECT f.file_id, f.sha256, f.lote, f.paginas, f.tiene_texto, f.ingerido_en,
       h.hechos_json, h.metodo, h.extractor_version,
       d.resultado, d.motivos_json, d.norma_version, d.fecha_corte, d.hechos_hash,
       d.maestro_version, d.erp_version, d.decidido_en
"""


def listar_ficheros(
    conn: sqlite3.Connection,
    *,
    q: str | None = None,
    estado: str | None = None,
    regla: str | None = None,
    lote: int | None = None,
    page: int = 1,
    page_size: int = PAGE_SIZE_DEFECTO,
) -> dict[str, Any]:
    """Una fila por PDF (sha256). Las identidades extra de `identidades` se resuelven en el detalle."""
    page = max(1, page)
    page_size = max(1, min(page_size, 1000))
    where, params = _where_ficheros(q, estado, regla, lote)
    total = conn.execute(
        f"{_WITH_HECHOS} SELECT count(*) n {_FROM_FICHEROS} {where}", params
    ).fetchone()["n"]
    filas = conn.execute(
        f"""{_WITH_HECHOS} {_SELECT_FICHERO} {_FROM_FICHEROS} {where}
            ORDER BY coalesce(d.decidido_en, f.ingerido_en) DESC, f.file_id
            LIMIT ? OFFSET ?""",
        [*params, page_size, (page - 1) * page_size],
    ).fetchall()
    return {
        "api": API_VERSION,
        "items": [_fichero_de_fila(r) for r in filas],
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }


def _cargar_snapshot(
    conn: sqlite3.Connection, tipo: str, version: str | None
) -> tuple[str | None, Any]:
    datos = None
    ver = version
    if version:
        datos = db.cargar_snapshot(conn, tipo, version)
    if datos is None:
        ultimo = db.ultimo_snapshot(conn, tipo)
        if ultimo is None:
            return None, None
        ver, datos = ultimo
    modelo = MasterSnapshot if tipo == "maestro" else ErpSnapshot
    try:
        return ver, modelo.model_validate_json(datos)
    except Exception:
        return ver, None


def _dump(modelo: Any) -> dict[str, Any]:
    return modelo.model_dump(mode="json")


def _fuentes(conn: sqlite3.Connection, fichero: dict[str, Any]) -> dict[str, Any]:
    """Maestro + asientos del ERP para el fichero. Sin snapshot: versiones nulas y listas vacías, no un 500.

    Versiones: las de la decisión vigente; si está PENDIENTE, el snapshot más reciente.
    """
    decision = fichero.get("decision") or {}
    maestro_ver = decision.get("maestro_version")
    erp_ver = decision.get("erp_version")
    out: dict[str, Any] = {
        "maestro_version": maestro_ver,
        "erp_version": erp_ver,
        "proveedor": None,
        "pedido": None,
        "asientos": [],
    }
    hechos = fichero.get("hechos") or {}
    pedido_id = hechos.get("pedido")
    nif = hechos.get("nif_emisor")

    maestro_ver, maestro = _cargar_snapshot(conn, "maestro", maestro_ver)
    erp_ver, erp = _cargar_snapshot(conn, "erp", erp_ver)
    if maestro_ver:
        out["maestro_version"] = maestro_ver
    if erp_ver:
        out["erp_version"] = erp_ver

    if isinstance(maestro, MasterSnapshot):
        pedido = maestro.pedidos.get(pedido_id) if pedido_id else None
        proveedor = None
        if pedido is not None:
            proveedor = maestro.proveedores.get(pedido.proveedor_id)
            out["pedido"] = _dump(pedido)
        if proveedor is None and nif:
            proveedor = maestro.proveedor_por_nif(str(nif))
        if proveedor is not None:
            out["proveedor"] = _dump(proveedor)

    if isinstance(erp, ErpSnapshot) and pedido_id:
        out["asientos"] = [_dump(a) for a in erp.por_pedido().get(str(pedido_id), [])]
    return out


def _fila_fichero(conn: sqlite3.Connection, columna: str, valor: str) -> sqlite3.Row | None:
    return conn.execute(
        f"{_WITH_HECHOS} {_SELECT_FICHERO} {_FROM_FICHEROS} WHERE f.{columna} = ?", (valor,)
    ).fetchone()


def _resolver(conn: sqlite3.Connection, file_id: str) -> tuple[sqlite3.Row | None, dict | None]:
    """Fila de `ficheros` para un `file_id` (NFC). Si no está y hay `identidades`, por su sha256."""
    fid = nfc(file_id)
    fila = _fila_fichero(conn, "file_id", fid)
    if fila is not None:
        return fila, None
    identidad = _identidad(conn, fid)
    if identidad is None:
        return None, None
    return _fila_fichero(conn, "sha256", str(identidad["sha256"])), identidad


def fichero(conn: sqlite3.Connection, file_id: str) -> dict[str, Any] | None:
    fid = nfc(file_id)
    fila, identidad = _resolver(conn, fid)
    if fila is None:
        return None
    out = _fichero_de_fila(fila)
    if identidad is not None:
        # El mismo PDF con otro nombre: la UI lo ve por el file_id que pidió, sin pisar el original.
        out["file_id"] = fid
        if identidad.get("lote") is not None:
            out["lote"] = int(identidad["lote"])
        if out["decision"]:
            out["decision"]["file_id"] = fid
    out["fuentes"] = _fuentes(conn, out)
    return out


def estados(conn: sqlite3.Connection, file_ids: list[str]) -> list[dict[str, Any]]:
    """Resultado de cada file_id (copias exactas incluidas): el de la decisión vigente, PENDIENTE si
    está ingerido sin ella, None si no llegó a ingerirse (PDF ilegible). Sin `fuentes`: es el poll
    de la bandeja, cada segundo."""
    out = []
    for fid in file_ids:
        fila, _identidad = _resolver(conn, fid)
        estado = None if fila is None else (fila["resultado"] or "PENDIENTE")
        out.append({"file_id": nfc(fid), "estado": estado})
    return out


def _resumen_etapa(conn: sqlite3.Connection, etapa: str) -> dict[str, Any]:
    por_estado = {e: 0 for e in ESTADOS_EVENTO}
    for r in conn.execute(
        "SELECT estado, count(*) n FROM eventos WHERE etapa = ? GROUP BY estado", (etapa,)
    ):
        por_estado[str(r["estado"])] = int(r["n"])
    agg = conn.execute(
        """SELECT count(*) eventos, round(avg(latencia_ms)) lat_media_ms,
                  coalesce(sum(intento > 1), 0) reintentos,
                  coalesce(sum(tokens_in), 0) tokens_in,
                  coalesce(sum(tokens_out), 0) tokens_out,
                  round(coalesce(sum(coste_eur), 0), 4) coste_eur,
                  max(ts) ultimo_ts, max(version) version,
                  count(DISTINCT CASE WHEN estado = 'ok' THEN file_id END) ficheros_ok
           FROM eventos WHERE etapa = ?""",
        (etapa,),
    ).fetchone()
    return {
        "etapa": etapa,
        "eventos": int(agg["eventos"] or 0),
        "ficheros_ok": int(agg["ficheros_ok"] or 0),
        "por_estado": por_estado,
        "latencia_media_ms": agg["lat_media_ms"],
        "reintentos": int(agg["reintentos"] or 0),
        "tokens_in": int(agg["tokens_in"] or 0),
        "tokens_out": int(agg["tokens_out"] or 0),
        "coste_eur": float(agg["coste_eur"] or 0),
        "version": agg["version"],
        "ultimo_evento_en": agg["ultimo_ts"],
    }


def etapas(conn: sqlite3.Connection) -> dict[str, Any]:
    n_ficheros = conn.execute("SELECT count(*) n FROM ficheros").fetchone()["n"]
    recientes = conn.execute("SELECT * FROM eventos ORDER BY ts DESC, id DESC LIMIT 10").fetchall()
    return {
        "api": API_VERSION,
        "ficheros": int(n_ficheros),
        "etapas": [_resumen_etapa(conn, e) for e in ETAPAS],
        "recientes": [_evento(r) for r in recientes],
    }


def eventos(
    conn: sqlite3.Connection, *, etapa: str | None = None, limit: int = 12
) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 200))
    if etapa:
        filas = conn.execute(
            "SELECT * FROM eventos WHERE etapa = ? ORDER BY ts DESC, id DESC LIMIT ?",
            (etapa, limit),
        ).fetchall()
    else:
        filas = conn.execute(
            "SELECT * FROM eventos ORDER BY ts DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_evento(r) for r in filas]


def _ts_a_epoch(valor: str | None) -> float | None:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _ultima_pasada(conn: sqlite3.Connection) -> dict[str, Any] | None:
    """La última ráfaga de eventos ingest/extract: ficheros distintos, duración y ritmo.

    Los eventos de ficheros vivos se recorren del más nuevo al más viejo; un hueco mayor que
    `HUECO_PASADA_S` cierra la pasada. Así el ritmo es el del último run, no 500 / (sábado − viernes).
    """
    filas = conn.execute(
        """SELECT ts, coalesce(sha256, file_id) clave FROM eventos
           WHERE etapa IN ('ingest', 'extract')
             AND (sha256 IN (SELECT sha256 FROM ficheros) OR file_id IN (SELECT file_id FROM ficheros))
           ORDER BY ts DESC, id DESC"""
    ).fetchall()
    claves: set[str] = set()
    t_fin = t_ini = anterior = None
    hasta = desde = None
    for fila in filas:
        t = _ts_a_epoch(fila["ts"])
        if t is None:
            continue
        if anterior is not None and anterior - t > HUECO_PASADA_S:
            break
        if t_fin is None:
            t_fin, hasta = t, fila["ts"]
        t_ini, desde = t, fila["ts"]
        anterior = t
        claves.add(str(fila["clave"]))
    if t_fin is None or t_ini is None:
        return None
    segundos = round(t_fin - t_ini, 3)
    return {
        "ficheros": len(claves),
        "segundos": segundos,
        "desde": desde,
        "hasta": hasta,
        "ficheros_s": round(len(claves) / segundos, 2) if segundos > 0 else None,
    }


def _operacion(conn: sqlite3.Connection) -> dict[str, Any]:
    """Cifras de operación del panel.

    - `coste_eur`: lo que costó la extracción **vigente** (por fichero, los eventos `extract` desde su
      último intento 1). Es el coste de los hechos que deciden hoy; una relectura de caché cuesta 0.
    - `coste_eur_historico`: todo lo gastado en la BD, incluidos runs anteriores. Es lo que asusta en
      `status`; el panel lo enseña como contexto, no como cifra principal.
    - `ficheros_s` / `ventana`: la última pasada de ingest/extract (`_ultima_pasada`).
    """
    pasada = _ultima_pasada(conn)
    coste_vigente = conn.execute(
        """WITH inicio AS (
             SELECT sha256, max(ts) ts FROM eventos
             WHERE etapa = 'extract' AND intento <= 1 AND sha256 IN (SELECT sha256 FROM ficheros)
             GROUP BY sha256
           )
           SELECT round(coalesce(sum(e.coste_eur), 0), 4) n
           FROM eventos e JOIN inicio i ON i.sha256 = e.sha256 AND e.ts >= i.ts
           WHERE e.etapa = 'extract'"""
    ).fetchone()["n"]
    coste_total = conn.execute(
        "SELECT round(coalesce(sum(coste_eur), 0), 4) n FROM eventos"
    ).fetchone()["n"]
    reintentos = conn.execute(
        """SELECT coalesce(sum(intento > 1), 0) n FROM eventos e
           WHERE e.file_id IN (SELECT file_id FROM ficheros) OR e.sha256 IN (SELECT sha256 FROM ficheros)"""
    ).fetchone()["n"]
    llm = conn.execute(
        f"""WITH {_HECHOS_ULTIMOS}
            SELECT count(*) n,
                   sum(CASE WHEN metodo IN ('llm_texto', 'llm_vision') THEN 1 ELSE 0 END) llm
            FROM hechos_ultimos"""
    ).fetchone()
    pct = None
    if llm and llm["n"]:
        pct = round(1000 * int(llm["llm"] or 0) / int(llm["n"])) / 10
    return {
        "ficheros_s": pasada["ficheros_s"] if pasada else None,
        "ventana": pasada,
        "coste_eur": float(coste_vigente or 0),
        "coste_eur_historico": float(coste_total or 0),
        "reintentos": int(reintentos or 0),
        "pct_llm": pct,
    }


def _versiones(conn: sqlite3.Connection) -> dict[str, Any]:
    """Versiones que deciden hoy. `norma` es la de la decisión vigente más reciente (nunca un literal);
    `normas` reparte las vigentes por versión, para el día en que conviven v3 y v4."""
    normas = [
        {"norma": r["norma_version"], "ficheros": int(r["n"])}
        for r in conn.execute(
            """SELECT norma_version, count(*) n FROM decisiones WHERE vigente = 1
               GROUP BY norma_version ORDER BY max(decidido_en) DESC"""
        )
    ]
    dec = conn.execute(
        """SELECT norma_version, maestro_version, erp_version
           FROM decisiones WHERE vigente = 1 ORDER BY decidido_en DESC LIMIT 1"""
    ).fetchone()
    ext = conn.execute(
        "SELECT extractor_version FROM hechos ORDER BY creado_en DESC LIMIT 1"
    ).fetchone()
    maestro = db.ultimo_snapshot(conn, "maestro")
    erp = db.ultimo_snapshot(conn, "erp")
    return {
        "norma": dec["norma_version"] if dec else None,
        "normas": normas,
        "maestro": (dec["maestro_version"] if dec else None) or (maestro[0] if maestro else None),
        "erp": (dec["erp_version"] if dec else None) or (erp[0] if erp else None),
        "extractor": ext["extractor_version"] if ext else None,
    }


def panel(conn: sqlite3.Connection) -> dict[str, Any]:
    n_ficheros = int(conn.execute("SELECT count(*) n FROM ficheros").fetchone()["n"])
    por_lote = [
        {"lote": int(r["lote"]), "ficheros": int(r["n"])}
        for r in conn.execute("SELECT lote, count(*) n FROM ficheros GROUP BY lote ORDER BY lote")
    ]
    por_estado = {k: 0 for k in ESTADOS_FICHERO}
    for r in conn.execute(
        """SELECT coalesce(d.resultado, 'PENDIENTE') estado, count(*) n
           FROM ficheros f
           LEFT JOIN decisiones d ON d.sha256 = f.sha256 AND d.vigente = 1
           GROUP BY estado"""
    ):
        por_estado[r["estado"]] = int(r["n"])
    decididos = max(n_ficheros - por_estado["PENDIENTE"], 1)
    distribucion = [
        {
            "resultado": res,
            "count": por_estado[res],
            "percent": round(100 * por_estado[res] / decididos),
        }
        for res in RESULTADOS
    ]
    por_mes = [
        {"mes": r["mes"], "ficheros": int(r["n"])}
        for r in conn.execute(
            f"""WITH {_HECHOS_ULTIMOS}
                SELECT substr(json_extract(h.hechos_json, '$.fecha'), 1, 7) mes, count(*) n
                FROM hechos_ultimos h
                WHERE json_extract(h.hechos_json, '$.fecha') IS NOT NULL
                GROUP BY mes ORDER BY mes"""
        )
        if r["mes"]
    ]
    recientes = conn.execute(
        f"""{_WITH_HECHOS} {_SELECT_FICHERO} {_FROM_FICHEROS}
            ORDER BY coalesce(d.decidido_en, f.ingerido_en) DESC, f.file_id
            LIMIT ?""",
        (RECIENTES_PANEL,),
    ).fetchall()
    return {
        "api": API_VERSION,
        "ficheros": n_ficheros,
        "por_lote": por_lote,
        "por_estado": por_estado,
        "distribucion": distribucion,
        "versiones": _versiones(conn),
        "operacion": _operacion(conn),
        "etapas": [_resumen_etapa(conn, e) for e in ETAPAS],
        "por_mes": por_mes,
        "recientes": [_fichero_de_fila(r) for r in recientes],
    }


def salud(conn: sqlite3.Connection | None) -> dict[str, Any]:
    """Lo mínimo para que la UI sepa si habla con una BD real y de qué tamaño. Sin BD, `bd` es None."""
    out: dict[str, Any] = {"ok": True, "lectura": True, "api": API_VERSION, "bd": None}
    if conn is None:
        return out
    n = int(conn.execute("SELECT count(*) n FROM ficheros").fetchone()["n"])
    vigentes = int(
        conn.execute("SELECT count(*) n FROM decisiones WHERE vigente = 1").fetchone()["n"]
    )
    ultimo = conn.execute("SELECT max(ts) ts FROM eventos").fetchone()["ts"]
    out["bd"] = {
        "ficheros": n,
        "decisiones_vigentes": vigentes,
        "pendientes": max(n - vigentes, 0),
        "ultimo_evento_en": ultimo,
        "identidades": _tabla_existe(conn, "identidades"),
        "versiones": _versiones(conn),
    }
    return out


def _motivo_paso(
    file_id: str, motivo: dict[str, Any], decision: dict[str, Any], idx: int
) -> dict[str, Any]:
    return {
        "id": f"mo-{file_id}-{motivo.get('regla_id', idx)}",
        "tipo": "motivo",
        "file_id": file_id,
        "ts": decision.get("decidido_en"),
        "motivo": motivo,
        "norma_version": decision.get("norma_version") or "—",
        "resultado": decision.get("resultado") or "ESCALAR",
    }


def _evento_paso(ev: dict[str, Any], idx: int) -> dict[str, Any]:
    fid = ev.get("file_id")
    return {
        "id": f"ev-{fid}-{ev.get('etapa')}-{ev.get('intento')}-{idx}",
        "tipo": "evento",
        "file_id": fid,
        "ts": ev.get("ts"),
        "evento": ev,
    }


def _pasa_filtro(paso: dict[str, Any], etapa: str | None, categoria: str | None) -> bool:
    if etapa:
        if paso["tipo"] == "evento":
            if paso["evento"].get("etapa") != etapa:
                return False
        elif not (etapa == "decide"):
            return False
    if not categoria or categoria == "all":
        return True
    if categoria == "norma":
        return paso["tipo"] == "motivo"
    if categoria == "incidencias":
        if paso["tipo"] == "evento":
            return paso["evento"].get("estado") != "ok"
        return not bool(paso["motivo"].get("ok"))
    if paso["tipo"] == "evento":
        return paso["evento"].get("etapa") == categoria
    return categoria == "decide"


def traza_pasos(
    conn: sqlite3.Connection,
    *,
    file_id: str | None = None,
    etapa: str | None = None,
    categoria: str | None = None,
) -> list[dict[str, Any]] | None:
    """Chain of Work plana: un paso por evento (orden `ts`) y, tras el `decide`, un paso por motivo
    de la decisión **vigente**. Con `file_id` inexistente devuelve None (404)."""
    if file_id:
        fid = nfc(file_id)
        cruda = db.traza(conn, fid)
        if cruda.get("fichero") is None:
            fila, identidad = _resolver(conn, fid)
            if fila is None or identidad is None:
                return None
            cruda = db.traza(conn, str(fila["file_id"]))
            if cruda.get("fichero") is None:
                return None
        eventos_f = [_evento(e) for e in cruda["eventos"]]
        vigente = next((d for d in reversed(cruda["decisiones"]) if d.get("vigente")), None)
        decision = _decision_de_fila(vigente) if vigente else None
        # Los motivos son de la vigente: van una vez, tras el último decide que decidió (no skip).
        # Tras cada decide se repetían con el mismo id en un fichero decidido en varias pasadas.
        ultimo_decide = max(
            (
                i
                for i, ev in enumerate(eventos_f)
                if ev.get("etapa") == "decide" and ev.get("estado") != "skip"
            ),
            default=None,
        )
        pasos: list[dict[str, Any]] = []
        for i, ev in enumerate(eventos_f):
            ev["file_id"] = fid
            pasos.append(_evento_paso(ev, i))
            if i == ultimo_decide and decision:
                for j, m in enumerate(decision["motivos"]):
                    pasos.append(_motivo_paso(fid, m, decision, j))
        if decision and not any(p["tipo"] == "motivo" for p in pasos):
            # Decisión sin evento `decide` (p. ej. hechos importados): los motivos van al final.
            for j, m in enumerate(decision["motivos"]):
                pasos.append(_motivo_paso(fid, m, decision, j))
        return [p for p in pasos if _pasa_filtro(p, etapa, categoria)]

    pasos = []
    for i, ev in enumerate(eventos(conn, etapa=None, limit=TRAZA_GLOBAL_LIMITE)):
        pasos.append(_evento_paso(ev, i))
    for r in conn.execute(
        """SELECT file_id, sha256, resultado, motivos_json, norma_version, fecha_corte,
                  hechos_hash, maestro_version, erp_version, decidido_en
           FROM decisiones WHERE vigente = 1 ORDER BY decidido_en DESC LIMIT 80"""
    ):
        decision = _decision_de_fila(r)
        if not decision:
            continue
        for j, m in enumerate(decision["motivos"]):
            pasos.append(_motivo_paso(r["file_id"], m, decision, j))
    filtrados = [p for p in pasos if _pasa_filtro(p, etapa, categoria)]
    filtrados.sort(key=lambda p: p.get("ts") or "", reverse=True)
    return filtrados[:TRAZA_GLOBAL_LIMITE]
