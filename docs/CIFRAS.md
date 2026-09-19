# Cifras para la defensa · catálogo G2, al día el 20/09/2026 a las 01:15

Una cifra sólo se puede citar con su población, máquina, fecha y estado. Ésta es la tabla de referencia;
los documentos enlazados conservan los experimentos originales. «Vigente» no significa volver a medir hoy
un ensayo con llamadas al LLM. No se hicieron llamadas al LLM ni se modificaron BD/entrega reales en G2.
Las cifras del portátil de Javier no son las del de Alfonso; medir allí antes de la defensa.
**El lote 2 ya está recibido, decidido y publicado** (20/09 00:17, entrega `d2ade3f`): las filas de abajo
distinguen lote 1, lote 2 y total. Lo que sigue diciendo «lote 1» es de la Caja del viernes y no ha cambiado.

| Cifra | Qué mide / alcance | Fuente | Comando que la reproduce o consulta | Fecha de medida | Vigencia / límite |
|---|---|---|---|---|---|
| **540/540 extraídos y decididos** | Los dos lotes: 500 de la Caja + 40 del lote 2; hechos disponibles, no significa 100 % de exactitud | BD real; [CONTRASTE-TOTAL §1](agentes/CONTRASTE-TOTAL.md), [EXTRACCION](agentes/lote2/EXTRACCION.md) | C1 debajo | 20/09 00:17, Javier | Confirmado sólo lectura. 0 pendientes |
| 40/40 del lote 2: 23 plantilla, 17 LLM de texto | Extracción del lote sorpresa; ninguna escaneada, todas con capa de texto | [EXTRACCION §1](agentes/lote2/EXTRACCION.md) | C1 (cambiando `lote=1` por `lote=2`) | 19/09 23:30, agente B | Las 17 pasaron por `deepseek-v4-flash` con el prompt p-0.4; 0 pendientes |
| 468/468 coincidencias, 0 discrepancias y 0 fallos; 472 s, 717.188 tokens | Contraste de ocho campos plantilla↔LLM; no etiqueta humana | [CONTRASTE-TOTAL §1](agentes/CONTRASTE-TOTAL.md); ADR-0002 | C2; no se repitió la lectura en G2 | 18/09, C1, desde 23:24 | Evidencia histórica vigente para esas plantillas/hechos; no mide las escaneadas |
| 468/500 = 93,6 %; 6 plantillas | Cobertura determinista; 29 escaneadas y 3 textos sin plantilla completan 500 | [RESILIENCIA §2](agentes/RESILIENCIA-Y-COSTE.md), ADR-0002 | C1; `uv run pytest tests/test_plantillas.py -q` | 18/09; recuento G2 19/09 | Confirmado 468; caché puede cambiar el nombre del método de las otras 32 |
| **468 PAGAR / 62 ESCALAR / 10 NO_PAGAR** (540) | Decisiones vigentes de los dos lotes, tal como se entregaron | BD real; entrega `d2ade3f` ([entregas.log](entregas.log)) | C1; `uv run albertitos status` | 20/09 00:17, Javier | Referencia actual. **No es verdad etiquetada**: la validación oficial es binaria y no la conocemos |
| 445 PAGAR / 46 ESCALAR / 9 NO_PAGAR | Sólo lote 1, norma v3 y ERP v1 (cada lote en su contexto, ADR-0021) | entrega `d2ade3f`; ADR-0017 | C1 | 20/09 00:17 | Antes del ADR-0017 era 438/53/9 (entrega `232bb76`): 7 escaneadas legibles pasaron a PAGAR. Antes del ADR-0011, 443/48/9 |
| 23 PAGAR / 16 ESCALAR / 1 NO_PAGAR | Sólo lote 2, norma v4 y ERP v2 | entrega `d2ade3f`; ADR-0022 | C1 | 20/09 00:17 | 8 de los 16 escalados son las facturas en divisa: sin tabla de cambio no convertimos. Pendiente de mentores |
| 57,1 s; 38,6 s con índice | Camino determinista a 10.000 en Ryzen 9; suma por etapas, excluye render/LLM | [ESCALA-10K §2 y §5](agentes/ESCALA-10K.md) | `uv run python scripts/bench_escala.py --n 10000 --etiqueta cifras-10k --workers 1,8 --decide-variantes` | 19/09 00:51–01:10, D1 | Histórico: 57,1 sin índice; 38,6 suma con índice. Esquema actual ya trae el índice; no prometer 57 s actuales |
| 3 min 39 s; pico 653 MB | Banco sintético 10k completo, dos tandas de extract; LLM sustituido por hechos congelados | [ESCALA-10K §1–2](agentes/ESCALA-10K.md) | `/usr/bin/time -v uv run python scripts/bench_escala.py --n 10000 --etiqueta cifras-banco --workers 1,8` | 19/09 00:51, D1 | No es un lote de 10k leído por el LLM ni un test de precisión |
| 0,065 y 0,106 ficheros/s | Visión real de doble lectura, 4 y 8 hilos, tandas de 24, Ryzen 9 | [ESCALA-10K §4](agentes/ESCALA-10K.md) | `uv run python scripts/bench_escala.py --n 0 --etiqueta cifras-llm --llm-vision 24 --llm-texto 12 --workers-llm 4,8` | 19/09 ~01:00, D1 | Base de extrapolación vigente; comando llama al LLM, no ejecutado G2. Sustituye 0,22 de una lectura |
| 1,30 / 1,80 ficheros/s | Texto LLM, 4/8 hilos, tandas de 12 sin caché de gateway | [ESCALA-10K §4](agentes/ESCALA-10K.md) | Mismo comando cifras-llm | 19/09 ~01:00, D1 | Medido en Javier, no en Alfonso; no equivale a plantillas |
| 580 escaneadas en ~1,5–2,5 h; >97 % del tiempo | Proyección para 10k con mezcla de Caja y una key | [ESCALA-10K §7](agentes/ESCALA-10K.md) | C3: 580 dividido entre las tasas medidas; sumar demás etapas | 19/09, D1 | EXTRAPOLADO, no ejecutado a 10k con LLM. El rango publicado es aproximado, no recalculado como medida |
| 0 EUR marginal registrado | Modelos abiertos incluidos en la suscripción; no coste total del servicio | [RESILIENCIA §1](agentes/RESILIENCIA-Y-COSTE.md); `llm.PRECIOS_POR_MODELO` | C4; `uv run albertitos bench` incluye costes históricos antiguos | 18/09, B2; código revisado 19/09 G2 | No nueva verificación de facturación; no generalizar a frontier ni otras tarifas |
| 399 EUR/mes; 0,0399 EUR/factura a 10k/mes | Cuota Starter documentada y división exacta; plan la redondea a 0,04 | [RESILIENCIA §1](agentes/RESILIENCIA-Y-COSTE.md), [ESCALA-10K §8](agentes/ESCALA-10K.md) | `uv run python -c 'from decimal import Decimal; print(Decimal(399)/10000)'` | Tarifa consultada por B2 el 18/09 | Histórico; G2 no consultó al proveedor. Confirmar tarifa contratada antes de presentarla como actual |
| 40/500 en 0,78 s; 500/500 en 7,06 s | ERP con 25 pagos +15 importes cambiados; después reproceso total | [ENSAYO-REPROCESADO, Qué salió](agentes/ENSAYO-REPROCESADO.md) | C5; comandos literales en la fuente | 19/09 02:40 | Medida histórica de esa copia; segunda pasada granular da 0, no 40. No redondear 7,06 a otra medida |
| 2/500 en 0,04 s; CLI 0,51 s | Diff v1→v2-sim de dos asientos, otro experimento | [benchmark, Cifras](benchmark.md), ADR-0006 | `ALBERTITOS_DB=<copia con v1 vigente> uv run albertitos reprocess --impacted --erp v2-sim --fecha-corte 2026-09-18` | 19/09 00:14, Miguel | No atribuir 0,04 s a recalcular las 500; requiere estado inicial restaurado en copia |
| 204,0 s, 500, 2,5 ficheros/s; 15,0 s, 33,4 ficheros/s y 0 tokens con caché | Pipeline en i5-1235U / 7,7 GB / Windows 11 / 4 hilos | [benchmark, Condiciones y Cifras](benchmark.md) | `ALBERTITOS_DB=<BD nueva aparte> uv run albertitos run --salida <carpeta aparte> --fecha-corte 2026-09-18`; caliente requiere copiar sólo caché | 19/09 00:14, Miguel | Histórico de otra máquina; primera pasada puede haber usado caché del gateway; no reproducido hoy |
| 0,11 / 0,16 s a 500; 4,08 / 3,97 s a 10k | Reproceso total con índice, historiales de distinto tamaño | [benchmark, Cifras](benchmark.md) | `pipeline.run.reprocesar(todo=True)` en copias preparadas; preparación completa no preservada en un comando | 19/09 01:45–01:55, Miguel | Histórico; no reproducible exactamente hoy desde un único comando. No confundir con 7,06 s de otra copia/máquina |
| Plantilla p50 3 ms / p95 11 ms; texto p50 3,3 s; visión p50 17,3 s | Latencias por factura en el i5; visión posiblemente cacheada por gateway | [benchmark, Cifras y Salvedad](benchmark.md) | `ALBERTITOS_DB=<BD del banco de Miguel> uv run albertitos bench --desde <inicio>` | 19/09 00:14 | No reproducible aquí sin esa BD/inicio; 17,3 s no sirve para extrapolar visión fría |
| 21,9 s demo con red | Tres run y tres lecturas LLM en portátil de Miguel | [benchmark, Cifras](benchmark.md), ADR-0007 | `uv run python scripts/demo_caos.py` (llama al LLM) | 19/09, Miguel | Histórico distinto de demo sin red; no garantía de latencia |
| 4,7 s; repeticiones 4,1 y 3,8 s; ~4 s en chuleta | Demo sin red en clon limpio, Ryzen 9; cache reinsertada en recuperación | [ENSAYO-CLON-LIMPIO](demo/ENSAYO-CLON-LIMPIO.md), [KIT-DEFENSA](agentes/KIT-DEFENSA.md) | `uv run python scripts/demo_caos.py --sin-red` | 19/09 ~07:25, F2 | Vigente para ese ensayo; E1 obtuvo 3,6 s después. Los 39,5 s bajo carga son históricos; medir en Alfonso |
| 5 fallos → apertura 60 s; 5 LLM-DOWN +3 LLM-CIRCUIT-OPEN | Umbral/ventana predeterminados, ocho ficheros y un hilo | [RESILIENCIA §3 (b bis)](agentes/RESILIENCIA-Y-COSTE.md); `llm.EstadoLLM` | `uv run pytest tests/test_llm.py -q -k circuit`; bloque aislado de §3 (b bis) | 19/09, E1/F2 | Configurable por entorno; no demostrarlo con sólo tres facturas |
| 60 s texto / 90 s visión; 3 intentos principal +1 respaldo | Límites por modalidad e intentos; no tiempo total máximo del lote | [CONTRASTE-TOTAL §6](agentes/CONTRASTE-TOTAL.md), [RESILIENCIA §3 (e)](agentes/RESILIENCIA-Y-COSTE.md) | `uv run pytest tests/test_llm.py -q -k 'timeout or respaldo'`; C4 | 18–19/09 C1/E1 | Defaults; comprobar overrides. Respaldo texto opcional, visión sin modelo configurado por defecto |
| 5/5 recuperadas en intento 2; 32,6 s | Caos 429 simulado, no 429 real del gateway | [RESILIENCIA §3 (b)](agentes/RESILIENCIA-Y-COSTE.md) | Receta §3 (b), copia y fixture de cinco; llama al LLM | 18/09 B2 | Histórico, no repetido G2; no confundir con 429 real del ERP |
| Respaldo 3/3, hechos iguales; 68,7 s | Principal texto con 402, respaldo glm5.3-flash | [RESILIENCIA §3 (e)](agentes/RESILIENCIA-Y-COSTE.md) | Receta §3 (e) sobre copia y fixture; llama al LLM | 18/09 B2 | Disponibilidad, no demuestra mejor precisión de NIF |
| ERP v1: 516 asientos, 31 consultas, 3 reintentos ORA-00600, 35 ms HTTP | Snapshot descargado 18/09 19:55:36 UTC =21:55 Madrid; ids 3213–3243 | BD real; `sources.snapshot.resumen_erp` | C6 | Descarga 18/09; consulta G2 19/09 | Asociación histórica inferida; latencia excluye backoff y ritmo. No usar 122 eventos/11 retries históricos como si fueran de v1 |
| Maestro del lote 2: 15 proveedores, 555 pedidos (`f504377103b2`) | Excel + `proveedores_nuevos.csv` + `pedidos_nuevos.csv`; el Excel solo da `80911e429c6c` | `sources/lote2.py`; [EXTRACCION](agentes/lote2/EXTRACCION.md) | `uv run albertitos maestro --lote2 data/lote2` | 19/09 20:45, Javier | Los IBAN de P013, P014 y P015 no pasan el control (el japonés no es un IBAN): quedan como avisos de calidad |
| ERP v2: 556 asientos, 33 consultas, 3 reintentos, 4,3 s | Descarga completa tras cargar el lote 2 en el bridge; 40 asientos nuevos, 0 cambiados | BD real; `sources.snapshot.diff_erp` | `python3 data/caja/alberto_erp.py --puerto 8011 --lote2 data/lote2/erp_export_lote2.csv` y `erp pull --tag v2` | 19/09 20:40, Javier | `AS-90001` es un asiento **nuevo** que deja PO-2026-0071 PAGADA; por eso `2026-08-22_P010` es NO_PAGAR |
| Un dato de la Caja cambiado: 50 de 500 recalculadas, 43 cambian, 1,4 s | IBAN de P006 cambiado en una copia del Excel; linaje granular | [KIT-DEFENSA](agentes/KIT-DEFENSA.md) | `bash scripts/ensayo/dato-cambiado.sh` | 19/09 20:26, Javier | Sobre una copia; la BD real y la entrega no cambian. Con un importe de pedido, 1 de 500 |
| Demo pública: 12/12 comprobaciones, chat en 5,7 s | Vercel contra Render, Chromium limpio y sin permisos especiales | ADR-0023; `deploy/README.md` | `bash scripts/demo.sh estado` | 20/09 00:50, Javier | Plan gratuito: si duerme, el primer acceso tarda ~50 s. El workflow la despierta cada 10 min |
| ERP inaccesible: 8 consultas, 7 reintentos, 5,619 s | Puerto local reservado sin escucha; política por defecto | `tests/test_erp.py::test_conexion_rechazada_se_registra_y_agota`; log `dist/ensayo/g2/sin-erp.log` | `uv run pytest tests/test_erp.py -q -k conexion_rechazada` usa 2 intentos, <2 s; C7 mide defaults | 19/09 G2 | Medido sin alterar bridge; latencia no instantánea. CLI requiere captura de ErrorERP por Miguel |

## Comandos de comprobación

Ejecutar desde la raíz en Bash/WSL. Los comandos C1, C3, C4 y C6 son sólo lectura/cálculo.
Los bancos, demo y C2/C5 escriben exclusivamente copias o sus carpetas de ensayo; nunca sustituir
esas rutas por la BD o entrega real. G2 no volvió a medir llamadas al LLM ni los bancos de 10k.

**C1 — hechos y decisiones actuales, sin red ni escrituras:**
```bash
uv run python - <<'PY'
import sqlite3
from contextlib import closing
with closing(sqlite3.connect('file:dist/albertitos.db?mode=ro', uri=True)) as c:
    for sql in (
        'SELECT lote,count(*) FROM ficheros GROUP BY lote',
        'SELECT f.lote,h.metodo,count(*) FROM hechos h JOIN ficheros f USING(sha256) GROUP BY f.lote,h.metodo',
        'SELECT d.resultado,count(*) FROM decisiones d WHERE d.vigente=1 GROUP BY d.resultado',
        'SELECT f.lote,d.norma_version,d.erp_version,d.resultado,count(*) FROM decisiones d JOIN ficheros f USING(sha256) WHERE d.vigente=1 GROUP BY f.lote,d.norma_version,d.erp_version,d.resultado',
    ): print(c.execute(sql).fetchall())
PY
```

**C2 — contraste histórico:** la fuente conserva resultado, campos y comando API
`etapa.contrastar(conn, file_ids=<468 plantillas>, workers=4)`. No hay informe independiente versionado
con las 468 comparaciones: repetir requiere preparar una copia SQLite y esa lista, y puede llamar al LLM
si falta caché. No se presenta como reproducido hoy ni basta con contar 468 entradas de caché para
demostrar que coinciden. Ver CONTRASTE-TOTAL §1 y ADR-0002.

**C3 — proyección, no medida:**
```bash
uv run python -c 'from decimal import Decimal as D; print("horas visión 580:", D(580)/D("0.106")/3600, D(580)/D("0.065")/3600)'
```

**C4 — precios y límites del código, no factura del proveedor:**
```bash
uv run python -c 'from albertitos.extract.llm import PRECIOS_POR_MODELO,TIMEOUT_S,TIMEOUT_VISION_S; print(PRECIOS_POR_MODELO); print(TIMEOUT_S,TIMEOUT_VISION_S)'
```

**C5 — linaje histórico:** el comando original es
`ALBERTITOS_DB=dist/ensayo-linaje.db uv run albertitos reprocess --impacted --erp v2-ensayo --fecha-corte 2026-09-18`;
después `--todo` en lugar de `--impacted`. Esa copia ya está reprocesada: volver a ejecutar no reproduce
40 cambios. No hay script versionado que reconstruya los 25+15 asientos elegidos; la cifra es evidencia
histórica de ENSAYO-REPROCESADO, no reproducida hoy. Para repetir hay que reconstruir ese estado en otra copia.

**C6 — resumen exacto del snapshot y atribución de sus eventos:**
```bash
uv run python - <<'PY'
import json, sqlite3
from contextlib import closing
from albertitos.sources.snapshot import resumen_erp
with closing(sqlite3.connect('file:dist/albertitos.db?mode=ro', uri=True)) as c:
    print(json.dumps(resumen_erp(c, 'v1'), ensure_ascii=False, indent=2))
PY
```
`atribucion=explicita` en descargas nuevas; `inferida_por_ventana` en el histórico compatible.
Si no hay vínculo ni ventana verificable, errores/latencia salen `null`: desconocidos, no cero.
`uv run albertitos status` y `uv run albertitos bench` enseñan reintentos acumulados; no adjudicarlos todos a una factura.

**C7 — fallo real de conexión sin tocar BD ni el bridge:**
```bash
uv run python - <<'PY'
import socket,time
from albertitos.sources.erp import ClienteERP,ErrorERP
with socket.socket() as reserva:
    reserva.bind(('127.0.0.1',0))
    inicio=time.perf_counter()
    with ClienteERP(f'http://127.0.0.1:{reserva.getsockname()[1]}') as cliente:
        try: cliente.descargar_todo('prueba-sin-erp')
        except ErrorERP as exc: print(str(exc)); print(time.perf_counter()-inicio)
PY
```

## Formas obsoletas vigiladas

`uv run python scripts/cifras_check.py` lee el bloque de datos siguiente y comprueba plan, guion,
KIT-DEFENSA y benchmark. Sale 1 si encuentra una forma, 0 si no y 2 si no pudo leer/validar todo.
Una mención histórica se señala hasta que alguien la revisa y la declara en `historicas` (fichero + un trozo literal
de la línea): si la frase se reescribe, vuelve a saltar. El comprobador no decide solo si un párrafo es falso. No cambia archivos ni presupone que siga mal el plan de Alfonso: Miguel ya corrigió su visión.

<!-- cifras-obsoletas
[
  {"formas": ["0,22 ficheros/s", "0,22 f/s"], "vigente": "0,065 ficheros/s (4 hilos) / 0,106 (8), visión con doble lectura", "fuente": "docs/agentes/ESCALA-10K.md §4; docs/CIFRAS.md",
   "historicas": [{"fichero": "docs/benchmark.md", "contiene": "La cifra que usábamos antes, 0,22 ficheros/s con 4 hilos"}]},
  {"formas": ["10.000 en ~45 min", "salen en ~45 min"], "vigente": "10.000: estimación 1,5–2,5 h con una key y mezcla de Caja", "fuente": "docs/agentes/ESCALA-10K.md §7; docs/CIFRAS.md"},
  {"formas": ["reprocesar 500 decisiones, 0,04 s"], "vigente": "2 de 500 en 0,04 s; total 500 depende del banco (7,06 s en ensayo de Javier)", "fuente": "docs/benchmark.md, Cifras; docs/agentes/ENSAYO-REPROCESADO.md, Qué salió"},
  {"formas": ["438/53/9", "438 PAGAR"], "vigente": "entrega d2ade3f (20/09 00:17): 540 = 468 PAGAR / 62 ESCALAR / 10 NO_PAGAR; lote 1 445/46/9 y lote 2 23/16/1", "fuente": "docs/CIFRAS.md; docs/entregas.log",
   "historicas": [{"fichero": "docs/agentes/KIT-DEFENSA.md", "contiene": "**438 PAGAR · 53 ESCALAR · 9 NO_PAGAR** y caché 881"}]},
  {"formas": ["500 líneas", "las 500 facturas", "500 outcomes"], "vigente": "540 facturas entregadas: outcomes.jsonl 500 + outcomes_lote2.jsonl 40", "fuente": "docs/CIFRAS.md; docs/entregas.log"}
]
-->
