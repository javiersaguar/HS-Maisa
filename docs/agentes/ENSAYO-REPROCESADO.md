# Ensayo del reprocesado por linaje (19/09, 02:40)

El sábado a las 18:00 llegan tres cosas a la vez: 40 PDFs nuevos, un ERP actualizado y una regla nueva.
Todo el plan se apoya en que **no hay que recalcular las 500 decisiones del lote 1 por cada cambio**, sino
sólo las que el cambio toca. Eso lo hacen `pipeline/linaje.py` y `albertitos reprocess --impacted`, que
hasta ahora sólo estaban comprobados con fixtures de tres ficheros. Esto es el ensayo con la Caja entera.

## Cómo se montó

Copia de la BD real con `sqlite3.backup()` (nunca `cp`: el WAL) a `dist/ensayo-linaje.db`, y sobre ella un
snapshot de ERP `v2-ensayo` construido a partir del `v1` vigente, con los tres cambios que de verdad
esperamos del sábado:

| Cambio | Cuántos | Qué debería pasar |
|---|---|---|
| Asientos `PENDIENTE` → `PAGADA` | 25 pedidos con factura | la factura ya no se paga |
| `importe_esperado` +10 % | 15 pedidos con factura | descuadre contra el importe de la factura |
| Asientos nuevos (`PO-2026-09xx`) | 40 | no deben tocar a nadie del lote 1 |

## Qué salió

```
$ ALBERTITOS_DB=dist/ensayo-linaje.db albertitos reprocess --impacted --erp v2-ensayo
destino: norma v3 · corte 2026-09-18 · maestro 80911e429c6c · erp v2-ensayo
duplicados: +0 −0 · sin impacto por diff: 460 · pendientes sin hechos: 0
40 de 500 recalculadas · 40 cambian · 0.78 s
```

- **40 de 500**, exactamente las 25 + 15 tocadas. Los 40 asientos nuevos no arrastraron a nadie: el diff
  mira pedido y NIF, y un pedido que no existía no aparece en ninguna decisión anterior.
- Las 460 restantes quedaron con un evento `decide/skip` "sin impacto", que es lo que hace auditable
  *por qué no se recalcularon*. Sin ese evento, un juez sólo vería decisiones viejas con un ERP nuevo.
- Los cambios son del tipo correcto: `PAGADA` → **NO_PAGAR** (25 casos), importe que no cuadra →
  **ESCALAR** (15 casos). Ninguna pasó a PAGAR.

Y el camino caro, el de la regla nueva, que por diseño recalcula todo:

```
$ ALBERTITOS_DB=dist/ensayo-linaje.db albertitos reprocess --todo --erp v2-ensayo
500 de 500 recalculadas · 0 cambian · 7.06 s
```

## Lo que hay que llevarse al sábado

1. **La norma v4 no es un problema de tiempo**: rehacer las 500 decisiones cuesta 7 s. Mónica puede
   iterar la regla todas las veces que quiera hasta las 19:00; no hay que racionar pasadas.
2. **El cuello de botella del lote 2 es la extracción**, no la decisión: las escaneadas van a 0,065–0,106
   ficheros/s (ver `RESILIENCIA-Y-COSTE.md` §4). Si a las 18:00 algo va lento, es el LLM, no el linaje.
3. **El orden correcto es ERP primero, norma después.** Con el ERP nuevo se reprocesa lo impactado
   (segundo escaso) y se ve enseguida qué facturas cambian de veredicto; si se mete antes la norma nueva,
   el `--todo` mezcla los dos efectos y ya no se sabe cuál causó qué.
4. `reprocess` **no toca lo pendiente sin hechos**: lo dice en su cabecera (`pendientes sin hechos: 0`).
   Si el LLM se cae durante el lote 2, esa línea será distinta de 0 y hay que mirarla antes de entregar.

La copia del ensayo se queda en `dist/ensayo-linaje.db` (gitignored) por si alguien quiere repetirlo; la BD
buena no se tocó en ningún momento.
