# Ensayo E3 · ciclo 5 · 19/09/2026

**Ensayo aislado:** `dist/ensayo/ensayo.db` (backup SQLite de la real), salida `dist/ensayo/entrega`, material `data/fixtures/lote2_sim`. Las 500 decisiones de partida eran 443 PAGAR / 48 ESCALAR / 9 NO_PAGAR. E3 no ha escrito en la BD real, su entrega ni data/. La comparación global detecta cambios concurrentes, detallados al final.

El flujo íntegro se ha medido: 10 nuevos hechos, 20 marcas de duplicado, nueve originales pasan a ESCALAR; el diff posterior de ERP recalcula sólo dos facturas. **La primera auditoría sale ROJO por el `"None"` heredado de scan_025**. Se detiene package final, se prueba la recuperación en la copia y se registra debajo; eso no autoriza una entrega real ni resuelve la política de Mónica.

Los tiempos siguientes son de pared por comando, incluyendo inicio de Python/CLI. **Ensayo caliente: 8 plantillas y 2 escaneadas ya cacheadas, 0 tokens nuevos / 0 EUR.** No compararlo como si las 2 escaneadas se hubieran vuelto a leer por red. Para visión fría, D1 midió 0,065–0,106 facturas/s con doble lectura en `ESCALA-10K.md`.

## 19/09 13:12 · ensayo general con `main` — EJECUTADO (Javier, con los scripts de J1)

I1 (ciclo 9) y J1 (ciclo 10) se quedaron sin terminal y J1 dejó la receta en dos scripts. Javier los ejecutó con
tres arreglos del propio script: publicar con `--sin-gh` y `ENTREGA_REPO` apuntando al repo local, `make plan-pdf`
antes de publicar (en un worktree limpio no hay PDF generado) y el patrón del rojo forzado sin espacios, como se
guarda el JSON. Ahora están versionados en `scripts/ensayo/lote2-ensayo.sh` y `scripts/ensayo/lote2-desvio-p05.sh`;
cada uno deja `dist/ensayo/j1/{tiempos,p05-tiempos}.tsv`.

**Resultado:** 14 PDFs (10 de `lote2_sim` y 4 de `lote2_identicos`), **14,3 s de principio a fin, todo en verde**. Los
tiempos por paso están en `CHULETA-LOTE2.md`. Lo que conviene saber:
- `run --erp v1`: los dos lotes APTO. El verificador avisa (no para) de las 4 copias exactas, gracias a P0-1.
- `erp pull --tag v2` desde `:8011`: **3,9 s** (519 asientos, 30 consultas, 2 reintentos). `reprocess --impacted`: 2 de 510, los dos cambios que mete el CSV simulado (`F26-9865` → NO_PAGAR, `2026-06-27_P001` → ESCALAR).
- `duplicados: +20`: los PDFs de `lote2_sim` son copias de facturas del lote 1 (mismo pedido), así que en el ensayo el lote 1 baja a 427/63/10. Es un efecto del material simulado, no del código.
- Desvío rojo: `package` se niega (exit 1). Con `--aceptar-rojo` entrega y deja «roja aceptada: <motivo>» en el emit.
- `make publicar` en seco contra un repo bare local: VERDE.
- **Desvío P0-5:** 39 s del ROJO del verificador a los dos lotes APTO (36 s son el `make check`). `2026-01-16_P004.pdf` sale en los dos lotes, ESCALAR. **Encontrado aquí:** con `ALBERTITOS_DB` exportada, `make check` daba 8 fallos en `test_publicar_entrega`, que leía la BD del entorno. A las 18:00 habría parecido que el merge de P0-5 rompía algo. Arreglado en `tests/test_publicar_entrega.py`.
- **No medido:** la visión de escaneadas nuevas (las simuladas ya estaban en la caché). Hay que contar 0,065–0,106 escaneadas/s con doble lectura.

La revisión estática de J1, que ya estaba aplicada en la skill y la chuleta, se confirmó ejecutando:
1. **`run --erp` existe** (`cli.py`): sobra la rama `if … grep -q -- '--erp'` y la alternativa
   `extract` + `reprocess --todo`, que la skill daba como obligatoria.
2. **`package` ya audita** y se niega en rojo salvo `--aceptar-rojo "<motivo>"`.
3. **P0-5 tiene salida y es un merge** (`miguel/p0-5-nombre-repetido`); medido arriba.

Trampa que sólo afecta a los ensayos: `cli.LOTE2` es la constante `Path("data/lote2")`, así que `run`, `package` y
`validate --lote 2` **no** leen `ALBERTITOS_DIR_LOTE2`. Por eso los scripts montan un worktree y copian el material a
`data/lote2/facturas`.
