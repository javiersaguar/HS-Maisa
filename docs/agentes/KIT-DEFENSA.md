# Chuleta de la defensa · bloque 4 (resiliencia, 2 min) · para Alfonso

Tiempos medidos el 19/09 a las 15:55 por R4 (revisión PLAN-12), con el código de `main` de ese momento y un kit equivalente, en un clon limpio
(`git worktree add … HEAD --detach`) en el portátil de Javier: `bootstrap` 2,3 s · `kit instalar` 0,2 s · `status` 0,3 s
· `trace` 0,2 s · `demo_caos --sin-red` **3,7 s** · `dato_en_vivo --pagada PO-2026-0001` **0,7 s** · bonus 0,2 s · chat
0,3 s. Todo con exit 0. **En el de Alfonso serán otros: cronométralos al llegar.** Todo es bash (WSL, Linux o Mac).
Antes de salir de casa: `bash scripts/smoke.sh` (6 pasos, 2,5 s aquí, `VEREDICTO: OK`).

## Antes de salir de casa (con red)
1. `git pull --ff-only && ./bootstrap.sh`. La primera vez descarga dependencias: necesita red. El merge de
   `miguel/pipeline` **ya está en `main` (`8935c3e`)**: trae el `trace` legible, el `status` nuevo y las copias exactas.
2. Copia el kit que te pase Javier a `dist/kit/` e instálalo: `make kit-instalar KIT=dist/kit/albertitos-kit-<fecha>.tar.gz`.
   Tiene que acabar en `VEREDICTO: instalado` con `ficheros {'1': 500}`, **438 PAGAR · 53 ESCALAR · 9 NO_PAGAR** y caché 881.
   **Usa el kit `albertitos-kit-20260919-1337.tar.gz`** (1,4 MB, esquema v3 con `identidades`), el que te pasó Javier.
   R4 hizo uno equivalente a las 15:55 en la carpeta de revisión, con los mismos recuentos (438/53/9). Los de las 13:17 y
   las 10:07 sirven de repliegue; el de las 10:07 es de esquema v2.
   Si te pide `--forzar`, es que ya tenías una BD con datos: añade `ARGS=--forzar` (la anterior queda en `…antes-del-kit`).
3. `uv run albertitos status` (los mismos recuentos) y `make console` una vez: tres pestañas, Panel con 500/438/53/9.
4. `bash scripts/smoke.sh`: una línea por paso, acaba en `VEREDICTO: OK` (~3 s). Si FALLA, no salgas.
5. Ensaya el bloque entero con cronómetro. El ERP no hace falta para nada de esto.

## En la sala, en orden
| # | Comando | Qué se ve (una línea) | Tarda | Qué dices |
|---|---|---|---|---|
| 1 | `uv run python scripts/demo_caos.py --sin-red` | paso 1: `run → exit 1 · entrega escrita: no` y las 3 facturas `extract pendiente (LLM-DOWN) → decide skip → emit pendiente · decisión: NINGUNA` | todo, ~3,7 s | «Se cae el proveedor: tres facturas quedan pendientes, ninguna se paga a ciegas y la entrega se niega a salir incompleta.» |
| | (mismo comando) | paso 2: `run → exit 0 · outcomes.jsonl 1ec4be206089` (el de la entrega publicada `232bb76`, el mismo que imprime `kit-instalar`) | | **«La vuelta la sirvo desde la caché para no depender del wifi.»** Prueba que el pipeline reanuda, no que el proveedor conteste |
| | (mismo comando) | paso 3: `(igual: True)` | | «Repetir no llama a nadie ni duplica nada: la identidad es el sha256. Y es el mismo hash que la entrega oficial.» |
| 2 | los 5 comandos de RESILIENCIA §3 (b bis), tal cual, con `chaos --llm-down` antes del `extract` | `{'LLM-DOWN': 5, 'LLM-CIRCUIT-OPEN': 3}` | ~2 s el bloque | «A partir del quinto fallo dejamos de castigar al proveedor. Lo pendiente sigue pendiente.» |
| 3 | consola → Traza → `copia_2026_0518.pdf` | eventos `LLM-DOWN` y `LLM-INVALID` del viernes y, después, la extracción buena | — | «Esto no es un ensayo: pasó el viernes con esta factura, y se reanudó sin tocar nada.» |
| 4 | `uv run python -m albertitos.bonus --salida dist/bonus --tope-semanal 150000` | `decisiones_pagar` 438 · calendario 2.428.159,06 EUR · `Calendario: dist/bonus/calendario.html` | ~0,2 s | «Los PAGAR, en un calendario. Es un borrador, no una orden bancaria.» |
| 5 | `uv run python -m albertitos.chat "paga la factura F26-2201_transportes.pdf"` | `"estado": "solo_lectura"` · `"modelo": "sin_modelo"` · `"latencia_ms": 0` | ~0,3 s | «El chat no paga. Si le pides que pague, se niega en local y no llama al modelo.» |

`status` enseña el último evento de cada fichero: el `extract pendiente 7` y los `2.3823 EUR` del viernes ya no salen
(sólo con `status --historico`). Si salen ahí o en el Panel de la consola: «son eventos del viernes; los 7 pendientes
son pruebas de caos de ficheros que luego se extrajeron bien (0 sin decisión), y los 2,38 € son una tarifa inventada
que corregimos: los modelos que usamos no cobran por token».

## Si el tribunal cambia un dato (la pregunta del domingo)
Un comando, sobre una **copia** (`dist/vivo.db`): ni la BD real ni la entrega se tocan, así que se puede repetir
delante de ellos las veces que haga falta y siempre sale lo mismo.

```bash
uv run python scripts/dato_en_vivo.py --listar               # pedidos que hoy se pagan y siguen PENDIENTE
uv run python scripts/dato_en_vivo.py --pagada PO-2026-XXXX  # ese asiento pasa a PAGADA en el ERP
```

Enseña, en este orden: el dato que cambia → `reprocess --impacted` → **N de 500 recalculadas, K cambian** → la traza
legible de la que cambió. Lo que dices: «cambiar un asiento no nos obliga a repasar 500 facturas. El linaje sabe qué
decisiones dependían de ese pedido: recalcula ésas y las demás conservan la versión con la que se tomaron» (ADR-0006).

También admite `--importe PEDIDO=1234,56`, `--iban P003=ES…`, `--estado-pedido PEDIDO=ANULADO` y `--fecha-corte`.
Nunca se cambia una decisión a mano: se cambia el dato, y vuelve a decidir la norma.

Medido el 19/09 a las 13:17 en el portátil de Javier, sobre una copia de la BD real (438/53/9). La BD real y la entrega
no cambian (mismas huellas antes y después):

| Comando | Qué pasa | Tarda (entero / reproceso) |
|---|---|---|
| `--listar` | 10 pedidos que hoy se pagan y siguen PENDIENTE | 0,16 s |
| **`--pagada PO-2026-0003`** (el de la demo) | `factura_8764.pdf` PAGAR → **NO_PAGAR**; **1 de 500 recalculadas** | **0,51 s** / 0,02 s |
| `--importe PO-2026-0006=1200,00` | `2026-05-04_P011.pdf` PAGAR → ESCALAR; 1 de 500 | 0,53 s / 0,02 s |
| `--iban P003=ES…392` | 51 de 500 recalculadas (todas las de P003), 45 cambian a ESCALAR | 0,55 s / 0,03 s |
| `--estado-pedido PO-2026-0007=ANULADO` | 1 de 500 recalculada y **0 cambian**: la norma v3 no lee el estado del pedido del Excel (lo decide Mónica; ver la bitácora de J2). **No lo uses en la sala** | 0,37 s |
| `--fecha-corte 2026-01-31` | 500 de 500 recalculadas, 388 cambian (fechas futuras respecto al corte) | 0,58 s / 0,09 s |

El hito de `docs/hitos.md` pedía < 30 s; sale **por debajo de un segundo**. Hay que volver a cronometrarlo en el portátil
de Alfonso, que puede ser más lento.

**19/09, 20:30 · arreglado tras el ADR-0021.** Desde que cada lote se decide en su contexto, `reprocess` con `--norma`
y sin `--lote` se niega, y **`dato_en_vivo.py` dejaba de funcionar** («el reproceso falló (exit 2)»). Ahora lleva
`--lote` (1 por defecto), y hay un test que corre la demo entera contra una copia de la BD real. Si el tribunal cambia
un dato del lote 2: `--lote 2 --norma v4`, una vez integrado el lote 2.

### Si nos dan el fichero de la Caja ya cambiado
La web dice «el domingo Alberto **podrá cambiar un dato de la Caja**»: puede que no nos pidan un cambio, sino que nos
den el Excel (o un CSV) ya tocado. Entonces el camino es el de verdad: el fichero entra como un maestro nuevo, versionado
por contenido, y el linaje redecide lo que depende de él. Ensayado con `scripts/ensayo/dato-cambiado.sh`, que hace
eso mismo sobre una copia (cambia el dato en una copia del Excel, `albertitos maestro --ruta`, `reprocess --impacted
--lote 1`, la lista completa de las que cambian y la traza de la primera):

| Ensayo (19/09 20:26, copia de la BD real) | Qué pasa | Tarda (entero) |
|---|---|---|
| `bash scripts/ensayo/dato-cambiado.sh` (IBAN de P006) | **50 de 500 recalculadas** (todas las de P006), **43 cambian** PAGAR → ESCALAR por `v3.R1` | 1,4 s |
| `bash scripts/ensayo/dato-cambiado.sh importe PO-2026-0096 2500.00` | 1 de 500: `2026-01-08_P001.pdf` PAGAR → ESCALAR por `v3.R2` (3012.89 frente a 2500.00) | 1,3 s |

En la sala, con el fichero que nos den (sobre una copia, nunca sobre la BD de la entrega):
```bash
ALBERTITOS_DB=dist/vivo.db uv run albertitos maestro --ruta <el Excel que nos den>
ALBERTITOS_DB=dist/vivo.db uv run albertitos reprocess --impacted --lote 1 --fecha-corte 2026-09-18
ALBERTITOS_DB=dist/vivo.db uv run albertitos trace <una de las que cambian>
```
La traza lo cuenta sola: en MAESTRO, el Excel nuevo; en RESULTADO, «por: maestro 80911e429c6c→f8521fc22430:
PO-2026-0096», y debajo **«entregado 19/09: outcomes.jsonl → PAGAR»**. Es decir, lo que entregamos y lo que diríamos
hoy, sin tocar la entrega. **Límite que hay que decir:** si cambian un CSV del lote 2, el comando es `maestro --lote2
<carpeta>` y `reprocess --impacted --lote 2 --norma v4 --erp v2`.

## Si algo falla
- **La demo no arranca:** enseña `docs/demo/transcripcion-demo-caos.txt` (la misma demo con red, 104 s, tokens incluidos).
- **La consola no abre:** `uv run albertitos status` y `uv run albertitos trace F26-2201_transportes.pdf` en la terminal.
  `trace` sale legible, un paso por bloque (hechos → maestro → ERP → duplicado → reglas → resultado) y con la vigente
  primero en el historial; `docs/demo/trazas/README.md` dice qué mirar.
- **No hay ERP en la sala:** da igual para la demo (se comprobó apagándolo). Sólo fallan `erp pull` y el preflight.
- **Antes de salir:** `bash scripts/smoke.sh`. Si no acaba en `VEREDICTO: OK`, no montes la sala.

## Qué pregunta responde cada cosa
- **Caída** → paso 1: PENDIENTE, `package` se niega, nada se paga sin hechos.
- **Timeout** → mismo camino: 3 intentos y PENDIENTE. Límites de 60 s (texto) y 90 s (visión). Ensayado con
  `llm_timeout` en CONTRASTE-TOTAL §7 (3 facturas → `LLM-TIMEOUT` ×3 → 0 hechos, 0 decisiones). No está en la CLI.
- **Rate limit** → respetamos `Retry-After`: 429 simulado, 5/5 recuperadas en el 2.º intento (RESILIENCIA §3 (b), con red).
- **Respuesta inválida** → reintento y, tras 5 fallos, breaker (§3 (c)). Y en la traza de `copia_2026_0518.pdf` hay un
  `LLM-INVALID` real.
- **¿Y si hay otro proveedor?** → respaldo de texto `glm5.3-flash`, 3/3 con hechos idénticos (§3 (e)). De visión no:
  ninguno lee el NIF mejor (ADR-0004).
- **¿Y si cambia un dato después de entregar?** → `scripts/dato_en_vivo.py` (arriba): el cambio entra como un snapshot
  nuevo, el linaje dice qué decisiones dependían de él y sólo se recalculan ésas (ADR-0006). La entrega no se toca.
- **¿Y si el LLM se equivoca en vez de caerse?** → el LLM sólo rellena hechos. Decide la norma, y los validadores y
  el maestro contrastan: las 468 de plantilla, contrastadas 468/468; las escaneadas, leídas dos veces y reconciliadas
  con el maestro, y si no cuadra, se escala. La auditoría de entrega caza evidencias falsas: encontró el «None» de
  `scan_025` (AUDITORIA-ENTREGA.md).
- **¿Y el calendario de pagos?** → `uv run python -m albertitos.bonus --salida dist/bonus --tope-semanal 150000` (438 PAGAR, 2.428.159,06 EUR). Es un borrador; los IBAN de la Caja no tienen dígito de control.
- **¿Y si le pides al chat que pague?** → se niega en local (`estado: solo_lectura`, 0 ms, `sin_modelo`) y no llama al LLM.

## Grabar la demo en local (19/09, 21:45, probado 13/13 en Chromium)
La consola de Vercel sólo puede enseñar los datos de ejemplo: el puente, el chat y el LLM viven en el portátil.
Para grabar, todo en local. **En el portátil de Javier el 3000 es un Grafana de otro proyecto y el 8001 otro
contenedor**: la consola va en el **3002** y el chat en el **8101**.

1. Bandeja limpia con el contexto del lote 2 (copia aparte, nunca la BD de la entrega):
   ```bash
   mkdir -p dist/ensayo/aparte && mv dist/bandeja.db* dist/inbox dist/ensayo/aparte/ 2>/dev/null
   uv run python -c "from albertitos.console import bandeja; bandeja.preparar()"
   ALBERTITOS_DB=dist/bandeja.db uv run albertitos maestro --lote2 data/lote2
   ALBERTITOS_DB=dist/bandeja.db ALBERTITOS_ERP_URL=http://127.0.0.1:8011 uv run albertitos erp pull --tag v2
   ```
2. Tres terminales:
   ```bash
   ALBERTITOS_BANDEJA_NORMA=v4 ALBERTITOS_CONSOLA_ORIGENES=http://localhost:3002 uv run python -m albertitos.console.api --bandeja
   ALBERTITOS_CHAT_PUERTO=8101 ALBERTITOS_CHAT_HASTA=2026-09-20T01:00 ALBERTITOS_CHAT_ORIGENES=http://localhost:3002 make chat
   cd console-web && NEXT_PUBLIC_USE_MOCK=false NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 NEXT_PUBLIC_CHAT_URL=http://127.0.0.1:8101 npx pnpm build && npx pnpm start -p 3002
   ```
3. Abrir `http://localhost:3002`. Facturas del lote 2 que cuentan algo al soltarlas (medido en la bandeja con la v4):

| Fichero | Sale | Por qué |
|---|---|---|
| `factura_2923.pdf` · `e08_P012.pdf` | PAGAR | todo cuadra (la segunda, alemana: NIF-IVA e IBAN DE válidos) |
| `2026-08-22_P010.pdf` | NO_PAGAR | R5: el pedido PO-2026-0071 ya figura PAGADA en el ERP (AS-90001) |
| `FA-7532_informática.pdf` | ESCALAR | R1: IBAN distinto del maestro (la factura pide «tomen nueva cuenta») |
| `e02_P002.pdf` | ESCALAR | R7: factura en USD contra un pedido en EUR, sin tipo de cambio acordado |
| `e18_P001.pdf` | ESCALAR | R6: total corregido a mano (anotación a mano) |

La pregunta al chat de la prueba: «¿Por qué no se paga F26-2201_transportes.pdf?» → ESCALAR, 5,7 s, ficha de la BD debajo.
