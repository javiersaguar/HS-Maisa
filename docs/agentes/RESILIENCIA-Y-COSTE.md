# Resiliencia y coste · evidencia medida

> Ciclo 2, agente B2 · viernes 18/09/2026, 22:45-01:30 · rama `javier/ingesta`
> Hardware de todas las medidas: **AMD Ryzen 9 8940HX, 24 CPUs, 43 GB RAM, WSL2 sobre Windows**.
> Proveedor: **Helmcode** (`https://api.helmcode.com/v1`, `openai_compat`), modelos `deepseek-v4-flash`
> (texto) y `qwen3.6` (visión). Lote: la Caja de 500 facturas. Todo lo que hay aquí sale de una
> ejecución real o de la tabla `eventos`. Lo que no está medido se dice que no lo está.
>
> Para Alfonso (plan, 35 pts) y Miguel (`docs/benchmark.md`). Rúbrica: **resiliencia 10 · escala y coste 25**.

---

## 1. El coste por token que veníamos contando no existe

`uv run albertitos bench` decía **2,30 EUR** por procesar la Caja. Esa cifra sale de
`ALBERTITOS_PRECIO_IN/OUT_EUR_MTOK = 3/15`, dos números que nadie había comprobado.

**Helmcode no cobra por token los modelos que usamos.** Cobra una **suscripción plana por API key**
(`helmcode.com/pricing`, consultado el 18/09/2026: Starter 399 €/mes · Growth 1.299 € · Scale 3.199 €).
Su catálogo separa dos familias (`helmcode.com/docs/models`):

| Familia | Modelos | Cómo se paga |
|---|---|---|
| **Abiertos** | `deepseek-v4-flash`, `qwen3.6`, `glm5.3-flash`, `gemma4` | incluidos en la suscripción, **sin coste por token** |
| **Frontier** | `claude-*`, `gpt-5.6-*`, `gemini-*` | crédito prepago por token |

Y nuestra organización **no tiene crédito prepago**. Probados los 8 frontier del gateway, los 8
devuelven `402` con este texto literal:

```
{"error":{"message":"gpt-5.6-sol is a third-party model billed per token from prepaid credit.
Your organisation has no credit balance …"}}
```

**Conclusión: el coste marginal de procesar una factura más es 0 EUR.** No "casi 0": cero. El
código ya lo refleja (`PRECIOS_POR_MODELO` en `extract/llm.py`, los abiertos a 0, sobrescribible con
`ALBERTITOS_PRECIOS_JSON`). Una ejecución completa de la Caja hoy imprime `0.0000 EUR`.

### Lo que sí cuesta dinero

Si hay que dar una cifra en euros, la honesta es la **suscripción amortizada**, y depende del volumen:

| Facturas/mes | Coste/factura (Starter, 399 €/mes) |
|---:|---:|
| 500 | 0,80 € |
| 10.000 | 0,040 € |
| 100.000 | 0,004 € |

El plan Starter incluye 5B tokens/mes de cuota mensual para los modelos abiertos. Con **8,9 K tokens
por factura escaneada** (medido, ver §2), 5B tokens dan para ~560.000 facturas escaneadas al mes: la
cuota **no** es la restricción. La restricción es el límite de tasa (§4).

> **Para Miguel:** al rehacer `bench`, el EUR de los modelos abiertos es 0. Si el tribunal pide un
> número de dinero, es la tabla de arriba, diciendo el plan y la fecha.

---

## 2. Coste y tamaño por camino (medido sobre las 500)

De las 500 facturas de la Caja: **468 por plantilla · 29 por visión · 3 por LLM de texto.**
Cifras de la tabla `eventos` (`estado='ok'`, excluidos los eventos de importación):

| Camino | n | tok entrada/factura | tok salida/factura | latencia media | EUR/factura |
|---|---:|---:|---:|---:|---:|
| **Plantilla** (A2) | 468 | 0 | 0 | **5 ms** | 0 |
| **LLM texto** (`deepseek-v4-flash`) | 3 | 1.123 | 665 | 3,3 s | 0 |
| **LLM visión** (`qwen3.6`, doble lectura) | 29 | 5.476 | 3.450 | 35,3 s | 0 |

Dos lecturas de esto:

1. **Las plantillas son la palanca real.** 93,6 % de la Caja no toca el LLM y tarda 5 ms. Si el
   proveedor cae, esas 468 salen igual (demostrado en §3a). `p_llm` no es un parámetro de coste
   aquí — es un parámetro de **exposición al fallo**.
2. **La visión es 7.000 veces más lenta que una plantilla** y consume 8,9 K tokens por factura. Es
   donde está todo el riesgo de tiempo y de calidad.

---

## 3. Guion de resiliencia · 2 minutos, ensayado

Ejecutado el 18/09 sobre **5 facturas que no estaban en caché** (las 3 de texto sin plantilla y 2
escaneadas), contra una **copia** de la BD (`ALBERTITOS_DB=…/demo.db`) para no tocar el estado real.
Salidas **literales**.

```bash
# preparación: copia de la BD y 5 ficheros sin caché
export ALBERTITOS_DB=/tmp/demo.db
```

### (a) El proveedor se cae — 0,9 s

```
$ uv run albertitos chaos --llm-down
modo caos: llm_down
$ uv run albertitos extract --no-solo-pendientes --fixture demo.txt --workers 4
extract: 0/5 ok · 5 pendientes · 0 pdf ilegibles · métodos {} · errores
{'LLM-DOWN': 5} · tokens 0/0 · 0.0000 EUR · 0.7 s (7.62 ficheros/s)
```

Los 5 quedan `PENDIENTE` con `error_codigo=LLM-DOWN`, **0 hechos escritos**, nada decidido. Lo que
hay que decir en la defensa: *sin hechos validados no hay decisión, y sin decisión no hay PAGAR.*
La degradación no es "seguir con datos peores": es **no decidir**.

### (b) Rate limit 429 — 32,6 s, se recupera solo

```
$ uv run albertitos chaos --llm-429
$ uv run albertitos extract --no-solo-pendientes --fixture demo.txt --workers 4
extract: 5/5 ok · 0 pendientes · métodos {'llm_texto': 3, 'llm_vision': 2} ·
errores {} · tokens 15234/8179 · 0.0000 EUR · 32.6 s
```

Los 5 salen en **`intento=2`**, visible en `eventos`:

```
('scan_028.pdf', 'ok', 2, 29094, "llm_vision avisos=['sin_texto'] modelo=qwen3.6")
('2026-03-19_P008.pdf', 'ok', 2, 3782, "llm_texto avisos=['campo_ausente'] modelo=deepseek-v4-flash")
```

**Mejora de este ciclo:** el gateway manda `Retry-After` en el 429 y `llm.py` lo tiraba, esperando a
ciegas 1/2/4 s. Ahora se respeta lo que pide el proveedor (tope de 60 s para no colgar el lote).

### (b bis) Con el proveedor caído, el breaker también salta — 0,8 s  *(corregido por E1, 19/09)*

Hasta este ciclo, `llm_down` lanzaba el error **antes** de contar el fallo: el contador no subía y con
una caída el breaker no se abría nunca, aunque el guion lo prometiera. Ya cuenta igual que un fallo real.
Comando reproducible, sobre una BD de ensayo (nunca la real) y sin salir a la red:

```bash
export ALBERTITOS_DB=dist/ensayo/breaker.db ALBERTITOS_CHAOS=dist/ensayo/breaker.chaos.json
uv run albertitos db init && uv run albertitos ingest --dir data/caja/facturas
ls data/caja/facturas/scan_0*.pdf | head -8 | xargs -n1 basename > dist/ensayo/ocho_escaneadas.txt
uv run albertitos chaos --llm-down
uv run albertitos extract --fixture dist/ensayo/ocho_escaneadas.txt --workers 1
```

```
extract: 0/8 ok · 8 pendientes · 0 pdf ilegibles · métodos {} · errores
{'LLM-DOWN': 5, 'LLM-CIRCUIT-OPEN': 3} · tokens 0/0 · 0.0000 EUR · 0.5 s (16.21 ficheros/s)

  scan_001.pdf   pendiente  LLM-DOWN           LLM-DOWN: caos: proveedor caído
  …
  scan_006.pdf   pendiente  LLM-CIRCUIT-OPEN   LLM-CIRCUIT-OPEN: 5 fallos seguidos; reabre en 60s
  scan_007.pdf   pendiente  LLM-CIRCUIT-OPEN   LLM-CIRCUIT-OPEN: 5 fallos seguidos; reabre en 60s
  scan_008.pdf   pendiente  LLM-CIRCUIT-OPEN   LLM-CIRCUIT-OPEN: 5 fallos seguidos; reabre en 60s
```

Lo que se enseña: **a partir del quinto fallo dejamos de castigar al proveedor**, y lo pendiente sigue
pendiente (nada se paga a ciegas). Con hilos también corta: el breaker se comprueba antes de cada
intento, no sólo al empezar cada fichero.

`make demo-caos` usa 3 facturas y 3 hilos, así que ahí el breaker **no** llega a verse con el umbral de
5: los tres entran antes de que ninguno falle. Para enseñarlo en esa demo, `ALBERTITOS_BREAKER_FALLOS=2`.

### (c) El modelo devuelve basura — 23,2 s, y salta el circuit breaker

```
$ uv run albertitos chaos --llm-invalid
extract: 0/5 ok · 5 pendientes · errores {'LLM-INVALID': 4, 'LLM-CIRCUIT-OPEN': 1} · 23.2 s
```

Los 4 primeros agotan 3 intentos cada uno; al quinto fallo seguido **el circuit breaker se abre** y
el último fichero ni siquiera sale a la red (`LLM-CIRCUIT-OPEN`), reabriendo a los 60 s. Es la
diferencia entre fallar 5 veces y fallar 500: con la Caja entera, el breaker corta a los 5.

### (d) Vuelve el proveedor — 30 s, y la segunda pasada es gratis

```
$ uv run albertitos chaos --off
$ uv run albertitos extract --fixture demo.txt --workers 4     # sólo pendientes
extract: 5/5 ok · 0 pendientes · métodos {'llm_texto': 3, 'llm_vision': 2} · tokens 15114/8560 · 30.0 s
$ uv run albertitos extract --no-solo-pendientes --fixture demo.txt --workers 4
extract: 5/5 ok · métodos {'cache': 5} · tokens 0/0 · 0.0000 EUR · 1.1 s
```

Y **sin duplicados**, que es lo que de verdad se comprueba:

```
sha256 con más de un hecho: 0
total hechos: 510 · ficheros: 510
```

La reanudación es por `sha256`, no por nombre: reprocesar es idempotente y gratis.

### (e) Modelo de respaldo — probado contra el gateway real

Con el principal puesto a un modelo que **no podemos pagar** (`claude-sonnet-5` → 402):

```
$ ALBERTITOS_MODELO_TEXTO=claude-sonnet-5 ALBERTITOS_MODELO_TEXTO_FALLBACK=glm5.3-flash \
    uv run albertitos extract --no-solo-pendientes --fixture demo_texto.txt
claude-sonnet-5 agotó reintentos (LLM-HTTP-402); pruebo el respaldo glm5.3-flash
extract: 3/3 ok · 0 pendientes · métodos {'llm_texto': 3} · tokens 2892/1620 · 0.0000 EUR · 68.7 s
```

El evento dice quién respondió, que es lo que la traza necesita:

```
FA-2967_seguridad.pdf | ok | modelo=glm5.3-flash respaldo=si
```

Y los hechos son **idénticos campo a campo** a los del modelo principal en las 3 facturas
(`num_factura`, `fecha`, `nif_emisor`, `iban`, `pedido`, `base`, `iva`, `total`).

Detalles de diseño, por si preguntan:
- El respaldo se intenta **una sola vez** (3 intentos del principal + 1 del respaldo, no 3+3).
- **No** se intenta si el fallo es `LLM-AUTH`, `LLM-CONFIG` o `LLM-PRESUPUESTO`: con la key mala o el
  presupuesto agotado, el respaldo del mismo gateway tampoco va a funcionar.
- Cachea con **clave propia por modelo**: la lectura del respaldo no se hace pasar por la del principal.
- Si no se configura respaldo, la degradación sigue siendo `PENDIENTE`. Es lo que hay por defecto.
- **Arreglado por E1 (19/09 02:45):** la llamada al respaldo pasaba por la comprobación del circuit
  breaker, así que en cuanto el principal agotaba sus 3 intentos el breaker se abría por esos mismos
  fallos y el respaldo **moría ahí**: no se usaba nunca, justo en el escenario para el que existe.
  Ahora esa llamada se salta el breaker (el breaker protege al proveedor que falla, no al alternativo);
  los fallos del respaldo sí siguen contando. Test: `test_el_respaldo_se_intenta_aunque_el_breaker_este_abierto`.

---

### (f) La demo entera de una tacada, y por qué en la sala va **sin red** *(medido por E1, 19/09 03:10)*

`make demo-caos` cuenta la historia completa sobre una copia de la BD (`dist/demo.db`, entrega aparte en
`dist/demo_entrega/`): 3 facturas que ninguna plantilla reconoce "llegan nuevas", el proveedor está caído,
quedan PENDIENTE, `package` se niega a entregar; vuelve el proveedor, se reanudan; y una tercera pasada no
llama a nadie. Termina comparando su JSONL con el oficial: **0 resultados distintos**.

Dos ejecuciones seguidas, mismo comando, misma máquina:

| Paso | 1.ª vez | 2.ª vez |
|---|---|---|
| 1. Proveedor caído → 3 PENDIENTE, `run` sale 1, no escribe entrega | 9,2 s | 9,2 s |
| 2. Vuelve el proveedor → 3 lecturas reales | **12,9 s** | **74,7 s** |
| 3. Idempotente (caché por sha256) | 10,4 s | 10,3 s |
| **Total** | **42,5 s** | **104,0 s** |

Los pasos 1 y 3 no tocan la red y son estables al décimo de segundo. El paso 2 son 3 llamadas al gateway y
**osciló 6×** entre dos ejecuciones separadas por veinte minutos. En un bloque de 4 minutos que además hay
que narrar, eso es demasiado margen para jugárselo.

Por eso la demo de la defensa se hace con `--sin-red`:

```
uv run python scripts/demo_caos.py --sin-red     # 39,5 s, sin una sola llamada al proveedor
```

Guarda las 3 lecturas de la caché antes de borrarlas y las devuelve entre el paso 1 y el 2, así que la
reanudación se sirve de la caché. El JSONL final sale con el mismo sha256 que el oficial (`5ec17aaa5045`).
**Se dice en voz alta**: prueba que el pipeline reanuda y que la entrega sale idéntica, no que el proveedor
conteste. Lo que de verdad puntúa —que con el LLM caído nada se paga a ciegas y `package` se niega— es el
paso 1, y ese es offline de todas formas.

Si el wifi de la sala va bien, el mismo comando sin la bandera hace las 3 lecturas de verdad. Y si falla
hasta el portátil, `docs/demo/transcripcion-demo-caos.txt` es la ejecución literal con red, tokens incluidos.

**Lo que hay que preparar antes**: la demo necesita `dist/albertitos.db` con las 500 ingeridas y su caché,
y esa BD está gitignorada: sólo vive en el portátil donde se corrió el pipeline. Si presenta Alfonso desde
el suyo, hay que copiársela (7,7 MB) **antes** del ensayo de las 15:00, no en la sala.

## 4. Capacidad medida: 1, 2, 4 y 8 hilos

`uv run python scripts/bench_llm.py --texto 16 --vision 8 --workers 1,2,4,8 --sufijo m2`
(16 facturas de texto y 8 escaneadas por tanda, **llamadas reales**, caché aparte por tanda).

| Camino | hilos | ficheros/s | p50 | p95 | 429 observados |
|---|---:|---:|---:|---:|---:|
| texto | 1 | 0,41 | 2,4 s | 4,7 s | 0 |
| texto | 2 | 0,76 | 2,5 s | 4,6 s | 0 |
| texto | **4** | **1,28** | 2,7 s | 4,6 s | 0 |
| texto | 8 | 0,17 ⚠ | 2,9 s | **94,0 s** | 0 |
| visión | 1 | 0,08 | 13,0 s | 24,8 s | 0 |
| visión | 2 | 0,13 | 13,0 s | 25,8 s | 0 |
| visión | **4** | **0,22** | 10,7 s | 35,8 s | 0 |
| visión | 8 | 0,22 | 14,5 s | 35,8 s | 0 |

**Qué dice esto:**

> **Corrección (E1, 19/09 02:10).** Las cifras de visión de esta sección miden **una sola lectura** por
> escaneada. El pipeline hace **dos** (la segunda sobre el recorte superior, para reconciliar identificadores):
> la visión real va a **0,065 f/s con 4 hilos y 0,106 con 8**, medido por D1 sobre 24 escaneadas
> (`ESCALA-10K.md` §4). Con eso, «10.000 facturas en ~45 min» es optimista entre 2 y 3 veces: la estimación
> buena es **1,5–2,5 h con una clave**. El resto de la sección (latencias, 429, saturación) sigue valiendo.

- **Visión satura en 4 hilos.** De 4 a 8 no gana nada (0,22 → 0,22 f/s). Encaja con el límite
  publicado: **5 peticiones concurrentes por modelo** para `qwen3.6`. Poner 8 hilos en visión no
  acelera; sólo llena la cola.
- **Texto escala bien hasta 4** (0,41 → 0,76 → 1,28 f/s, casi lineal). `deepseek-v4-flash` tiene
  concurrencia 10, así que el techo está más arriba, pero…
- **…el cuello de botella real no es el límite de tasa, es la cola de latencia.** En 0 de las 8
  tandas hubo un solo 429. Lo que rompe la tanda de 8 hilos en texto es **una petición que se queda
  colgada 94 s** mientras el p50 sigue en 2,9 s. Apareció dos veces, las dos clavada en ~94 s: huele
  a un timeout del lado del servidor.
- **Recomendación: `--workers 4`.** Es lo que ya usaba A1, y ahora está medido en vez de supuesto.

### Capacidad en facturas/hora (extrapolada de lo medido, a 4 hilos)

| Camino | ficheros/s | facturas/hora |
|---|---:|---:|
| Plantilla | 200 (5 ms) | ~720.000 |
| LLM texto | 1,28 | ~4.600 |
| LLM visión | 0,22 | ~790 |

Con la mezcla real de la Caja (93,6 % plantilla · 5,8 % visión · 0,6 % texto), **10.000 facturas
salen en ~45 min**, y de esos 45 minutos **~37 son las 580 escaneadas**. Todo lo demás es ruido.

### Qué haría falta para 10×

| Palanca | Efecto | Coste |
|---|---|---|
| **Más plantillas** | cada factura que sale de visión son 35 s que desaparecen | trabajo de A2, 0 € |
| Más keys de Helmcode | los límites se multiplican por asiento | 399 €/mes por tramo |
| Más hilos | **nada** en visión (saturado en 4) | 0 |
| Modelo de visión más rápido | `deepseek-v4-flash` leyó imágenes en 3-6 s frente a 12-35 s de qwen | 0 €, pero ver §5 |

La conclusión defendible: **para escalar 10× no hace falta pagar más LLM, hace falta que menos
facturas lleguen al LLM.** Es exactamente lo que hacen las 6 plantillas de A2.

---

## 5. Hallazgos sobre los modelos (medidos, no leídos en la doc)

**La documentación del gateway se equivoca sobre la visión, para bien.** `docs/models` dice que
`deepseek-v4-flash` y `glm5.3-flash` **no** aceptan imágenes. Sí las aceptan y devuelven tool call.
Comprobado con tres facturas distintas: aciertan el `pedido` y el `total` **de cada una**, así que
están leyendo la imagen, no adivinando.

**Pero ningún modelo lee el NIF de forma fiable.** Sobre escaneadas con verdad conocida:

| Factura | verdad (NIF) | qwen3.6 | deepseek-v4-flash | glm5.3-flash |
|---|---|---|---|---|
| `scan_001` | `B98120774` | `B88120774` ✗ | `B98120774` ✓ | `B98120774` ✓ |
| `scan_002` | `B98120774` | `B88125774` ✗ | `89812077W` ✗ | (HTTP 524) |
| `scan_004` | `B90233808` | `B60233808` ✗ | `B90233805` ✗ | `B00233858` ✗ |

El `pedido` y el `total` salen casi siempre bien; **el NIF casi nunca**. Son dígitos sueltos en una
imagen ruidosa, y cambiar de modelo no lo arregla.

**Esto valida la reconciliación con el maestro que montó A1 en el ciclo 1**, y conviene decirlo así en la
defensa: no confiamos en la lectura del NIF de ninguna IA; la contrastamos con el maestro de
proveedores y, si no hay evidencia, **escala**. Un modelo de respaldo compra **disponibilidad**, no
precisión.

`gemma4` queda descartado: acierta menos y tarda **75 s** en texto y 47 s en imagen.

---

## 6. Si Alberto manda emails, Excel o más escaneados

Lo que cambia es **un conector nuevo en `extract/`**, y nada más:

- El conector produce el mismo `InvoiceFacts`. `core/`, `rules/` y `pipeline/` no se tocan: la norma
  decide sobre hechos, no sobre formatos.
- **Email**: el cuerpo es texto → camino de texto (1,1 K tokens, 3,3 s) o, mejor, una plantilla nueva
  si el remitente repite formato. Los adjuntos entran por el camino que ya existe.
- **Excel**: no necesita LLM. Es un lector determinista, como `sources/excel.py`. Coste 0, latencia
  de milisegundos.
- **Más escaneados**: es el único caso que duele, 35 s y 8,9 K tokens por factura. La respuesta no es
  pagar más: es **subir la cobertura de plantillas** y que sólo lo verdaderamente ilegible llegue al
  LLM.
- **El texto de entrada sigue siendo un dato.** Un email es más fácil de envenenar que un PDF:
  `instrucciones.detectar_instruccion` se aplica igual, y la frase se guarda como evidencia.

La regla de diseño que sostiene todo esto: **un formato nuevo es un extractor nuevo, nunca una regla
nueva.** Por eso `InvoiceFacts` no tiene ningún campo que se llame `resultado`, `decision` ni `accion`.

---

## 7. Qué NO está medido (para no defender lo que no sabemos)

- **No hemos visto un solo 429 real.** Los límites (100 RPM, 5-10 concurrentes, 2M TPM) están
  publicados por Helmcode y son coherentes con la saturación observada en visión, pero no los hemos
  provocado. El 429 del guion es el caos simulado.
- **El respaldo de VISIÓN se deja vacío a propósito.** Existe el mecanismo y está probado, pero
  ninguno de los candidatos lee el NIF mejor que `qwen3.6`, así que activarlo sólo cambiaría un
  error por otro. Se activa con `ALBERTITOS_MODELO_VISION_FALLBACK` cuando haya un modelo que lo
  merezca.
- **Los 94 s de la tanda de 8 hilos** no están explicados. Se repitieron dos veces con el mismo
  valor; la hipótesis es un timeout del servidor, no está confirmada.
- Las cifras de facturas/hora de §4 son **extrapolación** de tandas de 16 y 8 ficheros, no una
  ejecución de 10.000.
