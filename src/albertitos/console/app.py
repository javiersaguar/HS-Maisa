"""Consola de Alberto: Escalados · Traza · Panel. Sólo lectura sobre dist/albertitos.db.

Arranque: make console  (streamlit run src/albertitos/console/app.py)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

RUTA_BD = Path(os.environ.get("ALBERTITOS_DB", "dist/albertitos.db"))

st.set_page_config(page_title="Albertitos · cuentas a pagar", layout="wide")


@st.cache_resource
def conexion():
    from albertitos.core import db

    return db.conectar(RUTA_BD, solo_lectura=True)


def consulta(sql: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, conexion(), params=params)


if not RUTA_BD.exists():
    st.error(f"No existe {RUTA_BD}. Ejecuta `make db && uv run albertitos ingest` (o `make run`).")
    st.stop()

st.title("Albertitos · cuentas a pagar de Alberto")
tab_esc, tab_traza, tab_panel = st.tabs(["Escalados", "Traza", "Panel"])

with tab_esc:
    st.subheader("Cola de revisión humana")
    df = consulta(
        """SELECT d.file_id, d.resultado, d.norma_version, d.motivos_json, d.decidido_en
           FROM decisiones d WHERE d.vigente=1 AND d.resultado IN ('ESCALAR','NO_PAGAR') ORDER BY d.file_id"""
    )
    if df.empty:
        st.info("No hay escalados todavía.")
    else:
        df["motivo"] = df["motivos_json"].map(
            lambda s: next(
                (m["regla_id"] + ": " + m["detalle"] for m in json.loads(s) if not m["ok"]), ""
            )
        )
        st.dataframe(
            df[["file_id", "resultado", "motivo", "norma_version", "decidido_en"]],
            width="stretch",
            hide_index=True,
        )
        elegido = st.selectbox("Ver evidencia de", df["file_id"].tolist())
        if elegido:
            motivos = json.loads(df.loc[df.file_id == elegido, "motivos_json"].iloc[0])
            for m in motivos:
                (st.success if m["ok"] else st.error)(f"**{m['regla_id']}** · {m['detalle']}")
                if m.get("evidencia"):
                    st.json(m["evidencia"], expanded=False)

with tab_traza:
    st.subheader("Seguir una decisión")
    ficheros = consulta("SELECT file_id FROM ficheros ORDER BY file_id")["file_id"].tolist()
    fid = st.selectbox("file_id", ficheros) if ficheros else None
    if fid:
        from albertitos.core import db

        t = db.traza(conexion(), fid)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Fichero**")
            st.json(t["fichero"], expanded=False)
            st.markdown("**Hechos extraídos**")
            for h in t["hechos"]:
                st.json(json.loads(h["hechos_json"]), expanded=True)
        with c2:
            st.markdown("**Decisiones (la última es la vigente)**")
            for d in t["decisiones"]:
                st.markdown(
                    f"`{d['resultado']}` · norma {d['norma_version']} · maestro {d['maestro_version']} · erp {d['erp_version']} · corte {d['fecha_corte']}"
                )
                for m in json.loads(d["motivos_json"]):
                    st.markdown(
                        ("✅ " if m["ok"] else "❌ ") + f"**{m['regla_id']}** {m['detalle']}"
                    )
        st.markdown("**Eventos** (latencia, reintentos, tokens, coste)")
        st.dataframe(pd.DataFrame(t["eventos"]), width="stretch", hide_index=True)

with tab_panel:
    st.subheader("Operación")
    tot = consulta("SELECT lote, count(*) n FROM ficheros GROUP BY lote")
    dec = consulta(
        "SELECT resultado, count(*) n FROM decisiones WHERE vigente=1 GROUP BY resultado"
    )
    pend = consulta(
        """SELECT count(*) n FROM ficheros f LEFT JOIN decisiones d ON d.sha256=f.sha256 AND d.vigente=1 WHERE d.id IS NULL"""
    )["n"].iloc[0]
    c = st.columns(4)
    c[0].metric("Ficheros", int(tot["n"].sum()) if not tot.empty else 0)
    for i, r in enumerate(["PAGAR", "ESCALAR", "NO_PAGAR"], start=1):
        c[i].metric(r, int(dec.loc[dec.resultado == r, "n"].sum()) if not dec.empty else 0)
    st.metric("Sin decisión vigente (pendientes)", int(pend))
    st.markdown("**Eventos por etapa y estado**")
    st.dataframe(
        consulta(
            """SELECT etapa, estado, count(*) n, round(avg(latencia_ms)) lat_media_ms, round(coalesce(sum(coste_eur),0),4) coste_eur,
                      sum(intento>1) reintentos, coalesce(sum(tokens_in),0) tokens_in, coalesce(sum(tokens_out),0) tokens_out
               FROM eventos GROUP BY etapa, estado ORDER BY etapa, estado"""
        ),
        width="stretch",
        hide_index=True,
    )
    snaps = consulta("SELECT tipo, version, creado_en FROM snapshots ORDER BY creado_en")
    st.markdown("**Versiones cargadas (maestro / ERP)**")
    st.dataframe(snaps, width="stretch", hide_index=True)
    st.markdown("---")
    if st.button("Reprocesar impactados (norma v3, ERP más reciente)"):
        with st.spinner("reprocesando…"):
            r = subprocess.run(
                [sys.executable, "-m", "albertitos.cli", "reprocess", "--impacted"],
                capture_output=True,
                text=True,
            )
        st.code(r.stdout + r.stderr)
        st.cache_resource.clear()
