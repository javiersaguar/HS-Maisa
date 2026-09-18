"""PreToolUse(Edit|Write|MultiEdit|NotebookEdit): qué ficheros no se tocan y qué contenido no entra.

permissions sólo consulta reglas Read/Edit por ruta; este hook añade contexto (dueño) y contenido.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from _common import decidir, es_dueno, leer_entrada, raiz_proyecto, ruta_relativa

datos = leer_entrada()
entrada = datos.get("tool_input") or {}
ruta = entrada.get("file_path") or entrada.get("notebook_path") or ""
raiz = raiz_proyecto(datos)
rel = ruta_relativa(ruta, raiz) if ruta else ""
nombre = PurePosixPath(rel).name

# Contenido nuevo (Write: content · Edit: new_string · MultiEdit: edits[].new_string)
contenido = entrada.get("content") or entrada.get("new_string") or ""
for e in entrada.get("edits") or []:
    contenido += "\n" + (e.get("new_string") or "")

# 1. Contratos congelados.
if rel.startswith("src/albertitos/core/") and not es_dueno("ALBERTITOS_CONTRACT_OWNER"):
    decidir(
        "deny",
        f"`{rel}` es parte de los contratos congelados (core/). Sólo Miguel los cambia. "
        "Escribe en el canal: campo/tabla, motivo y quién lo consume. Mientras tanto, si te falta "
        "un campo, guárdalo en `avisos` o en `evidencia` (dict) sin tocar el contrato. "
        "Si eres Miguel: ALBERTITOS_CONTRACT_OWNER=1 en .claude/settings.local.json → env.",
    )

# 2. Entregables generados.
if (
    re.fullmatch(r"outcomes[\w-]*\.jsonl", nombre)
    or nombre == "albertitos_plan.pdf"
    or rel.startswith("dist/")
):
    decidir(
        "deny",
        "Eso se genera desde la BD: `make package` (JSONL, pasa por el validador) o `make plan-pdf`. "
        "Si el resultado de una factura está mal, arregla la regla o los hechos y reprocesa.",
    )

# 3. Secretos.
if nombre == ".env" or (nombre.startswith(".env.") and nombre != ".env.example"):
    decidir(
        "deny",
        ".env es personal y secreto. Documenta variables nuevas en .env.example y avisa al equipo.",
    )

# 4. La Caja es inmutable.
if rel.startswith("data/caja/") or rel.startswith("data/lote2/"):
    decidir(
        "deny",
        "data/caja y data/lote2 son el input oficial y no se editan (la validación es contra el "
        "original). Fixtures alterados → data/fixtures/. Manifiesto: `make caja-verify`.",
    )

# 5. Lockfile.
if nombre == "uv.lock":
    decidir(
        "deny", "uv.lock lo escribe uv: `uv add <paquete>` / `uv remove <paquete>` / `uv lock`."
    )

# 6. Contenido: nada de hoy() en las decisiones. La fecha de corte es un parámetro con linaje.
if rel.startswith(("src/albertitos/rules/", "src/albertitos/pipeline/")) and re.search(
    r"\b(date\.today|datetime\.now|datetime\.utcnow|time\.time)\s*\(", contenido
):
    decidir(
        "deny",
        "Nada de date.today()/datetime.now() en rules/ ni pipeline/: la regla 'fecha no futura' se "
        "evalúa contra `fecha_corte` (parámetro de la decisión, guardado con ella) para que el "
        "reprocesado sea reproducible. Los timestamps de eventos los pone core/db.py.",
    )

# 7. Contenido: en rules/ el texto libre de la factura no entra en la función de decisión.
if rel.startswith("src/albertitos/rules/") and re.search(
    r"\b(texto_completo|raw_text|texto_pdf)\b", contenido
):
    decidir(
        "deny",
        "rules/ decide sobre InvoiceFacts (campos tipados) + maestro + ERP, nunca sobre el texto del "
        "PDF. Si necesitas una señal del texto (p. ej. 'intenta instruir'), extract/ la convierte en "
        "un Aviso tipado y la regla consume el Aviso.",
    )

raise SystemExit(0)
