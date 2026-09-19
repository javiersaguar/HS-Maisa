"""Etapa extract: ficheros pendientes → InvoiceFacts en la BD, con eventos. Dueño: Javier (agente A1).

Firma CONGELADA (la llaman pipeline/etapas.py y cli.py):

    extraer(conn, *, solo_pendientes=True, fixture=None, workers=1) -> ResumenExtraccion

Por fichero: texto (o imagen si es escaneado) → plantilla determinista si A2 la reconoce (coste 0) →
si no, LLM (texto o visión, con caché por sha256) → validadores → hechos en BD + evento EXTRACT.
Si el LLM falla (caído, 429 agotado, respuesta inválida, presupuesto, caos): evento PENDIENTE con
error_codigo y se sigue con el siguiente. Nada revienta el lote; sin hechos no hay decisión.
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from albertitos.core import db
from albertitos.core.contracts import (
    Aviso,
    EstadoEvento,
    Etapa,
    Event,
    InvoiceFacts,
    MasterSnapshot,
    Proveedor,
)
from albertitos.core.versions import EXTRACTOR_VERSION
from albertitos.extract import pdf, plantillas, validadores
from albertitos.extract.llm import ClienteLLM, ErrorLLM, EstadoLLM
from albertitos.formatos import normalizar_nif, sin_tildes

log = logging.getLogger(__name__)

DIRECTORIOS = {
    1: Path(os.environ.get("ALBERTITOS_DIR_CAJA", "data/caja/facturas")),
    2: Path(
        os.environ.get("ALBERTITOS_DIR_LOTE2", "data/lote2/facturas")
    ),  # ensayos: apuntar a un lote simulado
}
DPI_VISION = int(os.environ.get("ALBERTITOS_DPI_VISION", "150"))
# Segunda lectura de cada escaneada: recorte de la parte superior (identificadores) a más resolución.
# Medido el 18/09: a 130 dpi la segunda lectura era PEOR que la primera (B99 por B98, 51,27 por 61,27) y
# generaba discrepancias falsas; a 200 dpi la página entera dispara los tokens y qwen se pierde. El recorte
# superior a 200 dpi cuesta lo mismo que la página a 150 y lee mejor NIF/IBAN/pedido.
DPI_VISION_2 = int(os.environ.get("ALBERTITOS_DPI_VISION_2", "200"))
FRACCION_SUPERIOR_2 = float(os.environ.get("ALBERTITOS_FRACCION_SUPERIOR_2", "0.55"))
VISION_DOBLE = os.environ.get("ALBERTITOS_VISION_DOBLE", "1") != "0"
# Sólo se comparan los campos de identidad (los importes ya los cruzan validadores, maestro y ERP).
CAMPOS_SEGUNDA_LECTURA = (
    "nif_emisor",
    "iban",
    "pedido",
)  # num_factura no decide nada: no se compara
# Tercera lectura (ADR-0017): sólo si las dos primeras discrepan en NIF, IBAN o pedido. Recorte del 35 % superior
# a 300 dpi y gana el valor que repiten 2 de las 3 lecturas, SIN mirar el maestro: así la R1 sigue pudiendo
# fallar (con la reconciliación, el IBAN elegido era el del maestro por construcción). Medido el 19/09 sobre las
# 10 escaneadas con discrepancia: desempata bien 006/009/011/012 (comprobado mirando la imagen) y ninguna trampa
# (fax, copia_0518, 016, 021, 023) pasa a coincidir con el maestro. El recorte del 55 % a 300 dpi leía peor
# (falló el IBAN de 006 y el de 011): menos página, más atención a la línea de identificadores.
TERCERA_LECTURA = os.environ.get("ALBERTITOS_VISION_TERCERA", "1") != "0"
DPI_VISION_3 = int(os.environ.get("ALBERTITOS_DPI_VISION_3", "300"))
FRACCION_SUPERIOR_3 = float(os.environ.get("ALBERTITOS_FRACCION_SUPERIOR_3", "0.35"))
VARIANTE_3 = f"sup{round(FRACCION_SUPERIOR_3 * 100)}_{DPI_VISION_3}"
# El IBAN también se desempata (ADR-0017). Se probó a no hacerlo por scan_011 (Miguel leía ES83 donde dos
# lecturas leían ES93), pero escalaba 006 y 009, dos facturas limpias con un dígito mal leído en una lectura.
# Revisada de nuevo, scan_011 puede ser un 93: con mayoría, 26/26 de las escaneadas con respuesta conocida;
# sin ella, 24/26.
CAMPOS_DESEMPATE = ("nif_emisor", "iban", "pedido")
# Lo que la tercera lectura no desempata: se elige la lectura que coincide con el maestro Y con el proveedor del
# pedido; queda en el evento y baja `confianza` (la norma escala, ADR-0011). Sin esa evidencia, el desacuerdo se
# queda como DISCREPANCIA_EXTRACTORES (la norma escala).
RECONCILIAR_MAESTRO = os.environ.get("ALBERTITOS_RECONCILIAR_MAESTRO", "1") != "0"
# Importes (ADR-0017): la segunda lectura también ve base, IVA, total y líneas. Si las cuentas de la principal
# fallan, se toma el bloque de importes de otra lectura cuyas cuentas cuadran; si ninguna, una lectura más de la
# página entera a 200 dpi, que sólo se usa si cuadra. Criterio independiente: las cuentas de la propia factura, no
# el maestro ni el pedido (eso lo comprueba después la R2). Medido el 19/09: scan_001 (51,27 leído 61,27) y
# scan_014 (896,03 leído 898,03) escalaban por `importe_ambiguo`, y en la Caja ese aviso sólo salta en esas dos.
# En scan_001 cada una de las dos lecturas falló un dígito distinto: sólo la lectura extra la cuadra.
IMPORTES_POR_CUENTAS = os.environ.get("ALBERTITOS_IMPORTES_POR_CUENTAS", "1") != "0"
DPI_VISION_IMPORTES = int(os.environ.get("ALBERTITOS_DPI_VISION_IMPORTES", "200"))
VARIANTE_IMPORTES = f"pag{DPI_VISION_IMPORTES}"
CAMPOS_IMPORTE = ("base", "iva_pct", "iva", "total", "lineas")
CONFIANZA_RECONCILIADA = 0.6
# Una escaneada puede traer OTRA factura encima o transparentándose. El modelo no tiene dónde decirlo y lo
# deja en `texto_sospechoso`: en scan_025 (Limpiezas Turia, P004) la segunda lectura devolvió "Electricidad
# Montcada S.A. NIF: A48990201 Cuenta de abono …", que es P006. Si un fragmento nombra a un proveedor del
# maestro que no es el de la factura, eso no es una instrucción: es un documento superpuesto
# (Aviso.DOCUMENTO_SUPERPUESTO, con el fragmento y el proveedor en el evento). Qué hace la norma con él lo
# decide rules/.
_SUFIJOS_SOCIETARIOS = {"s", "l", "a", "c", "u", "sl", "sa", "sc", "slu", "sll", "coop"}
_NIF_EN_TEXTO = re.compile(r"\b(?:[A-Z]\d{7}[A-Z0-9]|\d{8}[A-Z])\b")


@dataclass
class ResumenExtraccion:
    candidatos: int = 0
    ok: int = 0
    pendientes: int = 0
    errores_pdf: int = 0
    por_metodo: dict[str, int] = field(
        default_factory=dict
    )  # plantilla | llm_texto | llm_vision | cache
    errores: dict[str, int] = field(default_factory=dict)  # error_codigo → n
    tokens_in: int = 0
    tokens_out: int = 0
    coste_eur: float = 0.0
    segundos: float = 0.0

    def texto(self) -> str:
        fps = self.candidatos / self.segundos if self.segundos else 0.0
        return (
            f"extract: {self.ok}/{self.candidatos} ok · {self.pendientes} pendientes · {self.errores_pdf} pdf ilegibles · "
            f"métodos {self.por_metodo} · errores {self.errores} · tokens {self.tokens_in}/{self.tokens_out} · "
            f"{self.coste_eur:.4f} EUR · {self.segundos:.1f} s ({fps:.2f} ficheros/s)"
        )


def ruta_pdf(file_id: str, lote: int) -> Path:
    """El PDF por su file_id: primero el directorio del lote, después el otro (por si se movió)."""
    for directorio in (DIRECTORIOS.get(lote), *DIRECTORIOS.values()):
        if directorio is not None and (directorio / file_id).exists():
            return directorio / file_id
    raise FileNotFoundError(f"{file_id} no está en {list(DIRECTORIOS.values())}")


def candidatos(
    conn: sqlite3.Connection, *, solo_pendientes: bool = True, fixture: Path | None = None
) -> list[dict[str, Any]]:
    filas = conn.execute(
        """SELECT f.file_id, f.sha256, f.lote, f.tiene_texto
           FROM ficheros f LEFT JOIN hechos h ON h.sha256 = f.sha256 AND h.extractor_version = ?
           WHERE (? = 0 OR h.sha256 IS NULL) ORDER BY f.file_id""",
        (EXTRACTOR_VERSION, 1 if solo_pendientes else 0),
    ).fetchall()
    quiero: set[str] | None = None
    if fixture is not None:
        quiero = {
            unicodedata.normalize("NFC", x.strip())
            for x in Path(fixture).read_text(encoding="utf-8").splitlines()
            if x.strip() and not x.startswith("#")
        }
    return [dict(f) for f in filas if quiero is None or f["file_id"] in quiero]


def _extraer_uno(
    conn: sqlite3.Connection, fila: dict[str, Any], llm: ClienteLLM
) -> tuple[str, str, dict[str, Any]]:
    """(estado, metodo|error_codigo, uso). Escribe hechos + evento en `conn` y hace commit."""
    file_id, sha, lote = fila["file_id"], fila["sha256"], int(fila["lote"] or 1)
    t0 = time.perf_counter()
    uso: dict[str, Any] = {"tokens_in": 0, "tokens_out": 0, "coste_eur": 0, "intento": 1}
    try:
        ruta = ruta_pdf(file_id, lote)
        texto: str | None = None
        png: bytes | None = None
        if fila["tiene_texto"]:
            texto = pdf.texto_de(ruta)
        else:
            png = pdf.imagen_png(ruta, dpi=DPI_VISION)
        hechos: InvoiceFacts | None = None
        if texto is not None:
            hechos = plantillas.extraer_por_plantilla(texto, file_id=file_id, sha256=sha)
        if hechos is None:
            hechos, uso = llm.extraer(sha256=sha, file_id=file_id, texto=texto, png=png)
            marcas = uso.pop("otras_marcas", [])
            if png is not None:  # sellos, anotaciones... de cada lectura: superpuestos y traza
                uso["marcas"] = {"principal": marcas}
            if png is not None and VISION_DOBLE:
                uso = _segunda_lectura(hechos, uso, llm, ruta, sha, file_id)
            elif png is not None:
                uso = _evidencia_de_lecturas(llm.conn, hechos, uso, [("principal", hechos)])
        # revalidar, no validar: la segunda lectura puede haber cambiado campos ya validados
        hechos.avisos = validadores.revalidar(hechos)
        db.guardar_hechos(conn, hechos)
        db.registrar_evento(
            conn,
            Event(
                file_id=file_id,
                sha256=sha,
                etapa=Etapa.EXTRACT,
                estado=EstadoEvento.OK,
                intento=int(uso.get("intento", 1)),
                latencia_ms=_ms(t0),
                tokens_in=int(uso.get("tokens_in", 0)),
                tokens_out=int(uso.get("tokens_out", 0)),
                coste_eur=uso.get("coste_eur", 0),
                version=EXTRACTOR_VERSION,
                # el modelo va en el evento: sin él, tras un fallback no se sabe quién leyó
                # la factura, y la traza (20 pts) tiene que poder responder a eso.
                detalle=f"{hechos.metodo.value} avisos={[a.value for a in hechos.avisos]}"
                + (f" modelo={uso['modelo']}" if uso.get("modelo") else "")
                + (" respaldo=si" if uso.get("respaldo") else "")
                + (f" desempate={uso['desempate']}" if uso.get("desempate") else "")
                + (f" importes_de={uso['importes_de']}" if uso.get("importes_de") else "")
                + (f" discrepancias={uso['discrepancias']}" if uso.get("discrepancias") else "")
                + (f" reconciliado={uso['reconciliado']}" if uso.get("reconciliado") else "")
                + (f" superpuesto={uso['superpuesto']}" if uso.get("superpuesto") else "")
                + (f" instruccion_de={uso['instruccion_de']}" if uso.get("instruccion_de") else "")
                + (f" no_confirmado={uso['no_confirmado']}" if uso.get("no_confirmado") else "")
                + (f" marcas={uso['marcas_vistas']}" if uso.get("marcas_vistas") else ""),
            ),
        )
        conn.commit()
        return "ok", hechos.metodo.value, uso
    except ErrorLLM as e:
        _evento_seguro(
            conn,
            Event(
                file_id=file_id,
                sha256=sha,
                etapa=Etapa.EXTRACT,
                estado=EstadoEvento.PENDIENTE,
                intento=getattr(e, "intentos", 1),
                latencia_ms=_ms(t0),
                error_codigo=e.codigo,
                detalle=str(e)[:200],
                version=EXTRACTOR_VERSION,
            ),
        )
        return "pendiente", e.codigo, {}
    except Exception as e:  # PDF ilegible, fichero movido, BD bloqueada...: se registra y se sigue
        codigo = f"EXTRACT-{type(e).__name__}"
        log.warning("%s: %s", file_id, e)
        _evento_seguro(
            conn,
            Event(
                file_id=file_id,
                sha256=sha,
                etapa=Etapa.EXTRACT,
                estado=EstadoEvento.ERROR,
                latencia_ms=_ms(t0),
                error_codigo=codigo,
                detalle=str(e)[:200],
                version=EXTRACTOR_VERSION,
            ),
        )
        return "error", codigo, {}


def _recorte_superior_png(ruta: Path, *, dpi: int, fraccion: float) -> bytes:
    import pymupdf

    with pymupdf.open(ruta) as doc:
        pagina = doc[0]
        r = pagina.rect
        clip = pymupdf.Rect(r.x0, r.y0, r.x1, r.y0 + r.height * fraccion)
        return pagina.get_pixmap(dpi=dpi, clip=clip).tobytes("png")


def _segunda_lectura(
    hechos: InvoiceFacts, uso: dict[str, Any], llm: ClienteLLM, ruta: Path, sha: str, file_id: str
) -> dict[str, Any]:
    """Escaneadas: segunda pasada sobre el recorte superior a más resolución. Si los identificadores
    no coinciden, una tercera (`_desempatar`) y, para lo que siga sin acuerdo, el maestro; lo que quede
    se marca DISCREPANCIA_EXTRACTORES (la norma escala) y queda la evidencia en el uso.
    Después, lo que digan las lecturas en `texto_sospechoso` (`_evidencia_de_lecturas`)."""
    try:
        png2 = _recorte_superior_png(ruta, dpi=DPI_VISION_2, fraccion=FRACCION_SUPERIOR_2)
        otra, uso2 = llm.extraer(
            sha256=sha, file_id=file_id, png=png2, variante=f"sup{DPI_VISION_2}"
        )
    except ErrorLLM as e:  # la segunda lectura es opcional: sin ella, se sigue con la primera
        log.warning("%s: segunda lectura no disponible (%s)", file_id, e.codigo)
        return _evidencia_de_lecturas(llm.conn, hechos, uso, [("principal", hechos)])
    difs = {
        k: v
        for k, v in validadores.discrepancias(hechos, otra).items()
        if k in CAMPOS_SEGUNDA_LECTURA and getattr(otra, k) is not None
    }
    uso = dict(uso)
    _sumar_uso(uso, uso2)
    uso["marcas"] = {**uso.get("marcas", {}), f"sup{DPI_VISION_2}": uso2.get("otras_marcas", [])}
    lecturas = [("principal", hechos), (f"sup{DPI_VISION_2}", otra)]
    if TERCERA_LECTURA and any(k in CAMPOS_DESEMPATE for k in difs):
        difs, tercera = _desempatar(hechos, otra, difs, uso, llm, ruta, sha, file_id)
        if tercera is not None:
            lecturas.append((VARIANTE_3, tercera))
    if difs:
        reconciliados = (
            _reconciliar_con_maestro(llm.conn, hechos, otra, difs) if RECONCILIAR_MAESTRO else {}
        )
        if reconciliados:
            uso["reconciliado"] = reconciliados
            hechos.confianza = CONFIANZA_RECONCILIADA
        restantes = {k: v for k, v in difs.items() if k not in reconciliados}
        if restantes:
            if Aviso.DISCREPANCIA_EXTRACTORES not in hechos.avisos:
                hechos.avisos.append(Aviso.DISCREPANCIA_EXTRACTORES)
            uso["discrepancias"] = {k: (str(a), str(b)) for k, (a, b) in restantes.items()}
    if IMPORTES_POR_CUENTAS and validadores.cuentas_fallan(hechos):
        _importes_que_cuadran(hechos, uso, lecturas[1:], llm, ruta, sha, file_id)
    # después de reconciliar: el proveedor "propio" de la factura sale ya de los identificadores elegidos
    return _evidencia_de_lecturas(llm.conn, hechos, uso, lecturas)


def _importes_que_cuadran(
    hechos: InvoiceFacts,
    uso: dict[str, Any],
    otras: list[tuple[str, InvoiceFacts]],
    llm: ClienteLLM,
    ruta: Path,
    sha: str,
    file_id: str,
) -> None:
    """Las cuentas de la principal fallan: toma el bloque de importes de la primera otra lectura cuyas cuentas
    cuadran y, si no hay, de una lectura más de la página entera. Si ninguna cuadra, no toca nada y los avisos
    se quedan (la norma escala): puede ser el documento el que no cuadra, no la lectura. No baja `confianza`:
    el criterio no sale del maestro. La evidencia (qué lectura y los importes de antes) va al evento como
    `importes_de=`; la lectura extra es opcional, como la segunda."""

    elegida = next(((n, o) for n, o in otras if validadores.cuentas_cuadran(o)), None)
    if elegida is None:  # ninguna de las ya hechas cuadra: una lectura más, sólo ahora
        try:
            png = pdf.imagen_png(ruta, dpi=DPI_VISION_IMPORTES)
            otra, uso_extra = llm.extraer(
                sha256=sha, file_id=file_id, png=png, variante=VARIANTE_IMPORTES
            )
        except ErrorLLM as e:
            log.warning("%s: lectura de importes no disponible (%s)", file_id, e.codigo)
            return
        _sumar_uso(uso, uso_extra)
        if not validadores.cuentas_cuadran(otra):
            return
        elegida = (VARIANTE_IMPORTES, otra)
    nombre, otra = elegida
    uso["importes_de"] = {
        "lectura": nombre,
        "antes": {
            "base": str(hechos.base),
            "iva": str(hechos.iva),
            "total": str(hechos.total),
            "lineas": [str(x.importe) for x in hechos.lineas],
        },
    }
    for campo in CAMPOS_IMPORTE:
        setattr(hechos, campo, getattr(otra, campo))


def _sumar_uso(uso: dict[str, Any], otro: dict[str, Any]) -> None:
    for k in ("tokens_in", "tokens_out"):
        uso[k] = int(uso.get(k, 0)) + int(otro.get(k, 0))
    uso["coste_eur"] = Decimal(str(uso.get("coste_eur", 0))) + Decimal(
        str(otro.get("coste_eur", 0))
    )


def _desempatar(
    hechos: InvoiceFacts,
    otra: InvoiceFacts,
    difs: dict[str, Any],
    uso: dict[str, Any],
    llm: ClienteLLM,
    ruta: Path,
    sha: str,
    file_id: str,
) -> tuple[dict[str, Any], InvoiceFacts | None]:
    """Tercera lectura para los identificadores en desacuerdo (`CAMPOS_DESEMPATE`): gana
    el valor ENTERO que repiten dos de las
    tres lecturas. No se vota carácter a carácter: en scan_023 (NIF tapado por una mancha) las lecturas
    B96233418, B68233419 y B96233419 del ensayo compondrían, dígito a dígito, justo el NIF del maestro
    (B96233419), y una trampa se pagaría. Tampoco se mira el maestro: por eso
    un desempate no baja `confianza`, y la R1 compara contra el maestro un dato que no salió de él.

    Devuelve (desacuerdos que quedan, tercera lectura o None). Muta `hechos` y `uso` (tokens y
    `desempate`, que va al evento con las tres lecturas). Si la tercera no llega, todo sigue como estaba."""
    try:
        png = _recorte_superior_png(ruta, dpi=DPI_VISION_3, fraccion=FRACCION_SUPERIOR_3)
        tercera, uso3 = llm.extraer(sha256=sha, file_id=file_id, png=png, variante=VARIANTE_3)
    except ErrorLLM as e:  # opcional, como la segunda: sin ella decide el camino de siempre
        log.warning("%s: tercera lectura no disponible (%s)", file_id, e.codigo)
        return difs, None
    _sumar_uso(uso, uso3)
    uso["marcas"] = {**uso.get("marcas", {}), VARIANTE_3: uso3.get("otras_marcas", [])}
    desempate: dict[str, Any] = {}
    for campo in (k for k in difs if k in CAMPOS_DESEMPATE):
        # los tres valores ya vienen normalizados de `_a_hechos` (NIF, IBAN y pedido)
        a, b, t = getattr(hechos, campo), getattr(otra, campo), getattr(tercera, campo)
        if t is None or t not in (a, b):
            continue
        desempate[campo] = {
            "lecturas": [a, b, t],
            "elegido": t,
            "por": f"{'principal' if t == a else f'sup{DPI_VISION_2}'} y {VARIANTE_3}",
        }
        setattr(hechos, campo, t)
    if desempate:
        uso["desempate"] = desempate
    return {k: v for k, v in difs.items() if k not in desempate}, tercera


def _evidencia_de_lecturas(
    conn: sqlite3.Connection,
    hechos: InvoiceFacts,
    uso: dict[str, Any],
    lecturas: list[tuple[str, InvoiceFacts]],
) -> dict[str, Any]:
    """Lo que las lecturas de una escaneada ven además de sus campos: instrucciones y otras marcas.

    - **Documento superpuesto:** si un `texto_sospechoso` o una de las `otras_marcas` (sellos, texto de otro
      documento…) nombra a otro proveedor del maestro → DOCUMENTO_SUPERPUESTO, con la evidencia en el evento.
      Sin maestro, o sin saber de qué proveedor es la factura, no se marca: no hay contra qué comparar.
    - **Instrucciones, con dos lecturas o más (ADR-0018, «B'»):** un texto sólo se cita como instrucción
      (TEXTO_INSTRUCCION y `texto_sospechoso`, que R6 cita como "el documento dice") si lo ven al menos dos
      lecturas con un texto parecido. Si lo ve una sola, la factura escala igual (DISCREPANCIA_EXTRACTORES:
      las lecturas no coinciden) pero el texto NO se cita como del documento; queda en el evento
      (`no_confirmado=`). Medido el 19/09: el modelo inventó "FACTURA NO PAGAR" leyendo un "FACTURA Nº" tapado
      (scan_021) y citó "URGENTE PAGAR EL TOTAL IMPRESO", un ejemplo del prompt (scan_025); las dos, en una
      sola lectura. Las notas reales (scan_016, scan_029) las ven varias lecturas en todas las pasadas.
    - **Una sola lectura** (sin doble lectura, o la segunda falló): no hay con qué confirmar, se queda lo que
      puso `_a_hechos`, como antes.
    """
    uso = dict(uso)
    marcas: dict[str, list[str]] = uso.pop("marcas", {})
    vistas = {n: m for n, m in marcas.items() if m}
    if vistas:
        uso["marcas_vistas"] = vistas
    maestro = _maestro(conn)
    propio = _proveedor_de_la_factura(hechos, maestro) if maestro is not None else None
    superpuestas: set[str] = set()  # lecturas cuyo texto_sospechoso es de otro documento
    for nombre, lectura in lecturas:
        if maestro is None or propio is None:
            break
        for texto in [lectura.texto_sospechoso, *marcas.get(nombre, [])]:
            otro = _proveedor_nombrado(texto, maestro, excluir=propio.id) if texto else None
            if otro is None:
                continue
            if texto == lectura.texto_sospechoso:
                superpuestas.add(nombre)
            if "superpuesto" not in uso:
                proveedor, por = otro
                uso["superpuesto"] = {
                    "lectura": nombre,
                    "proveedor": proveedor.id,
                    "por": por,
                    "factura_de": propio.id,
                    "fragmento": texto[:160],
                }
            if Aviso.DOCUMENTO_SUPERPUESTO not in hechos.avisos:
                hechos.avisos.append(Aviso.DOCUMENTO_SUPERPUESTO)
    if len(lecturas) < 2:
        return uso
    candidatos = [
        (n, lec.texto_sospechoso)
        for n, lec in lecturas
        if lec.texto_sospechoso and n not in superpuestas
    ]
    # lo que `_a_hechos` adoptó de la principal se decide aquí, con todas las lecturas
    hechos.texto_sospechoso = None
    hechos.avisos = [a for a in hechos.avisos if a != Aviso.TEXTO_INSTRUCCION]
    grupo = _confirmados(candidatos)
    if grupo:
        hechos.texto_sospechoso = grupo[0][1]  # el de la principal si está en el grupo
        hechos.avisos.append(Aviso.TEXTO_INSTRUCCION)
        uso["instruccion_de"] = [n for n, _ in grupo]
    elif candidatos:
        if Aviso.DISCREPANCIA_EXTRACTORES not in hechos.avisos:
            hechos.avisos.append(Aviso.DISCREPANCIA_EXTRACTORES)
        uso["no_confirmado"] = {n: t[:160] for n, t in candidatos}
    return uso


def _confirmados(candidatos: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """El grupo más grande de lecturas (≥ 2) con textos parecidos: comparten al menos la mitad de sus
    palabras (Jaccard ≥ 0,5, sin tildes ni signos). Así "NOTA NUEVO NUM. DE CUENTA" y "NOTA: NUEVO NUM. DE
    CUENTA" son el mismo texto, y un "URGENTE" suelto no confirma "URGENTE PAGAR EL TOTAL IMPRESO"."""
    mejor: list[tuple[str, str]] = []
    for _, texto in candidatos:
        base = set(_palabras(texto))
        grupo = [
            (n, t)
            for n, t in candidatos
            if base and len(base & set(_palabras(t))) / len(base | set(_palabras(t))) >= 0.5
        ]
        if len(grupo) > len(mejor):
            mejor = grupo
    return mejor if len(mejor) >= 2 else []


def _maestro(conn: sqlite3.Connection) -> MasterSnapshot | None:
    from albertitos.sources import snapshot

    try:
        return snapshot.cargar_maestro_bd(conn)
    except LookupError:
        return None


def _proveedor_de_la_factura(h: InvoiceFacts, maestro: MasterSnapshot) -> Proveedor | None:
    """El proveedor por el NIF leído y, si no está en el maestro, el del pedido."""
    if h.nif_emisor:
        p = maestro.proveedor_por_nif(h.nif_emisor)
        if p is not None:
            return p
    pedido = maestro.pedidos.get(h.pedido or "")
    return maestro.proveedores.get(pedido.proveedor_id) if pedido is not None else None


def _palabras(texto: str) -> list[str]:
    return re.sub(r"[^a-z0-9]+", " ", sin_tildes(texto).lower()).split()


def _nombre_comercial(razon_social: str) -> str:
    """'Electricidad Montcada S.A.' → 'electricidad montcada': sin tildes, signos ni forma societaria."""
    palabras = _palabras(razon_social)
    while palabras and palabras[-1] in _SUFIJOS_SOCIETARIOS:
        palabras.pop()
    return " ".join(palabras)


def _proveedor_nombrado(
    fragmento: str, maestro: MasterSnapshot, *, excluir: str
) -> tuple[Proveedor, str] | None:
    """Otro proveedor del maestro nombrado en el fragmento, por razón social (≥ 2 palabras, para no
    casar con una palabra suelta) o por NIF exacto. Devuelve (proveedor, cómo se reconoció)."""
    plano = f" {' '.join(_palabras(fragmento))} "
    nifs = {normalizar_nif(x) for x in _NIF_EN_TEXTO.findall(fragmento.upper())}
    for p in sorted(maestro.proveedores.values(), key=lambda p: p.id):
        if p.id == excluir:
            continue
        nombre = _nombre_comercial(p.razon_social)
        if len(nombre.split()) >= 2 and f" {nombre} " in plano:
            return p, f"razón social {p.razon_social!r}"
        if normalizar_nif(p.nif) in nifs:
            return p, f"NIF {p.nif}"
    return None


def _reconciliar_con_maestro(
    conn: sqlite3.Connection, hechos: InvoiceFacts, otra: InvoiceFacts, difs: dict[str, Any]
) -> dict[str, Any]:
    """Para cada identificador en desacuerdo, elige la lectura respaldada por el maestro y el pedido.

    NIF: la lectura que es el NIF del proveedor al que pertenece el pedido (según el Excel).
    IBAN: la lectura que es el IBAN de ese mismo proveedor.
    Pedido: la lectura que existe en el Excel y cuyo proveedor tiene el NIF leído.
    Devuelve {campo: {"lecturas": [a, b], "elegido": x, "evidencia": "..."}} y muta `hechos`."""
    from albertitos.sources import snapshot

    try:
        maestro = snapshot.cargar_maestro_bd(conn)
    except LookupError:
        return {}
    out: dict[str, Any] = {}
    candidatos_pedido = [x for x in (hechos.pedido, otra.pedido) if x]
    pedido = next((maestro.pedidos[x] for x in candidatos_pedido if x in maestro.pedidos), None)
    if "pedido" in difs and pedido is not None:
        validos = [x for x in candidatos_pedido if x in maestro.pedidos]
        if len(validos) == 1:
            out["pedido"] = {
                "lecturas": [hechos.pedido, otra.pedido],
                "elegido": validos[0],
                "evidencia": "único que existe en el Excel",
            }
            hechos.pedido = validos[0]
            pedido = maestro.pedidos[validos[0]]
    proveedor = maestro.proveedores.get(pedido.proveedor_id) if pedido is not None else None
    if "nif_emisor" in difs and proveedor is not None:
        lecturas = [hechos.nif_emisor, otra.nif_emisor]
        if lecturas.count(proveedor.nif) == 1:
            out["nif_emisor"] = {
                "lecturas": lecturas,
                "elegido": proveedor.nif,
                "evidencia": f"NIF de {proveedor.id}, proveedor del pedido {pedido.pedido}",
            }
            hechos.nif_emisor = proveedor.nif
    if "iban" in difs and proveedor is not None and hechos.nif_emisor == proveedor.nif:
        lecturas = [hechos.iban, otra.iban]
        if lecturas.count(proveedor.iban) == 1:
            out["iban"] = {
                "lecturas": lecturas,
                "elegido": proveedor.iban,
                "evidencia": f"IBAN de {proveedor.id} en el maestro",
            }
            hechos.iban = proveedor.iban
    return out


def contrastar(
    conn: sqlite3.Connection,
    *,
    n: int = 40,
    workers: int = 4,
    semilla: int = 7,
    lote: int | None = None,
    file_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Pasa el LLM (texto) por `n` facturas que salieron por plantilla y compara con `discrepancias`.

    No toca `hechos`: sólo devuelve el informe (y deja las lecturas en caché con variante 'contraste').
    Es la única forma de descartar que un parser se equivoque en bloque sobre cientos de facturas.

    `lote` y `file_ids` acotan la muestra (petición de B1, bitácora 18/09): en el lote 2 interesa
    contrastar SÓLO lo nuevo, y además es la única vía de que una factura de plantilla pase por el
    LLM y suelte su `texto_sospechoso`. Una instrucción con redacción nueva, en una factura que
    resuelve la plantilla, hoy sólo la ven las regex de `instrucciones.py`."""
    import random
    from concurrent.futures import ThreadPoolExecutor as _Pool

    sql = """SELECT f.file_id, f.sha256, f.lote, h.hechos_json FROM hechos h JOIN ficheros f ON f.sha256 = h.sha256
             WHERE h.extractor_version = ? AND h.metodo = 'plantilla'"""
    params: list[Any] = [EXTRACTOR_VERSION]
    if lote is not None:
        sql += " AND f.lote = ?"
        params.append(lote)
    if file_ids:
        quiero = [unicodedata.normalize("NFC", x) for x in file_ids]
        sql += f" AND f.file_id IN ({','.join('?' * len(quiero))})"
        params.extend(quiero)
    filas = conn.execute(sql + " ORDER BY f.file_id", params).fetchall()
    rng = random.Random(semilla)
    candidatas = [dict(f) for f in filas]
    # con una lista explícita se contrastan todas: el llamador ya ha elegido
    muestra = candidatas if file_ids else rng.sample(candidatas, min(n, len(candidatas)))
    estado = EstadoLLM()
    ruta_db = conn.execute("PRAGMA database_list").fetchone()[2]

    def uno(fila: dict[str, Any]) -> dict[str, Any]:
        c = db.conectar(ruta_db)
        try:
            base = InvoiceFacts.model_validate_json(fila["hechos_json"])
            texto = pdf.texto_de(ruta_pdf(fila["file_id"], int(fila["lote"] or 1)))
            cli = ClienteLLM(c, estado=estado)
            otra, uso = cli.extraer(
                sha256=fila["sha256"], file_id=fila["file_id"], texto=texto, variante="contraste"
            )
            difs = validadores.discrepancias(base, otra)
            return {
                "file_id": fila["file_id"],
                "ok": not difs,
                "discrepancias": {k: (str(a), str(b)) for k, (a, b) in difs.items()},
                "tokens": int(uso.get("tokens_in", 0)) + int(uso.get("tokens_out", 0)),
            }
        except ErrorLLM as e:
            return {"file_id": fila["file_id"], "ok": None, "error": e.codigo}
        finally:
            c.close()

    with _Pool(max_workers=workers) as pool:
        resultados = list(pool.map(uno, muestra))
    coinciden = sum(1 for r in resultados if r["ok"] is True)
    difieren = [r for r in resultados if r["ok"] is False]
    fallos = [r for r in resultados if r["ok"] is None]
    return {
        "n": len(resultados),
        "coinciden": coinciden,
        "difieren": difieren,
        "fallos": fallos,
        "tokens": sum(r.get("tokens", 0) for r in resultados),
        "plantillas_en_bd": len(filas),
    }


def extraer(
    conn: sqlite3.Connection,
    *,
    solo_pendientes: bool = True,
    fixture: Path | None = None,
    workers: int = 1,
) -> ResumenExtraccion:
    t0 = time.perf_counter()
    filas = candidatos(conn, solo_pendientes=solo_pendientes, fixture=fixture)
    r = ResumenExtraccion(candidatos=len(filas))
    estado = EstadoLLM()

    def sumar(res: tuple[str, str, dict[str, Any]]) -> None:
        est, clave, uso = res
        if est == "ok":
            r.ok += 1
            r.por_metodo[clave] = r.por_metodo.get(clave, 0) + 1
            r.tokens_in += int(uso.get("tokens_in", 0))
            r.tokens_out += int(uso.get("tokens_out", 0))
            r.coste_eur += float(uso.get("coste_eur", 0))
        elif est == "pendiente":
            r.pendientes += 1
            r.errores[clave] = r.errores.get(clave, 0) + 1
        else:
            r.errores_pdf += 1
            r.errores[clave] = r.errores.get(clave, 0) + 1

    if workers <= 1 or len(filas) <= 1:
        llm = ClienteLLM(conn, estado=estado)
        for fila in filas:
            sumar(_extraer_uno(conn, fila, llm))
    else:
        ruta_db = conn.execute("PRAGMA database_list").fetchone()[2]

        def trabajo(fila: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
            c = db.conectar(
                ruta_db
            )  # una conexión por hilo; WAL aguanta escritores concurrentes cortos
            try:
                return _extraer_uno(c, fila, ClienteLLM(c, estado=estado))
            finally:
                c.close()

        with ThreadPoolExecutor(max_workers=workers) as pool:
            for res in pool.map(trabajo, filas):
                sumar(res)
    r.segundos = time.perf_counter() - t0
    return r


def _evento_seguro(conn: sqlite3.Connection, ev: Event) -> None:
    """Registrar un evento de error nunca puede tumbar el lote: si la BD no deja, se reintenta y se loguea."""
    for intento in range(3):
        try:
            conn.rollback()
            db.registrar_evento(conn, ev)
            conn.commit()
            return
        except sqlite3.OperationalError as e:
            log.warning("evento no registrado (%s), intento %s: %s", ev.file_id, intento + 1, e)
            time.sleep(0.5 * (intento + 1))


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)
