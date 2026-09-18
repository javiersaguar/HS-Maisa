"""SessionStart: contexto operativo en 10 líneas para no preguntar lo mismo cada sesión.

Nunca falla: cada sonda está protegida. Sale por stdout (se añade al contexto del agente).
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import urllib.request
from datetime import datetime

from _common import es_dueno, leer_entrada, raiz_proyecto, rama_actual

datos = leer_entrada()
raiz = raiz_proyecto(datos)
lineas = ["[Albertitos · estado de sesión]"]

rama = rama_actual(raiz)
try:
    sucios = len(
        subprocess.run(
            ["git", "status", "--porcelain"], cwd=raiz, capture_output=True, text=True, timeout=5
        ).stdout.splitlines()
    )
except Exception:
    sucios = -1
dueno = "Miguel (merge owner)" if rama in ("main", "master") else rama.split("/")[0]
aviso_main = (
    "  ⚠ estás en main: crea tu rama `git switch -c <nombre>/<tema>`"
    if rama in ("main", "master") and not es_dueno("ALBERTITOS_MERGE_OWNER", "merge", raiz)
    else ""
)
lineas.append(f"- rama: {rama} (dueño: {dueno}) · ficheros sin commitear: {sucios}{aviso_main}")

env = raiz / ".env"
if env.exists():
    claves = [
        linea.split("=", 1)[0]
        for linea in env.read_text(errors="ignore").splitlines()
        if "=" in linea and not linea.startswith("#")
    ]
    tiene_key = any(k == "ANTHROPIC_API_KEY" for k in claves)
    lineas.append(
        f"- .env: presente ({len(claves)} variables){'' if tiene_key else ' · ⚠ falta ANTHROPIC_API_KEY'}"
    )
else:
    lineas.append(
        "- .env: NO existe → `cp .env.example .env` y pon la key del LLM (sin key, extract/ sólo usa caché)"
    )

erp_url = os.environ.get("ALBERTITOS_ERP_URL", "http://127.0.0.1:8009")
try:
    with urllib.request.urlopen(f"{erp_url}/erp/estado", timeout=1.5) as r:
        cuerpo = r.read().decode("iso-8859-1")
    import re

    asientos = re.search(r"<asientos>(\d+)</asientos>", cuerpo)
    lote2 = re.search(r"<actualizacion_cargada>(\w+)</actualizacion_cargada>", cuerpo)
    lineas.append(
        f"- ERP 2009: vivo en {erp_url} · asientos={asientos.group(1) if asientos else '?'} · lote2={lote2.group(1) if lote2 else '?'}"
    )
except Exception:
    lineas.append(
        f"- ERP 2009: no responde en {erp_url} → `make erp` (o `make erp-fast` para tests) en otra terminal"
    )

db = raiz / os.environ.get("ALBERTITOS_DB", "dist/albertitos.db")
if db.exists():
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        n_f = con.execute("select count(*) from ficheros").fetchone()[0]
        n_d = con.execute("select count(*) from decisiones where vigente=1").fetchone()[0]
        n_p = con.execute("select count(*) from eventos where estado='pendiente'").fetchone()[0]
        lineas.append(
            f"- BD: {db.name} · ficheros={n_f} · decisiones vigentes={n_d} · eventos pendientes={n_p}"
        )
    except Exception as e:
        lineas.append(f"- BD: {db.name} existe pero no se lee ({e}) → `make db`")
else:
    lineas.append("- BD: no existe → `make db` la crea")

try:
    from zoneinfo import ZoneInfo

    ahora = datetime.now(ZoneInfo("Europe/Madrid"))
    hitos = [
        ("lote 2 + norma v4", datetime(2026, 9, 19, 18, 0, tzinfo=ZoneInfo("Europe/Madrid"))),
        (
            "entrega de seguro (lote 1)",
            datetime(2026, 9, 19, 17, 30, tzinfo=ZoneInfo("Europe/Madrid")),
        ),
        ("congelación", datetime(2026, 9, 20, 2, 0, tzinfo=ZoneInfo("Europe/Madrid"))),
        ("entrega final", datetime(2026, 9, 20, 8, 0, tzinfo=ZoneInfo("Europe/Madrid"))),
        ("clonan el repo", datetime(2026, 9, 20, 10, 30, tzinfo=ZoneInfo("Europe/Madrid"))),
    ]
    proximos = [
        (n, (t - ahora).total_seconds() / 3600)
        for n, t in sorted(hitos, key=lambda x: x[1])
        if t > ahora
    ][:2]
    if proximos:
        lineas.append("- próximos hitos: " + " · ".join(f"{n} en {h:.1f} h" for n, h in proximos))
except Exception:
    pass

lineas.append(
    "- procedimientos: /sync /handoff /check /trace · skills: /entrega /lote2 /demo /benchmark /adr · lee el CLAUDE.md de tu módulo"
)
print("\n".join(lineas))
