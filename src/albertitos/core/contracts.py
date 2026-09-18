"""Contratos congelados de Albertitos (hora 1). Dueño: Miguel.

Todo lo que cruza una frontera de módulo pasa por aquí. Cambios: sólo con aviso al equipo,
compatibles hacia atrás (campos nuevos opcionales con default), con test en
tests/test_contracts.py y con la fila correspondiente en docs/contratos.md.

Principios que estos tipos hacen imposibles de saltar:
- InvoiceFacts no tiene campo "resultado"/"decision": el LLM no opina sobre pagar.
- Decision lleva versiones y hashes de todo lo que la produjo: reprocesado por linaje.
- Outcome sólo admite los campos que el verificador tolera.
"""

from __future__ import annotations

import unicodedata
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from albertitos.core.hashing import hash_canonico

# ----------------------------------------------------------------------------- enums


class Resultado(StrEnum):
    PAGAR = "PAGAR"
    NO_PAGAR = "NO_PAGAR"
    ESCALAR = "ESCALAR"


class Etapa(StrEnum):
    INGEST = "ingest"  # PDF → ficheros (sha256, páginas, tiene_texto)
    EXTRACT = "extract"  # PDF → InvoiceFacts
    VALIDATE = "validate"  # coherencia interna de los hechos
    ENRICH = "enrich"  # maestro + ERP
    DECIDE = "decide"  # norma vN → Decision
    EMIT = "emit"  # Decision → outcomes.jsonl


class EstadoEvento(StrEnum):
    OK = "ok"
    ERROR = "error"
    PENDIENTE = "pendiente"  # no se pudo completar (LLM caído...): se reintenta después
    RETRY = "retry"
    SKIP = "skip"


class MetodoExtraccion(StrEnum):
    PLANTILLA = "plantilla"  # parser determinista por plantilla conocida
    LLM_TEXTO = "llm_texto"  # LLM sobre la capa de texto
    LLM_VISION = "llm_vision"  # LLM sobre la imagen (escaneadas)
    CACHE = "cache"  # respuesta LLM reproducida desde cache_llm


class Aviso(StrEnum):
    """Señales que extract/validate producen y que la norma puede consumir. Nunca decisiones."""

    TEXTO_INSTRUCCION = "texto_instruccion"  # el PDF intenta dictar qué hacer
    SIN_TEXTO = "sin_texto"  # escaneada: hizo falta visión
    CAMPO_AUSENTE = "campo_ausente"
    IMPORTE_AMBIGUO = "importe_ambiguo"
    FECHA_EN_LETRA = "fecha_en_letra"
    IVA_NO_ESTANDAR = "iva_no_estandar"  # ≠ 21 % o mal calculado
    TOTAL_NO_CUADRA = "total_no_cuadra"  # base + IVA ≠ total (±0,01)
    IBAN_INVALIDO = "iban_invalido"  # falla mod-97
    NIF_INVALIDO = "nif_invalido"  # formato o letra/dígito de control incorrectos
    DUPLICADO_SOSPECHOSO = "duplicado_sospechoso"  # mismo nº factura/pedido/importe que otro PDF
    PEDIDO_ANULADO_SEGUN_PDF = "pedido_anulado_segun_pdf"
    DISCREPANCIA_EXTRACTORES = "discrepancia_extractores"  # plantilla y LLM no coinciden
    EXTRACCION_PARCIAL = "extraccion_parcial"


# ----------------------------------------------------------------------------- hechos


def _nfc(v: str) -> str:
    return unicodedata.normalize("NFC", v)


class LineaFactura(BaseModel):
    concepto: str
    unidades: Decimal | None = None
    importe: Decimal | None = None


class InvoiceFacts(BaseModel):
    """Lo que el extractor ve en el PDF. Sólo hechos: nada de 'resultado' ni 'accion'."""

    model_config = ConfigDict(extra="forbid")

    file_id: str
    sha256: str
    num_factura: str | None = None
    fecha: date | None = None
    razon_social: str | None = None
    nif_emisor: str | None = None
    iban: str | None = None
    pedido: str | None = None
    base: Decimal | None = None
    iva_pct: Decimal | None = None
    iva: Decimal | None = None
    total: Decimal | None = None
    lineas: list[LineaFactura] = Field(default_factory=list)
    metodo: MetodoExtraccion
    extractor_version: str
    avisos: list[Aviso] = Field(default_factory=list)
    texto_sospechoso: str | None = None  # fragmento literal que intenta instruir: evidencia
    confianza: float | None = None

    @field_validator("file_id")
    @classmethod
    def _file_id_nfc(cls, v: str) -> str:
        return _nfc(v)

    def hash(self) -> str:
        """Hash canónico de los hechos de negocio: si cambia, la decisión hay que recalcularla."""
        campos = self.model_dump(
            mode="json", exclude={"metodo", "confianza", "extractor_version", "texto_sospechoso"}
        )
        return hash_canonico(campos)


# ----------------------------------------------------------------------------- fuentes


class Proveedor(BaseModel):
    id: str
    razon_social: str
    nif: str
    iban: str
    ciudad: str | None = None
    condiciones_dias: int | None = None


class Pedido(BaseModel):
    pedido: str
    proveedor_id: str
    nif: str
    importe_total: Decimal
    estado: str
    fecha_pedido: date | None = None


class MasterSnapshot(BaseModel):
    """El Excel, ya limpio. `version` es el hash del contenido útil: cambia si cambia un dato."""

    version: str
    origen: str
    proveedores: dict[str, Proveedor]  # por id (P001...)
    pedidos: dict[str, Pedido]  # por nº de pedido (PO-2026-0001...)
    avisos_calidad: list[str] = Field(default_factory=list)
    cargado_en: datetime

    def proveedor_por_nif(self, nif: str) -> Proveedor | None:
        nif = nif.replace(" ", "").replace("-", "").upper()
        for p in self.proveedores.values():
            if p.nif.replace(" ", "").replace("-", "").upper() == nif:
                return p
        return None


class ErpEntry(BaseModel):
    asiento_id: str
    fecha_registro: date
    proveedor_id: str
    nif: str
    pedido: str
    importe_esperado: Decimal
    estado: str  # PENDIENTE | PAGADA


class ErpSnapshot(BaseModel):
    """Descarga completa del bridge en un momento dado. `version` = tag (v1, v2) elegido al bajar."""

    version: str
    asientos: dict[str, ErpEntry]  # por asiento_id
    descargado_en: datetime
    lote2_cargado: bool = False
    consultas: int = 0  # peticiones totales, reintentos incluidos
    reintentos: int = 0  # ORA-00600 / 429 / SES-401 superados

    def por_pedido(self) -> dict[str, list[ErpEntry]]:
        out: dict[str, list[ErpEntry]] = {}
        for a in self.asientos.values():
            out.setdefault(a.pedido, []).append(a)
        return out


# ----------------------------------------------------------------------------- decisión


class Motivo(BaseModel):
    regla_id: str  # "v3.R2"
    ok: bool
    detalle: str  # legible por Alberto
    evidencia: dict[str, Any] = Field(default_factory=dict)


class ContextoDecision(BaseModel):
    norma_version: str
    fecha_corte: date  # NUNCA date.today(): se guarda con la decisión
    maestro_version: str
    erp_version: str


class Decision(BaseModel):
    file_id: str
    sha256: str
    resultado: Resultado
    motivos: list[Motivo]
    norma_version: str
    fecha_corte: date
    hechos_hash: str
    maestro_version: str
    erp_version: str
    decidido_en: datetime | None = None  # lo sella core.db: decidir() no mira el reloj

    @field_validator("file_id")
    @classmethod
    def _file_id_nfc(cls, v: str) -> str:
        return _nfc(v)

    @property
    def motivo_principal(self) -> str:
        for m in self.motivos:
            if not m.ok:
                return f"{m.regla_id}: {m.detalle}"
        return "todas las reglas cumplidas"

    @property
    def reglas_incumplidas(self) -> list[str]:
        return [m.regla_id for m in self.motivos if not m.ok]


# ----------------------------------------------------------------------------- eventos


class Event(BaseModel):
    """Una fila del log de eventos. Cada etapa emite al menos uno por fichero."""

    file_id: str | None = None
    sha256: str | None = None
    etapa: Etapa
    estado: EstadoEvento
    intento: int = 1
    latencia_ms: int | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    coste_eur: Decimal | None = None
    error_codigo: str | None = None  # ORA-00600, ERP-429, SES-401, LLM-TIMEOUT, LLM-INVALID...
    detalle: str | None = None
    version: str | None = None  # versión del componente que lo emite
    ts: datetime | None = None  # lo pone core.db.registrar_evento


# ----------------------------------------------------------------------------- entrega


CAMPOS_TRAZA_PERMITIDOS = {"motivo", "norma_version", "regla"}


class Outcome(BaseModel):
    """Una línea del JSONL de entrega. Sólo file_id y result son obligatorios."""

    model_config = ConfigDict(extra="forbid")

    file_id: str
    result: Resultado
    motivo: str | None = None
    norma_version: str | None = None
    regla: str | None = None

    @field_validator("file_id")
    @classmethod
    def _file_id_valido(cls, v: str) -> str:
        if not unicodedata.is_normalized("NFC", v):
            raise ValueError(f"file_id no está en NFC: {v!r}")
        if "/" in v or "\\" in v or not v.lower().endswith(".pdf"):
            raise ValueError(f"file_id debe ser el nombre exacto del PDF: {v!r}")
        return v

    def linea(self) -> str:
        return self.model_dump_json(exclude_none=True)
