"""Calendario y borrador de remesa: proyección de sólo lectura de decisiones PAGAR."""

from __future__ import annotations

import csv
import html
import json
import re
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from albertitos.core import db
from albertitos.core.contracts import InvoiceFacts, MasterSnapshot
from albertitos.formatos import iban_valido, normalizar_iban


class Pago(BaseModel):
    file_id: str
    decision_id: int
    proveedor_id: str
    beneficiario: str
    iban: str
    referencia: str
    importe_eur: Decimal
    fecha_factura: date
    vencimiento: date
    fecha_ejecucion: date
    semana: str
    vencido: bool
    maestro_version: str
    apto_remesa: bool
    iban_control_ok: bool = True  # mod-97; los IBAN sintéticos de la Caja no lo pasan


class Incidencia(BaseModel):
    file_id: str
    codigo: str
    detalle: str


class Informe(BaseModel):
    fecha_corte: date
    decisiones_pagar: int
    calendario: list[Pago] = Field(default_factory=list)
    avisos: list[Incidencia] = Field(default_factory=list)

    @property
    def remesa(self) -> list[Pago]:
        return [p for p in self.calendario if p.apto_remesa]

    def resumen(self) -> dict:
        semanas = {}
        for p in self.calendario:
            grupo = semanas.setdefault(p.semana, {"numero": 0, "importe_eur": Decimal("0.00")})
            grupo["numero"] += 1
            grupo["importe_eur"] += p.importe_eur
        return {
            "tipo": "BORRADOR: no es una orden bancaria ni acredita pagos ejecutados",
            "fecha_corte": self.fecha_corte.isoformat(),
            "decisiones_pagar": self.decisiones_pagar,
            "calendario_numero": len(self.calendario),
            "calendario_total_eur": str(
                sum((p.importe_eur for p in self.calendario), Decimal("0.00"))
            ),
            "remesa_numero": len(self.remesa),
            "remesa_total_eur": str(sum((p.importe_eur for p in self.remesa), Decimal("0.00"))),
            "excluidos_remesa": self.decisiones_pagar - len(self.remesa),
            "remesa_iban_sin_control": sum(not p.iban_control_ok for p in self.remesa),
            "sin_vencimiento_calculable": self.decisiones_pagar - len(self.calendario),
            "vencidos": sum(p.vencido for p in self.calendario),
            "vencen_semana_corte": sum(
                p.semana == semana_iso(self.fecha_corte) for p in self.calendario
            ),
            "avisos_por_codigo": dict(sorted(Counter(a.codigo for a in self.avisos).items())),
            "semanas": {
                k: {**v, "importe_eur": str(v["importe_eur"])} for k, v in sorted(semanas.items())
            },
        }


def semana_iso(fecha: date) -> str:
    anio, semana, _ = fecha.isocalendar()
    return f"{anio}-W{semana:02d}"


def _forma_iban_ok(iban: str) -> bool:
    """Forma de IBAN (país, dígitos, longitud española), sin el dígito de control."""
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", iban):
        return False
    return not iban.startswith("ES") or len(iban) == 24


def calcular(ruta_bd: Path, fecha_corte: date | None = None, estricto: bool = False) -> Informe:
    """Usa hechos y maestro del linaje guardado, nunca el reloj ni una decisión nueva.

    Los 11 IBAN del maestro de la Caja son sintéticos: tienen forma de IBAN, pero ninguno pasa el
    mod-97 (formatos.iban_valido lo avisa: "es un Aviso, no una regla"). Por defecto, un IBAN con
    forma válida y control fallido entra en la remesa MARCADO (`iban_control_ok=False`) y se avisa
    una vez por proveedor. Con `estricto=True` se excluye, como haría el banco. Un IBAN sin forma de
    IBAN, o distinto del de la factura, se excluye siempre."""
    conn = db.conectar(ruta_bd, solo_lectura=True)
    try:
        conn.execute("BEGIN")  # Vista consistente también con otros lectores/escritores.
        decisiones = db.decisiones_vigentes(conn)
        cortes = {d["fecha_corte"] for d in decisiones}
        if fecha_corte is None:
            if len(cortes) != 1:
                raise ValueError("BD vacía o cortes distintos: indique --fecha-corte AAAA-MM-DD")
            fecha_corte = date.fromisoformat(cortes.pop())
        seleccion = [d for d in decisiones if d["resultado"] == "PAGAR"]
        informe = Informe(fecha_corte=fecha_corte, decisiones_pagar=len(seleccion))
        copias = db.nombres_por_sha(conn)
        maestros = {}
        sin_control: set[str] = set()
        for d in seleccion:

            def aviso(codigo: str, detalle: str, file_id: str = d["file_id"]) -> None:
                informe.avisos.append(Incidencia(file_id=file_id, codigo=codigo, detalle=detalle))

            fila = conn.execute(
                "SELECT hechos_json,hechos_hash FROM hechos WHERE sha256=? ORDER BY creado_en DESC, extractor_version DESC LIMIT 1",
                (d["sha256"],),
            ).fetchone()
            if fila is None or fila["hechos_hash"] != d["hechos_hash"]:
                aviso(
                    "HECHOS_NO_VIGENTES",
                    "Faltan los hechos de la decisión o han cambiado; reprocesar antes.",
                )
                continue
            try:
                h = InvoiceFacts.model_validate_json(fila["hechos_json"])
                version = d["maestro_version"]
                if version not in maestros:
                    datos = db.cargar_snapshot(conn, "maestro", version)
                    if datos is None:
                        aviso("MAESTRO_AUSENTE", f"Falta snapshot {version} de la decisión.")
                        continue
                    maestros[version] = MasterSnapshot.model_validate_json(datos)
                maestro = maestros[version]
            except ValidationError:
                aviso("DATOS_INVALIDOS", "Hechos o maestro no cumplen el contrato.")
                continue
            if h.hash() != d["hechos_hash"] or h.sha256 != d["sha256"]:
                aviso(
                    "HECHOS_NO_VIGENTES",
                    "El contenido de hechos no coincide con el hash de la decisión.",
                )
                continue
            pedido = maestro.pedidos.get(h.pedido or "")
            proveedor = maestro.proveedores.get(pedido.proveedor_id) if pedido else None
            if proveedor is None or maestro.proveedor_por_nif(h.nif_emisor or "") != proveedor:
                aviso(
                    "PROVEEDOR_NO_IDENTIFICADO", "Pedido y NIF no identifican al mismo proveedor."
                )
                continue
            if proveedor.condiciones_dias is None or proveedor.condiciones_dias < 0:
                aviso("SIN_CONDICIONES", "El proveedor no tiene un plazo de pago válido.")
                continue
            if h.fecha is None or not h.num_factura or not h.num_factura.strip() or h.total is None:
                aviso("FACTURA_INCOMPLETA", "Falta fecha, referencia o importe.")
                continue
            if not h.total.is_finite() or h.total <= 0 or h.total.as_tuple().exponent < -2:
                aviso(
                    "IMPORTE_INVALIDO",
                    "Se requiere un importe positivo en EUR, con un máximo de dos decimales.",
                )
                continue
            try:
                vencimiento = h.fecha + timedelta(days=proveedor.condiciones_dias)
            except OverflowError:
                aviso("PLAZO_INVALIDO", "El vencimiento queda fuera del rango de fechas.")
                continue
            apto = True
            iban = normalizar_iban(proveedor.iban)
            control_ok = iban_valido(iban)
            if not _forma_iban_ok(iban) or (estricto and not control_ok):
                aviso(
                    "IBAN_INVALIDO",
                    f"El IBAN del proveedor {proveedor.id} no supera "
                    + ("el formato." if not _forma_iban_ok(iban) else "el mod-97 (modo estricto)."),
                )
                apto = False
            elif not control_ok and proveedor.id not in sin_control:
                sin_control.add(proveedor.id)
                aviso(
                    "IBAN_SIN_CONTROL",
                    f"El IBAN de {proveedor.id} no pasa el mod-97 (IBAN sintético de la Caja): "
                    "entra marcado; un banco real lo rechazaría (usa --estricto para excluirlo).",
                )
            if iban != normalizar_iban(h.iban or ""):
                aviso(
                    "IBAN_DISCREPANTE",
                    "El IBAN de los hechos no coincide con el maestro de la decisión.",
                )
                apto = False
            if d["sha256"] in copias:
                aviso(
                    "COPIA_EXACTA",
                    "Hay varios nombres para este contenido; reprocesar antes de preparar pagos.",
                )
                apto = False
            informe.calendario.append(
                Pago(
                    file_id=d["file_id"],
                    decision_id=d["id"],
                    proveedor_id=proveedor.id,
                    beneficiario=proveedor.razon_social,
                    iban=iban,
                    referencia=h.num_factura,
                    importe_eur=h.total.quantize(Decimal("0.01")),
                    fecha_factura=h.fecha,
                    vencimiento=vencimiento,
                    fecha_ejecucion=max(vencimiento, fecha_corte),
                    semana=semana_iso(vencimiento),
                    vencido=vencimiento < fecha_corte,
                    maestro_version=version,
                    apto_remesa=apto,
                    iban_control_ok=control_ok,
                )
            )
        referencias = Counter(
            (p.proveedor_id, p.referencia.strip().casefold()) for p in informe.calendario
        )
        for p in informe.calendario:
            if referencias[p.proveedor_id, p.referencia.strip().casefold()] > 1:
                p.apto_remesa = False
                informe.avisos.append(
                    Incidencia(
                        file_id=p.file_id,
                        codigo="REFERENCIA_DUPLICADA",
                        detalle="Más de un PAGAR del mismo proveedor con la misma referencia.",
                    )
                )
        informe.calendario.sort(key=lambda p: (p.vencimiento, p.file_id))
        return informe
    finally:
        conn.close()


def _celda(valor: object) -> str:
    texto = str(valor)
    # Los campos del PDF son datos, tampoco fórmulas al abrirlos en una hoja de cálculo.
    return (
        "'" + texto
        if texto.lstrip().startswith(("=", "+", "-", "@")) or texto.startswith(("\t", "\r", "\n"))
        else texto
    )


def exportar(informe: Informe, salida: Path, *, ruta_bd: Path) -> None:
    """CSV UTF-8, separador ;, fechas ISO, euros con punto decimal. No envía pagos."""
    salida = salida.resolve()
    raiz = Path(__file__).resolve().parents[3]
    protegidos = [raiz / "dist/entrega", raiz / "data/caja", raiz.parent / "HS-Maisa-Entrega"]
    if any(salida == p.resolve() or p.resolve() in salida.parents for p in protegidos):
        raise ValueError("La salida no puede estar en la Caja ni en la entrega oficial.")
    nombres = ("calendario.csv", "remesa.csv", "avisos.csv", "resumen.json", "calendario.html")
    for nombre in nombres:
        destino = salida / nombre
        if (
            destino.is_symlink()
            or destino.resolve() == ruta_bd.resolve()
            or (destino.exists() and destino.samefile(ruta_bd))
        ):
            raise ValueError("Un fichero de salida apunta a la BD o es un enlace simbólico.")
    salida.mkdir(parents=True, exist_ok=True)
    for nombre, modelos, campos in (
        ("calendario.csv", informe.calendario, Pago.model_fields),
        ("remesa.csv", informe.remesa, Pago.model_fields),
        ("avisos.csv", informe.avisos, Incidencia.model_fields),
    ):
        with (salida / nombre).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(campos), delimiter=";")
            writer.writeheader()
            writer.writerows(
                {k: _celda(v) for k, v in m.model_dump(mode="json").items()} for m in modelos
            )
    resumen = informe.resumen()
    (salida / "resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    filas = "".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(str(v))}</td>"
            for v in (
                p.semana,
                p.vencimiento,
                p.file_id,
                p.beneficiario,
                p.importe_eur,
                "Vencido" if p.vencido else "En plazo",
                ("Preparado" if p.iban_control_ok else "Preparado · IBAN sin control")
                if p.apto_remesa
                else "Excluido: ver avisos",
            )
        )
        + "</tr>"
        for p in informe.calendario
    )
    (salida / "calendario.html").write_text(
        '<!doctype html><html lang="es"><meta charset="utf-8"><title>Albertitos · Calendario de pagos</title>'
        "<style>body{font:16px system-ui;margin:2rem;color:#142b35}table{border-collapse:collapse;width:100%}td,th{padding:.6rem;text-align:left;border-bottom:1px solid #ddd}h1{color:#125c50}</style>"
        f"<h1>Calendario de pagos</h1><p>Borrador · corte {informe.fecha_corte} · EUR</p>"
        f"<p><b>{informe.decisiones_pagar} PAGAR</b> · {resumen['calendario_total_eur']} € calculables · "
        f"{resumen['vencidos']} vencidos · {resumen['vencen_semana_corte']} vencen esta semana.</p>"
        f"<p>Remesa: {resumen['remesa_numero']} pagos · {resumen['remesa_total_eur']} € · "
        f"{resumen['excluidos_remesa']} excluidos. No se ha ejecutado ningún pago.</p>"
        '<p><a href="remesa.csv">Remesa CSV</a> · <a href="avisos.csv">Avisos por factura</a> · <a href="resumen.json">Totales por semana</a></p>'
        "<table><thead><tr><th>Semana</th><th>Vence</th><th>Factura</th><th>Proveedor</th><th>EUR</th><th>Plazo</th><th>Remesa</th></tr></thead>"
        f"<tbody>{filas}</tbody></table></html>",
        encoding="utf-8",
    )
