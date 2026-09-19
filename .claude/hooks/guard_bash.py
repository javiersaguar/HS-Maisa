"""PreToolUse(Bash): prohibiciones reales del equipo, con mensaje de qué hacer en su lugar.

Complementa permissions.deny (que es literal por prefijo) con comprobaciones de contexto:
rama actual, ficheros en stage, hosts de red. Sale con JSON deny/ask; nunca bloquea en silencio.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from _common import decidir, es_dueno, leer_entrada, raiz_proyecto, rama_actual

datos = leer_entrada()
cmd_original = (datos.get("tool_input") or {}).get("command") or ""
raiz = raiz_proyecto(datos)
rama = rama_actual(raiz)
dueno_merge = es_dueno("ALBERTITOS_MERGE_OWNER", "merge", raiz)
dueno_contratos = es_dueno("ALBERTITOS_CONTRACT_OWNER", "contratos", raiz)


def sin_heredocs(texto: str) -> str:
    """Quita el cuerpo de los heredocs (cat > f <<'EOF' ... EOF): es contenido, no comandos.

    Sin esto, un agente que escribe documentación con la frase "git push main" quedaría bloqueado.
    """
    salida: list[str] = []
    terminador: str | None = None
    for linea in texto.split("\n"):
        if terminador is not None:
            if linea.strip() == terminador:
                terminador = None
            continue
        salida.append(linea)
        m = re.search(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", linea)
        if m:
            terminador = m.group(1)
    return "\n".join(salida)


RE_GIT_C = re.compile(r"\bgit\s+-C\s+(\"[^\"]*\"|'[^']*'|\S+)")


def repo_objetivo(texto: str, raiz: Path) -> tuple[Path, bool]:
    """Sobre qué repositorio actúa este comando y si es el repo de la solución.

    `git -C <ruta> push` actúa sobre otro repo: sin esto, el runbook de entrega
    (`git -C ../HS-Maisa-Entrega push -u origin HEAD:main`) quedaría bloqueado por la regla de
    "main es de Miguel", que sólo habla de ESTE repo, y además `git -C . push --force` se saltaría
    la regla 1 por la forma del patrón.
    """
    m = RE_GIT_C.search(texto)
    if m is None:
        return raiz, True
    ruta = m.group(1).strip("\"'")
    if (
        "$" in ruta or "`" in ruta
    ):  # variable sin expandir: no arriesgamos, tratamos como el nuestro
        return raiz, True
    destino = (raiz / ruta).resolve()
    if not destino.is_dir():
        return raiz, True
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=destino,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except Exception:
        return destino, True
    if not top:
        return destino, True
    return Path(top), Path(top) == raiz


cmd = sin_heredocs(cmd_original)
objetivo, es_solucion = repo_objetivo(cmd, raiz)
if not es_solucion:
    rama = rama_actual(objetivo)
# `git -C <ruta> push` tiene que casar con los mismos patrones que `git push`.
cmd = RE_GIT_C.sub("git", cmd)

# Cada trozo separado por operadores de shell se evalúa por separado y también el comando entero.
trozos = [t.strip() for t in re.split(r"&&|\|\||;|\||\n", cmd) if t.strip()] + [cmd]


def alguno(patron: str) -> bool:
    return any(re.search(patron, t) for t in trozos)


# 1. Push forzado: prohibido para todos. Sincronizamos con merge, así que nunca hace falta.
if alguno(r"\bgit\s+push\b.*(\s--force(-with-lease)?\b|\s-f\b|\s\+\S+)"):
    decidir(
        "deny",
        "Push forzado prohibido. Este equipo sincroniza con `git merge origin/main` (/sync), "
        "no con rebase, así que tu rama nunca necesita --force. Si de verdad hay que "
        "reescribir historia, lo hace Miguel a mano.",
    )

# 2. main es de Miguel: ni commit, ni merge hacia main, ni push a main.
en_main = rama in ("main", "master")
if not dueno_merge and es_solucion:
    if en_main and alguno(r"\bgit\s+(commit|merge)\b"):
        decidir(
            "deny",
            f"Estás en la rama `{rama}` y sólo Miguel commitea/mergea ahí. Crea tu rama: "
            "`git switch -c <nombre>/<tema>` (ej. javier/erp-cliente) y vuelve a intentarlo.",
        )
    if alguno(r"\bgit\s+push\b.*(\bmain\b|\bmaster\b|HEAD:main)") or (
        en_main and alguno(r"\bgit\s+push\b")
    ):
        decidir(
            "deny",
            "Nadie hace push a main salvo Miguel. Sube tu rama (`git push -u origin <rama>`) "
            "y pide el merge con /handoff.",
        )

# 3. Historia destructiva. (permissions.deny ya cubre rebase/reset --hard/clean; esto añade el resto)
if alguno(r"\bgit\s+branch\s+.*-D\b") or alguno(r"\bgit\s+stash\s+(drop|clear)\b"):
    decidir(
        "deny",
        "Borrar ramas o stashes destruye trabajo de otros. Si sobra una rama, dilo en el canal "
        "y la borra su dueño. Para descartar cambios propios usa `git stash` (sin drop).",
    )
if alguno(r"\bgit\s+checkout\s+--\s"):
    decidir("ask", "Esto descarta cambios locales sin copia. ¿Seguro? Alternativa: `git stash`.")

# 4. rm sobre lo que no se regenera.
if alguno(r"\brm\s+(-\w*r\w*|--recursive)\b.*(\bdata/|\.git\b|\s/\s|\s~|\*\s*$)"):
    decidir(
        "deny",
        "No se borra data/, .git ni la raíz. data/caja es inmutable; si necesitas un "
        "dataset alterado, cópialo a data/fixtures/. dist/ sí se puede limpiar con `make clean`.",
    )

# 5. Los outcomes no se escriben a mano (ni con echo > ni con tee).
if alguno(r"(>|>>|\btee\b)\s*\S*outcomes\S*\.jsonl") or alguno(
    r"(>|>>|\btee\b)\s*\S*albertitos_plan\.pdf"
):
    decidir(
        "deny",
        "Los entregables se generan, no se escriben: `make package` (JSONL) y `make plan-pdf` (PDF). "
        "Así pasan el validador y quedan ligados a la BD.",
    )

# 6. Contratos congelados también por shell (sed -i, redirecciones, mv/cp/rm).
if not dueno_contratos and alguno(
    r"(sed\s+-i|>|>>|\btee\b|\bmv\b|\bcp\b|\brm\b|\bpatch\b).*src/albertitos/core/"
):
    decidir(
        "deny",
        "src/albertitos/core/ son los contratos congelados y sólo Miguel los cambia. Propón el "
        "cambio en el canal con el campo y el motivo. Si eres Miguel: ALBERTITOS_CONTRACT_OWNER=1 "
        "en .claude/settings.local.json → env.",
    )

# 7. pip prohibido: rompe el lockfile. (permissions.deny cubre `pip install`; esto cubre python -m pip)
if alguno(r"python3?\s+-m\s+pip\s+install") or alguno(r"\buv\s+pip\s+install"):
    decidir(
        "deny", "Dependencias con `uv add <paquete>` (actualiza pyproject y uv.lock). Nada de pip."
    )

# 8. Secretos en stage: comprobado en el momento del commit.
if alguno(r"\bgit\s+commit\b"):
    try:
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=objetivo,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.split()
    except Exception:
        staged = []
    malos = [
        p
        for p in staged
        if re.search(r"(^|/)\.env($|\.)|\.(pem|key)$|(^|/)(la-caja-outcomes|HS-Maisa-Entrega)/", p)
        and not p.endswith(".env.example")
    ]
    if malos:
        decidir(
            "deny",
            f"Hay secretos o ficheros prohibidos en stage: {malos}. Sácalos con "
            "`git restore --staged <fichero>` y revisa .gitignore. La key del LLM sólo vive en .env.",
        )
if alguno(r"\bgit\s+add\b.*(\s|/)\.env(\s|$)"):
    decidir(
        "deny",
        ".env nunca va al repo. Está en .gitignore por algo. Usa .env.example para documentar variables.",
    )

# 9. Red hacia fuera: las facturas no salen del portátil salvo al LLM vía SDK.
m = re.search(r"\b(curl|wget)\b\s+(?:-\S+\s+)*[\"']?(https?://)?([\w.-]+)", cmd)
if m:
    host = m.group(3).lower()
    permitidos = (
        "127.0.0.1",
        "localhost",
        "astral.sh",
        "github.com",
        "raw.githubusercontent.com",
        "code.claude.com",
    )
    if not any(host == h or host.endswith("." + h) for h in permitidos):
        decidir(
            "ask",
            f"curl/wget hacia `{host}`. Los datos de la Caja no salen del portátil salvo al LLM por el SDK. "
            "Si es documentación, usa WebFetch. Si es legítimo, confirma.",
        )

# 10. El ERP con latencia en tests desperdicia minutos: avisar, no bloquear.
if alguno(r"alberto_erp\.py") and not alguno(r"--rapido") and alguno(r"pytest"):
    decidir(
        "ask",
        "Vas a correr tests contra el ERP con latencia artificial. Mejor `make erp-fast` en otra terminal.",
    )

raise SystemExit(0)
