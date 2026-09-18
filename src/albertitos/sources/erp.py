"""Cliente del bridge ERP de 2009: token, reintentos ORA-00600, 429, rate limit, XML ISO-8859-1.

Se usa para bajar TODO una vez (ErpSnapshot). Cada petición emite un Event (etapa enrich): los
reintentos reales son parte de la demo de trazabilidad.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import httpx

from albertitos.core import db
from albertitos.core.contracts import ErpEntry, ErpSnapshot, EstadoEvento, Etapa, Event
from albertitos.formatos import normalizar_nif, normalizar_pedido, parse_fecha_es, parse_importe_es

log = logging.getLogger(__name__)

USUARIO = "alberto"
CLAVE = "FACTURAS2009"
RENOVAR_A_LOS_USOS = 250  # el token muere a los 300 usos o 15 min
RENOVAR_A_LOS_SEGUNDOS = 13 * 60


class ErrorERP(Exception):
    def __init__(self, codigo: str, mensaje: str = "") -> None:
        super().__init__(f"{codigo}: {mensaje}")
        self.codigo = codigo


class ClienteERP:
    def __init__(
        self,
        url: str | None = None,
        *,
        conn: sqlite3.Connection | None = None,
        rps: float = 8.0,
        max_intentos: int = 8,
        timeout: float = 15.0,
    ) -> None:
        self.url = (url or os.environ.get("ALBERTITOS_ERP_URL", "http://127.0.0.1:8009")).rstrip(
            "/"
        )
        self.conn = conn
        self.intervalo = 1.0 / rps
        self.max_intentos = max_intentos
        self.http = httpx.Client(timeout=timeout)
        self.token: str | None = None
        self.token_desde = 0.0
        self.usos = 0
        self.consultas = 0
        self.reintentos = 0
        self._ultima = 0.0

    # ------------------------------------------------------------------ fontanería

    def _evento(self, **kw) -> None:
        if self.conn is not None:
            db.registrar_evento(self.conn, Event(etapa=Etapa.ENRICH, **kw))

    def _respetar_ritmo(self) -> None:
        espera = self.intervalo - (time.perf_counter() - self._ultima)
        if espera > 0:
            time.sleep(espera)
        self._ultima = time.perf_counter()

    @staticmethod
    def _codigo_error(contenido: bytes, status: int) -> tuple[str, str]:
        try:
            raiz = ET.fromstring(contenido)
            return (raiz.findtext("codigo") or f"HTTP-{status}", raiz.findtext("mensaje") or "")
        except ET.ParseError:
            return (f"HTTP-{status}", contenido[:120].decode("iso-8859-1", "replace"))

    def _enviar(
        self,
        metodo: str,
        ruta: str,
        *,
        params: dict[str, str] | None = None,
        data: dict[str, str] | None = None,
        auth: bool = True,
        file_id: str | None = None,
    ) -> ET.Element:
        """Una petición con la política completa: ritmo, token, ORA-00600, 429, SES-401, eventos."""
        ultimo = "?"
        for intento in range(1, self.max_intentos + 1):
            if auth and (
                not self.token
                or self.usos >= RENOVAR_A_LOS_USOS
                or time.time() - self.token_desde > RENOVAR_A_LOS_SEGUNDOS
            ):
                self.login()
            self._respetar_ritmo()
            t0 = time.perf_counter()
            cab = {"X-ERP-Token": self.token or ""} if auth else {}
            r = self.http.request(
                metodo, f"{self.url}{ruta}", params=params, data=data, headers=cab
            )
            self.consultas += 1
            if auth:
                self.usos += 1
            que = f"{metodo} {ruta} {params or ''}".strip()
            if r.status_code == 200:
                self._evento(
                    file_id=file_id,
                    estado=EstadoEvento.OK,
                    intento=intento,
                    latencia_ms=_ms(t0),
                    detalle=que,
                    version="erp-2009",
                )
                return ET.fromstring(r.content)
            codigo, msg = self._codigo_error(r.content, r.status_code)
            ultimo = codigo
            self.reintentos += 1
            self._evento(
                file_id=file_id,
                estado=EstadoEvento.RETRY,
                intento=intento,
                latencia_ms=_ms(t0),
                error_codigo=codigo,
                detalle=f"{que}: {msg[:80]}",
            )
            if codigo == "SES-401":
                if not auth:
                    raise ErrorERP(
                        codigo, msg
                    )  # credenciales malas en el login: no tiene arreglo reintentando
                self.token = None
            elif r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", "1")))
            elif codigo == "ORA-00600":
                time.sleep(0.05 * intento)  # "Reintente la misma consulta. Funciona."
            elif r.status_code in (400, 404):
                raise ErrorERP(codigo, msg)
            else:
                time.sleep(0.2 * intento)
        raise ErrorERP(
            "ERP-AGOTADO", f"{ruta} tras {self.max_intentos} intentos (último: {ultimo})"
        )

    def login(self) -> str:
        raiz = self._enviar(
            "POST", "/erp/login", data={"usuario": USUARIO, "clave": CLAVE}, auth=False
        )
        self.token = raiz.findtext("token")
        self.token_desde = time.time()
        self.usos = 0
        return self.token or ""

    def _get(
        self, ruta: str, params: dict[str, str] | None = None, *, file_id: str | None = None
    ) -> ET.Element:
        return self._enviar("GET", ruta, params=params, auth=True, file_id=file_id)

    # ------------------------------------------------------------------ API

    def estado(self) -> dict[str, str]:
        return {el.tag: (el.text or "") for el in self._enviar("GET", "/erp/estado", auth=False)}

    def pagina(self, n: int) -> tuple[list[ErpEntry], int, int]:
        raiz = self._get("/erp/asientos", {"pagina": str(n)})
        meta = raiz.find("meta")
        paginas = int(meta.findtext("paginas") or 1) if meta is not None else 1
        total = int(meta.findtext("total") or 0) if meta is not None else 0
        asientos = [_asiento_de_xml(el) for el in raiz.iter("asiento")]
        return asientos, paginas, total

    def asiento(self, asiento_id: str) -> ErpEntry:
        raiz = self._get(f"/erp/asientos/{asiento_id}")
        el = raiz if raiz.tag == "asiento" else raiz.find(".//asiento")
        if el is None:
            raise ErrorERP("ERP-404", asiento_id)
        return _asiento_de_xml(el)

    def descargar_todo(self, tag: str) -> ErpSnapshot:
        """Baja todas las páginas una vez. El snapshot es la referencia contable para conciliar."""
        consultas0, reintentos0 = self.consultas, self.reintentos
        asientos: dict[str, ErpEntry] = {}
        primera, paginas, total = self.pagina(1)
        for a in primera:
            asientos[a.asiento_id] = a
        for n in range(2, paginas + 1):
            for a in self.pagina(n)[0]:
                asientos[a.asiento_id] = a
        if len(asientos) != total:
            log.warning("ERP: meta.total=%s pero se han leído %s asientos", total, len(asientos))
        est = self.estado()
        s = ErpSnapshot(
            version=tag,
            asientos=asientos,
            descargado_en=datetime.now(UTC),
            lote2_cargado=est.get("actualizacion_cargada", "NO").upper() == "SI",
            consultas=self.consultas - consultas0,
            reintentos=self.reintentos - reintentos0,
        )
        if self.conn is not None:
            self.conn.commit()
        return s


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


def _asiento_de_xml(el: ET.Element) -> ErpEntry:
    fecha = parse_fecha_es(el.findtext("fecha") or "")
    importe = parse_importe_es(el.findtext("importe") or "")
    if fecha is None or importe is None:
        raise ErrorERP(
            "ERP-FORMATO",
            f"asiento {el.findtext('id')}: fecha={el.findtext('fecha')} importe={el.findtext('importe')}",
        )
    return ErpEntry(
        asiento_id=(el.findtext("id") or "").strip(),
        fecha_registro=fecha,
        proveedor_id=(el.findtext("proveedor") or "").strip(),
        nif=normalizar_nif(el.findtext("nif") or ""),
        pedido=normalizar_pedido(el.findtext("pedido") or ""),
        importe_esperado=importe,
        estado=(el.findtext("estado") or "").strip().upper(),
    )
