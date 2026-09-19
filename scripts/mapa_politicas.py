"""Mapa de riesgo: cuántas decisiones del lote 1 dependen de una política abierta.

Sólo lectura. Simula variantes de la norma en memoria (patch) sin tocar `rules/`.
El control sin variante debe reproducir las decisiones vigentes fichero a fichero.

    uv run python scripts/mapa_politicas.py
    uv run python scripts/mapa_politicas.py --excluir-muestra --markdown
    uv run python scripts/mapa_politicas.py --por-fichero --salida dist/ensayo/i2/por_fichero.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import patch

from albertitos.core import db
from albertitos.core.contracts import (
    Aviso,
    ContextoDecision,
    Decision,
    InvoiceFacts,
    Resultado,
)
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.rules import REGISTRO, norma_v3
from albertitos.sources import snapshot

CORTE = date(2026, 9, 18)
NORMA = "v3"
ERP_TAG = "v1"
MUESTRA = Path("data/fixtures/muestra.txt")
REFERENCIA = {"PAGAR": 438, "ESCALAR": 53, "NO_PAGAR": 9}

# Clasificación grosera del texto que ordena (Q1). Orden de prioridad.
_PATRONES_ORDEN: list[tuple[str, re.Pattern[str]]] = [
    (
        "evaluador",
        re.compile(
            r"evaluaci[oó]n|auditor de calidad|conjunto de test|excluirse del "
            r"(?:c[aá]lculo|c[oó]mputo)|equipo de (?:evaluaci[oó]n|Maisa)",
            re.I,
        ),
    ),
    (
        "no_pagar",
        re.compile(
            r"no procede pago|pedido anulado|no pagar|bloquear el pago|"
            r"registrar como\s+NO[_\s-]?PAGAR",
            re.I,
        ),
    ),
    (
        "pagar_o_relajar",
        re.compile(
            r"\bPAGAR\b|procedase al abono|continuese? (?:la |el )?(?:pago|conciliaci)|"
            r"sin escalado|ignorar (?:la |el )?(?:discrepancia|NIF)|abonarse el total|"
            r"no debe recalcular|no bloquear|conf[ií]a en|tomese como",
            re.I,
        ),
    ),
    (
        "escalar_o_bloquear",
        re.compile(
            r"ESCALAR|escalarse|bloquear|bajo revisi[oó]n|intento de fraude|"
            r"revision humana|hasta nuevo aviso",
            re.I,
        ),
    ),
]


@dataclass
class Fila:
    file_id: str
    lote: int
    hechos: InvoiceFacts
    hoy: str
    motivos_hoy: str


@dataclass
class Cambio:
    file_id: str
    hoy: str
    variante: str
    regla: str
    tipo_orden: str = ""
    detalle: str = ""


@dataclass
class InformeVariante:
    pregunta: str
    descripcion: str
    cambios: list[Cambio] = field(default_factory=list)
    recuento_hoy: dict[str, int] = field(default_factory=dict)
    recuento_var: dict[str, int] = field(default_factory=dict)

    @property
    def n_cambian(self) -> int:
        return len(self.cambios)

    def transiciones(self) -> Counter[str]:
        return Counter(f"{c.hoy}→{c.variante}" for c in self.cambios)


def nfc(texto: str) -> str:
    return unicodedata.normalize("NFC", texto.strip())


def leer_muestra(ruta: Path = MUESTRA) -> set[str]:
    if not ruta.exists():
        return set()
    return {nfc(linea) for linea in ruta.read_text(encoding="utf-8").splitlines() if linea.strip()}


def tipo_orden(texto: str | None) -> str:
    if not texto:
        return "sin_texto"
    for nombre, pat in _PATRONES_ORDEN:
        if pat.search(texto):
            return nombre
    return "otro"


def cargar_filas(conn, lote: int = 1) -> list[Fila]:
    sql = """
        SELECT f.file_id, f.lote, f.sha256, h.hechos_json, d.resultado, d.motivos_json
        FROM ficheros f
        JOIN hechos h ON h.sha256 = f.sha256 AND h.extractor_version = ?
        JOIN decisiones d ON d.sha256 = f.sha256 AND d.vigente = 1
        WHERE f.lote = ?
        ORDER BY f.file_id
    """
    out: list[Fila] = []
    for r in conn.execute(sql, (EXTRACTOR_VERSION, lote)):
        out.append(
            Fila(
                file_id=nfc(r["file_id"]),
                lote=int(r["lote"]),
                hechos=InvoiceFacts.model_validate_json(r["hechos_json"]),
                hoy=str(r["resultado"]),
                motivos_hoy=r["motivos_json"] or "[]",
            )
        )
    return out


def ctx_de(maestro, erp) -> ContextoDecision:
    return ContextoDecision(
        norma_version=NORMA,
        fecha_corte=CORTE,
        maestro_version=maestro.version,
        erp_version=erp.version,
    )


def decidir(h: InvoiceFacts, maestro, erp, ctx: ContextoDecision) -> Decision:
    return REGISTRO[NORMA].decidir(h, maestro, erp, ctx)


def primera_regla_ko(d: Decision) -> str:
    for m in d.motivos:
        if not m.ok:
            return m.regla_id
    return ""


def control(filas: list[Fila], maestro, erp) -> list[str]:
    """Devuelve lista de desajustes. Vacía = OK (reproduce vigentes fichero a fichero)."""
    ctx = ctx_de(maestro, erp)
    errores: list[str] = []
    cuenta: Counter[str] = Counter()
    for f in filas:
        d = decidir(f.hechos, maestro, erp, ctx)
        cuenta[d.resultado.value] += 1
        if d.resultado.value != f.hoy:
            errores.append(f"{f.file_id}: vigente={f.hoy} simulado={d.resultado.value}")
    for res, n in REFERENCIA.items():
        if cuenta[res] != n:
            errores.append(f"recuento {res}: simulado={cuenta[res]} referencia={n}")
    if len(filas) != 500:
        errores.append(f"filas lote 1: {len(filas)} (se esperaban 500)")
    return errores


def _informe(
    pregunta: str,
    descripcion: str,
    filas: list[Fila],
    maestro,
    erp,
    decidir_var: Callable[..., Decision],
    *,
    baseline: dict[str, Decision] | None = None,
    extra: Callable[[Fila, Decision, Decision], dict[str, str]] | None = None,
) -> InformeVariante:
    """Compara la decisión base con `decidir_var`.

    `baseline` es obligatorio cuando `decidir_var` corre bajo un patch de la norma:
    si no, d0 y d1 verían la misma norma parcheada y el diff saldría vacío.
    """
    ctx = ctx_de(maestro, erp)
    inf = InformeVariante(pregunta=pregunta, descripcion=descripcion)
    hoy_c: Counter[str] = Counter()
    var_c: Counter[str] = Counter()
    for f in filas:
        d0 = baseline[f.file_id] if baseline is not None else decidir(f.hechos, maestro, erp, ctx)
        d1 = decidir_var(f.hechos, maestro, erp, ctx)
        hoy_c[d0.resultado.value] += 1
        var_c[d1.resultado.value] += 1
        if d0.resultado != d1.resultado:
            meta = extra(f, d0, d1) if extra else {}
            inf.cambios.append(
                Cambio(
                    file_id=f.file_id,
                    hoy=d0.resultado.value,
                    variante=d1.resultado.value,
                    regla=primera_regla_ko(d0) or primera_regla_ko(d1),
                    tipo_orden=meta.get("tipo_orden", ""),
                    detalle=meta.get("detalle", ""),
                )
            )
    inf.recuento_hoy = dict(hoy_c)
    inf.recuento_var = dict(var_c)
    return inf


def _baseline(filas: list[Fila], maestro, erp) -> dict[str, Decision]:
    ctx = ctx_de(maestro, erp)
    return {f.file_id: decidir(f.hechos, maestro, erp, ctx) for f in filas}


@contextmanager
def _sin_aviso(aviso: Aviso) -> Iterator[None]:
    reducido = set(norma_v3.ANOMALIAS_HUMANO) - {aviso}
    with patch.object(norma_v3, "ANOMALIAS_HUMANO", reducido):
        yield


def variante_q1_pagar_si_solo_texto(filas: list[Fila], maestro, erp) -> InformeVariante:
    """Q1: TEXTO_INSTRUCCION deja de ser anomalía humana → ¿cuántas pasan a PAGAR?"""

    def _extra(f: Fila, d0: Decision, d1: Decision) -> dict[str, str]:
        return {
            "tipo_orden": tipo_orden(f.hechos.texto_sospechoso),
            "detalle": (f.hechos.texto_sospechoso or "")[:200],
        }

    base = _baseline(filas, maestro, erp)
    with _sin_aviso(Aviso.TEXTO_INSTRUCCION):
        return _informe(
            "Q1",
            "TEXTO_INSTRUCCION fuera de ANOMALIAS_HUMANO (hoy ESCALAR → ¿PAGAR?)",
            filas,
            maestro,
            erp,
            decidir,
            baseline=base,
            extra=_extra,
        )


def variante_q2(filas: list[Fila], maestro, erp, *, destino: str) -> InformeVariante:
    """Q2: PEDIDO_ANULADO_SEGUN_PDF → PAGAR (quitar aviso) o forzar NO_PAGAR."""

    if destino == "PAGAR":
        base = _baseline(filas, maestro, erp)
        with _sin_aviso(Aviso.PEDIDO_ANULADO_SEGUN_PDF):
            return _informe(
                "Q2a",
                "PEDIDO_ANULADO_SEGUN_PDF fuera de ANOMALIAS_HUMANO → ¿PAGAR?",
                filas,
                maestro,
                erp,
                decidir,
                baseline=base,
            )

    def forzar_no_pagar(h: InvoiceFacts, m, e, ctx: ContextoDecision) -> Decision:
        d = decidir(h, m, e, ctx)
        if Aviso.PEDIDO_ANULADO_SEGUN_PDF in h.avisos:
            # Misma estructura; sólo cambia el resultado (política hipotética).
            return Decision(
                file_id=d.file_id,
                sha256=d.sha256,
                resultado=Resultado.NO_PAGAR,
                motivos=d.motivos,
                norma_version=d.norma_version,
                fecha_corte=d.fecha_corte,
                hechos_hash=d.hechos_hash,
                maestro_version=d.maestro_version,
                erp_version=d.erp_version,
                decidido_en=d.decidido_en,
            )
        return d

    return _informe(
        "Q2b",
        "PEDIDO_ANULADO_SEGUN_PDF → NO_PAGAR (política hipotética)",
        filas,
        maestro,
        erp,
        forzar_no_pagar,
    )


def variante_q3_objetivos_no_pagar(filas: list[Fila], maestro, erp) -> InformeVariante:
    """Q3: fallo objetivo R1–R4 → NO_PAGAR en vez de ESCALAR (R5 PAGADA ya es NO_PAGAR)."""

    def decidir_frontera(h: InvoiceFacts, m, e, ctx: ContextoDecision) -> Decision:
        motivos = [regla(h, m, e, ctx) for regla in norma_v3.REGLAS]
        fallos = [x for x in motivos if not x.ok]
        if not fallos:
            res = Resultado.PAGAR
        elif any(x.evidencia.get("no_pagar") for x in fallos):
            res = Resultado.NO_PAGAR
        elif any(x.regla_id.endswith(suf) for x in fallos for suf in (".R1", ".R2", ".R3", ".R4")):
            res = Resultado.NO_PAGAR
        else:
            res = Resultado.ESCALAR
        return Decision(
            file_id=h.file_id,
            sha256=h.sha256,
            resultado=res,
            motivos=motivos,
            norma_version=ctx.norma_version,
            fecha_corte=ctx.fecha_corte,
            hechos_hash=h.hash(),
            maestro_version=ctx.maestro_version,
            erp_version=ctx.erp_version,
            decidido_en=datetime.now(UTC),
        )

    return _informe(
        "Q3",
        "Fallo objetivo R1–R4 → NO_PAGAR (hoy ESCALAR)",
        filas,
        maestro,
        erp,
        decidir_frontera,
    )


_RE_EVALUADOR = re.compile(
    r"evaluaci[oó]n|auditor de calidad|conjunto de test|excluirse del "
    r"(?:c[aá]lculo|c[oó]mputo)",
    re.I,
)


def variante_q4_evaluador(filas: list[Fila], maestro, erp) -> InformeVariante:
    """Q4: documentos que se declaran de prueba del evaluador — qué decide hoy (sin cambio).

    No hay variante de norma: se listan los que el texto apunta al evaluador/auditor y su
    decisión vigente. El campo n_cambian del informe es el tamaño del inventario.
    """
    ctx = ctx_de(maestro, erp)
    inf = InformeVariante(
        pregunta="Q4",
        descripcion="Documentos de prueba del evaluador (inventario; decisión vigente)",
    )
    hoy_c: Counter[str] = Counter()
    for f in filas:
        d0 = decidir(f.hechos, maestro, erp, ctx)
        hoy_c[d0.resultado.value] += 1
        texto = f.hechos.texto_sospechoso or ""
        if _RE_EVALUADOR.search(texto):
            inf.cambios.append(
                Cambio(
                    file_id=f.file_id,
                    hoy=d0.resultado.value,
                    variante=d0.resultado.value,
                    regla=primera_regla_ko(d0) or "cumple",
                    tipo_orden="evaluador",
                    detalle=texto[:200],
                )
            )
    inf.recuento_hoy = dict(hoy_c)
    inf.recuento_var = dict(hoy_c)
    return inf


def variante_q5_duplicado_0492(filas: list[Fila], maestro, erp) -> InformeVariante:
    """Q5: PO-2026-0492 — hoy dos ESCALAR; variante: la más antigua PAGAR, la otra NO_PAGAR."""
    duo = [f for f in filas if f.hechos.pedido == "PO-2026-0492"]
    duo_sorted = sorted(
        duo,
        key=lambda f: (f.hechos.fecha or date.max, f.file_id),
    )
    primero = duo_sorted[0].file_id if duo_sorted else None
    segundo = duo_sorted[1].file_id if len(duo_sorted) > 1 else None

    def decidir_dup(h: InvoiceFacts, m, e, ctx: ContextoDecision) -> Decision:
        d = decidir(h, m, e, ctx)
        if h.pedido != "PO-2026-0492":
            return d
        if h.file_id == primero:
            # Quitar el aviso de duplicado en memoria y redecidir.
            h2 = h.model_copy(
                update={
                    "avisos": [a for a in h.avisos if a != Aviso.DUPLICADO_SOSPECHOSO],
                }
            )
            return decidir(h2, m, e, ctx)
        if h.file_id == segundo:
            return Decision(
                file_id=d.file_id,
                sha256=d.sha256,
                resultado=Resultado.NO_PAGAR,
                motivos=d.motivos,
                norma_version=d.norma_version,
                fecha_corte=d.fecha_corte,
                hechos_hash=d.hechos_hash,
                maestro_version=d.maestro_version,
                erp_version=d.erp_version,
                decidido_en=d.decidido_en,
            )
        return d

    return _informe(
        "Q5",
        f"PO-2026-0492: primero ({primero}) PAGAR, segundo ({segundo}) NO_PAGAR",
        filas,
        maestro,
        erp,
        decidir_dup,
    )


def candidatos_limpios_r1_r5(filas: list[Fila], maestro, erp, aviso: Aviso) -> list[Fila]:
    """Facturas con el aviso y R1–R5 OK si se ignora ese aviso (candidatas 'limpias')."""
    ctx = ctx_de(maestro, erp)
    out: list[Fila] = []
    with _sin_aviso(aviso):
        for f in filas:
            if aviso not in f.hechos.avisos:
                continue
            d = decidir(f.hechos, maestro, erp, ctx)
            # Tras quitar el aviso: si PAGAR, R1–R5 (y R6 restante) pasan.
            if d.resultado == Resultado.PAGAR:
                out.append(f)
    return out


def formatear_tabla(informes: list[InformeVariante], *, excluir: set[str]) -> str:
    lineas = [
        "| Pregunta | Descripción | Cambian | Transiciones | Notas |",
        "|---|---|---:|---|---|",
    ]
    for inf in informes:
        cambios = [c for c in inf.cambios if c.file_id not in excluir]
        # Q4: "cambian" = inventario (mismo resultado); contar igual.
        n = len(cambios)
        trans = Counter(f"{c.hoy}→{c.variante}" for c in cambios)
        trans_s = ", ".join(f"{k} {v}" for k, v in sorted(trans.items())) or "—"
        notas = ""
        if inf.pregunta == "Q1":
            tipos = Counter(c.tipo_orden for c in cambios)
            notas = ", ".join(f"{k}={v}" for k, v in sorted(tipos.items()))
        elif inf.pregunta == "Q4":
            notas = f"inventario ({n} docs); decisión vigente sin cambio de norma"
            n = len(cambios)  # show count as inventory
        lineas.append(f"| {inf.pregunta} | {inf.descripcion} | {n} | {trans_s} | {notas} |")
    return "\n".join(lineas)


def escribir_por_fichero(ruta: Path, informes: list[InformeVariante], excluir: set[str]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["pregunta", "file_id", "hoy", "variante", "regla", "tipo_orden", "detalle"],
        )
        w.writeheader()
        for inf in informes:
            for c in inf.cambios:
                if c.file_id in excluir:
                    continue
                w.writerow(
                    {
                        "pregunta": inf.pregunta,
                        "file_id": c.file_id,
                        "hoy": c.hoy,
                        "variante": c.variante,
                        "regla": c.regla,
                        "tipo_orden": c.tipo_orden,
                        "detalle": c.detalle,
                    }
                )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=None, help="BD (por defecto ALBERTITOS_DB)")
    p.add_argument(
        "--por-fichero", action="store_true", help="lista completa (cuidado con muestra)"
    )
    p.add_argument(
        "--salida",
        type=Path,
        default=Path("dist/ensayo/i2/por_fichero.csv"),
        help="CSV de --por-fichero",
    )
    p.add_argument("--markdown", action="store_true", help="tabla markdown a stdout")
    p.add_argument(
        "--excluir-muestra",
        action="store_true",
        help="quita los 21 de muestra.txt de la salida por fichero y de los recuentos publicados",
    )
    p.add_argument(
        "--json",
        type=Path,
        default=None,
        help="vuelca recuentos a un JSON (sin file_id de muestra si --excluir-muestra)",
    )
    args = p.parse_args(argv)

    muestra = leer_muestra()
    excluir = muestra if args.excluir_muestra else set()

    conn = db.conectar(args.db, solo_lectura=True)
    try:
        maestro = snapshot.cargar_maestro_bd(conn)
        erp = snapshot.cargar_erp_bd(conn, ERP_TAG)
        filas = cargar_filas(conn, lote=1)
    finally:
        conn.close()

    errs = control(filas, maestro, erp)
    if errs:
        print(
            "CONTROL FALLIDO: la simulación no reproduce las decisiones vigentes:", file=sys.stderr
        )
        for e in errs[:30]:
            print(f"  - {e}", file=sys.stderr)
        if len(errs) > 30:
            print(f"  … y {len(errs) - 30} más", file=sys.stderr)
        return 2
    print("CONTROL OK: 500/500 fichero a fichero · 438 PAGAR · 53 ESCALAR · 9 NO_PAGAR")

    informes = [
        variante_q1_pagar_si_solo_texto(filas, maestro, erp),
        variante_q2(filas, maestro, erp, destino="PAGAR"),
        variante_q2(filas, maestro, erp, destino="NO_PAGAR"),
        variante_q3_objetivos_no_pagar(filas, maestro, erp),
        variante_q4_evaluador(filas, maestro, erp),
        variante_q5_duplicado_0492(filas, maestro, erp),
    ]

    # Recuentos con y sin muestra para el resumen.
    print()
    print(formatear_tabla(informes, excluir=set()))
    if excluir:
        print()
        print("### Sin los 21 de la muestra")
        print(formatear_tabla(informes, excluir=excluir))

    # Desglose Q1 por tipo de orden (todos / sin muestra).
    q1 = next(i for i in informes if i.pregunta == "Q1")
    for etiqueta, exc in (("todos", set()), ("sin muestra", excluir)):
        tipos = Counter(c.tipo_orden for c in q1.cambios if c.file_id not in exc)
        print(f"Q1 tipos ({etiqueta}): " + ", ".join(f"{k}={v}" for k, v in sorted(tipos.items())))

    limpios_q1 = candidatos_limpios_r1_r5(filas, maestro, erp, Aviso.TEXTO_INSTRUCCION)
    limpios_q2 = candidatos_limpios_r1_r5(filas, maestro, erp, Aviso.PEDIDO_ANULADO_SEGUN_PDF)
    con_texto = sum(1 for f in filas if Aviso.TEXTO_INSTRUCCION in f.hechos.avisos)
    con_anulado = sum(1 for f in filas if Aviso.PEDIDO_ANULADO_SEGUN_PDF in f.hechos.avisos)
    print(f"Con aviso hoy: TEXTO_INSTRUCCION={con_texto} · PEDIDO_ANULADO_SEGUN_PDF={con_anulado}")
    print(
        f"Candidatas 'limpias' (pasan a PAGAR al quitar sólo ese aviso): "
        f"Q1={len(limpios_q1)} · Q2={len(limpios_q2)}"
    )
    q1 = next(i for i in informes if i.pregunta == "Q1")
    print(f"Q1 con aviso que seguirían ESCALAR/NO_PAGAR por otra causa: {con_texto - q1.n_cambian}")

    if args.por_fichero:
        escribir_por_fichero(args.salida, informes, excluir)
        print(f"Lista por fichero → {args.salida} (excluidos {len(excluir)} de muestra)")

    if args.json:
        payload = {
            "control": "ok",
            "referencia": REFERENCIA,
            "excluir_muestra": sorted(excluir),
            "avisos": {
                "texto_instruccion": con_texto,
                "pedido_anulado_segun_pdf": con_anulado,
                "q1_pasan_a_pagar": len(limpios_q1),
                "q2_pasan_a_pagar": len(limpios_q2),
            },
            "preguntas": [],
            "preguntas_todos": [],
        }
        for inf in informes:
            cambios_ex = [c for c in inf.cambios if c.file_id not in excluir]
            payload["preguntas"].append(
                {
                    "id": inf.pregunta,
                    "descripcion": inf.descripcion,
                    "n_cambian": len(cambios_ex),
                    "transiciones": dict(Counter(f"{c.hoy}→{c.variante}" for c in cambios_ex)),
                    "tipos_orden": dict(Counter(c.tipo_orden for c in cambios_ex if c.tipo_orden)),
                    "file_ids": [c.file_id for c in cambios_ex],
                }
            )
            payload["preguntas_todos"].append(
                {
                    "id": inf.pregunta,
                    "n_cambian": inf.n_cambian,
                    "transiciones": dict(inf.transiciones()),
                    "tipos_orden": dict(Counter(c.tipo_orden for c in inf.cambios if c.tipo_orden)),
                    "file_ids": [c.file_id for c in inf.cambios],
                }
            )
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON → {args.json}")

    if args.markdown:
        print()
        print(formatear_tabla(informes, excluir=excluir))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
