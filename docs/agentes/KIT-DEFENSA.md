# Chuleta de la defensa · bloque 4 (resiliencia, 2 min) · para Alfonso

Tiempos medidos por F2 el 19/09 a las 07:25 en un clon limpio del repo (`docs/demo/ENSAYO-CLON-LIMPIO.md`), en el
portátil de Javier. **En el tuyo serán otros: cronométralos en el ensayo de las 15:00.** Todo es bash (WSL, Linux o Mac).

## Antes de salir de casa (con red)
1. `git pull --ff-only && ./bootstrap.sh`. La primera vez descarga dependencias: necesita red. Hazlo **después del merge
   de `miguel/pipeline`**: trae el `trace` legible y el `status` nuevo. El kit de las 10:07 sirve igual.
2. Copia el kit que te pase Javier a `dist/kit/` e instálalo: `make kit-instalar KIT=dist/kit/albertitos-kit-<fecha>.tar.gz`.
   Tiene que acabar en `VEREDICTO: instalado` con `ficheros {'1': 500}`, **438 PAGAR · 53 ESCALAR · 9 NO_PAGAR** y caché 881 (kit de las 10:07, con las decisiones de Mónica; el de las 09:02 decía 443/48/9).
   Si te pide `--forzar`, es que ya tenías una BD con datos: añade `ARGS=--forzar` (la anterior queda en `…antes-del-kit`).
3. `uv run albertitos status` (los mismos recuentos) y `make console` una vez: tres pestañas, Panel con 500/438/53/9.
4. Ensaya el bloque entero con cronómetro. El ERP no hace falta para nada de esto.

## En la sala, en orden
| # | Comando | Qué se ve (una línea) | Tarda | Qué dices |
|---|---|---|---|---|
| 1 | `uv run python scripts/demo_caos.py --sin-red` | paso 1: `run → exit 1 · entrega escrita: no` y las 3 facturas `extract pendiente (LLM-DOWN) → decide skip → emit pendiente · decisión: NINGUNA` | todo, ~4 s | «Se cae el proveedor: tres facturas quedan pendientes, ninguna se paga a ciegas y la entrega se niega a salir incompleta.» |
| | (mismo comando) | paso 2: `run → exit 0 · outcomes.jsonl 5ec17aaa5045` (el mismo hash que imprimió `kit-instalar`) | | **«La vuelta la sirvo desde la caché para no depender del wifi.»** Prueba que el pipeline reanuda, no que el proveedor conteste |
| | (mismo comando) | paso 3: `(igual: True)` | | «Repetir no llama a nadie ni duplica nada: la identidad es el sha256. Y es el mismo hash que la entrega oficial.» |
| 2 | los 5 comandos de RESILIENCIA §3 (b bis), tal cual, con `chaos --llm-down` antes del `extract` | `{'LLM-DOWN': 5, 'LLM-CIRCUIT-OPEN': 3}` | ~2 s el bloque | «A partir del quinto fallo dejamos de castigar al proveedor. Lo pendiente sigue pendiente.» |
| 3 | consola → Traza → `copia_2026_0518.pdf` | eventos `LLM-DOWN` y `LLM-INVALID` del viernes y, después, la extracción buena | — | «Esto no es un ensayo: pasó el viernes con esta factura, y se reanudó sin tocar nada.» |

`status` enseña el último evento de cada fichero: el `extract pendiente 7` y los `2.3823 EUR` del viernes ya no salen
(sólo con `status --historico`). Si salen ahí o en el Panel de la consola: «son eventos del viernes; los 7 pendientes
son pruebas de caos de ficheros que luego se extrajeron bien (0 sin decisión), y los 2,38 € son una tarifa inventada
que corregimos: los modelos que usamos no cobran por token».

## Si algo falla
- **La demo no arranca:** enseña `docs/demo/transcripcion-demo-caos.txt` (la misma demo con red, 104 s, tokens incluidos).
- **La consola no abre:** `uv run albertitos status` y `uv run albertitos trace F26-2201_transportes.pdf` en la terminal.
  `trace` sale legible, un paso por bloque (hechos → maestro → ERP → duplicado → reglas → resultado) y con la vigente
  primero en el historial; `docs/demo/trazas/README.md` dice qué mirar.
- **No hay ERP en la sala:** da igual para la demo (se comprobó apagándolo). Sólo fallan `erp pull` y el preflight.

## Qué pregunta responde cada cosa
- **Caída** → paso 1: PENDIENTE, `package` se niega, nada se paga sin hechos.
- **Timeout** → mismo camino: 3 intentos y PENDIENTE. Límites de 60 s (texto) y 90 s (visión). Ensayado con
  `llm_timeout` en CONTRASTE-TOTAL §7 (3 facturas → `LLM-TIMEOUT` ×3 → 0 hechos, 0 decisiones). No está en la CLI.
- **Rate limit** → respetamos `Retry-After`: 429 simulado, 5/5 recuperadas en el 2.º intento (RESILIENCIA §3 (b), con red).
- **Respuesta inválida** → reintento y, tras 5 fallos, breaker (§3 (c)). Y en la traza de `copia_2026_0518.pdf` hay un
  `LLM-INVALID` real.
- **¿Y si hay otro proveedor?** → respaldo de texto `glm5.3-flash`, 3/3 con hechos idénticos (§3 (e)). De visión no:
  ninguno lee el NIF mejor (ADR-0004).
- **¿Y si el LLM se equivoca en vez de caerse?** → el LLM sólo rellena hechos. Decide la norma, y los validadores y
  el maestro contrastan: las 468 de plantilla, contrastadas 468/468; las escaneadas, leídas dos veces y reconciliadas
  con el maestro, y si no cuadra, se escala. La auditoría de entrega caza evidencias falsas: encontró el «None» de
  `scan_025` (AUDITORIA-ENTREGA.md).
