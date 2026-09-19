# Contraste de la muestra · tres lecturas independientes y el sistema

**Estado (19/09 10:41):** método y comando. **Sin etiquetas** hasta que Mónica cierre la suya: a esa hora
`esperado_muestra.csv` sigue en 0 de 21. La tercera lectura (agente H2) está hecha y guardada fuera del repo.

## Por qué
La muestra de 21 facturas (`data/fixtures/muestra.txt`) es lo único que valida la norma como código contra algo que
no es la norma como código. Sólo vale si cada lectura es a ciegas: si quien etiqueta ve antes lo que decide el
sistema, su etiqueta deja de ser una comprobación y pasa a ser una confirmación.

## Las lecturas
| Lectura | Fuentes | Lo que no vio |
|---|---|---|
| Mónica · Alfonso (`esperado_muestra.csv`) | los PDFs, el Excel (norma `Norma_Pagos_v3`, maestro, pedidos), el ERP | el sistema, la columna del otro, la del agente |
| Agente H2 (`esperado_muestra_agente.csv`, fuera del repo hasta el cierre) | las mismas. El ERP, bajado del bridge por su cuenta (516 asientos, idénticos al snapshot `v1`). Las escaneadas, como imagen. Las dos páginas de `2026-01-25_P001.pdf` | durante la lectura, nada de `hechos`/`decisiones`/`eventos`/`cache_llm`, `rules/`, trazas, auditoría ni `docs/agentes/`. **Contaminación declarada:** antes del encargo, la sesión había leído documentos que citan una decisión del sistema de una de las 21 y la política NO_PAGAR; afecta a una etiqueta de forma directa y a cinco de forma leve, marcadas en su CSV (detalle en el parte de H2) |
| Sistema | los hechos extraídos + la norma v3 como código, decisión vigente de la BD | — |

Cada etiqueta del agente lleva motivo, lo comprobado (campos y fuentes), confianza (alta/media/baja) y la duda
concreta.

## El comando
```bash
uv run python scripts/comparar_muestra.py                  # hoy: sólo lo humano; sistema y agente, ocultos
uv run python scripts/comparar_muestra.py --markdown       # la tabla, para pegarla aquí
```
- Mientras la parte humana no esté cerrada (`acordado` completo, o `esperado_monica` completo si Alfonso no ha
  etiquetado), el script **no enseña la columna del sistema ni la del agente, y ni siquiera abre la BD**.
- Para verlas antes: `--revelar-sistema` / `--revelar-agente` con `--motivo "<por qué>"`. La salida lo dice en la
  primera línea. Nadie que esté etiquetando debería usarlo.
- Arriba, las coincidencias por pares; después, las discrepancias (filas donde las columnas visibles no coinciden);
  al final, la tabla con el motivo principal del sistema (la primera regla que falla). Una columna vacía se dice y
  no cuenta.
- Tests: `tests/test_comparar_muestra.py` (10: no revela sin cerrar, ni con la BD real, se cierra también sin
  Alfonso, `--motivo` obligatorio, NFC, sólo la decisión vigente, etiquetas inválidas, Markdown).

Salida de hoy, literal:
```
CONTRASTE DE LA MUESTRA
Muestra humana: abierta · acordado 0/21 · Mónica 0/21 · Alfonso 0/21
Agente: oculta. La muestra humana no está cerrada (acordado 0/21 · Mónica 0/21 · Alfonso 0/21). Antes de tiempo: --revelar-agente --motivo "..."
Sistema: oculta. La muestra humana no está cerrada (acordado 0/21 · Mónica 0/21 · Alfonso 0/21). Antes de tiempo: --revelar-sistema --motivo "..."
```

## Cuando Mónica cierre
1. `cp dist/ensayo/h2/esperado_muestra_agente.csv data/fixtures/` y commit (`fixtures: tercera lectura de la muestra`).
2. `uv run python scripts/comparar_muestra.py --markdown` y pegar la tabla aquí.
3. Para cada discrepancia (una persona ≠ sistema, o una persona ≠ agente), su dueño y la siguiente acción:
   - **REGLA:** la norma como código decide distinto de lo que dice la norma de Alberto → Mónica, con el test que lo fija.
   - **DATO:** los hechos extraídos están mal (ahora sí: `albertitos trace <file_id>`) → Javier, con el campo y el valor.
   - **ETIQUETA:** se equivocó una persona o el agente → quién y por qué, con la fuente. Si es el agente, se dice.
4. Lo que cambie en la norma o en la extracción, con `PIDO A Mónica` / `PIDO A Javier` en la bitácora y antes de las
   17:00, para que la entrega de las 17:30 ya lo lleve.
