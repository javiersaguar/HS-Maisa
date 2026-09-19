# API de la confianza por factura · contrato para la consola (K3, 19/09 15:07)

**Qué es:** para cada factura, cuánta seguridad hay de que su **clasificación** (PAGAR / NO_PAGAR / ESCALAR) es la
correcta. Es una puntuación 0-100, con una banda (alta ≥ 80 · media ≥ 50 · baja < 50) y las tres razones que más pesan,
en frases para Alberto. **Qué no es:** ni la probabilidad de pagar (un ESCALAR puede tener confianza alta) ni una
probabilidad calibrada. Es ordinal: parte de 100 y resta una penalización por cada duda con nombre. Los pesos y su
porqué están en `src/albertitos/confianza/modelo.py` (`PESOS`) y en el ADR-0014.

**Sólo lectura.** No cambia decisiones, hechos, avisos ni la entrega. Hay un test que lo comprueba sobre una copia de
la BD real: `package` da el mismo `outcomes.jsonl`. Tiempos: las 500 en 0,04-0,06 s; una factura en 0,33 ms.

## Cómo se registra (Alejandro, una línea en `src/albertitos/console/api.py`)
```python
try:
    from albertitos import confianza
    RUTAS.update(confianza.rutas())
except ImportError:
    logger.warning("sin rutas de confianza")
```
Los handlers tienen la firma del puente, `(conn, query) -> (status, body)`, con la conexión de sólo lectura del puente.
Todas las respuestas llevan `api: 1`: sube si cambia un nombre o un tipo que la consola ya lee.

## Rutas
| Ruta | Parámetros | Devuelve | Ejemplo real |
|---|---|---|---|
| `GET /confianza/resumen` | `lote` | `{api, version, total, bandas{alta,media,baja}, por_resultado{PAGAR:{…}}, por_lote{"1":{…}}, media, umbrales, escala, segundos}` | `ejemplos/confianza-resumen.json` |
| `GET /confianza/ficheros` | `banda` (`alta`/`media`/`baja`), `resultado`, `lote`, `limite` (50; máx. 1000), `orden` (`asc` por defecto: **menor confianza primero**; `desc`) | `{api, items: [{file_id, lote, resultado, regla, puntuacion, banda, razon_principal, razones}], total, limite}` | `ejemplos/confianza-ficheros-revisar-primero.json` |
| `GET /confianza/fichero` | `file_id` (nombre del PDF; NFC) | la ficha completa (abajo) · `400` sin `file_id` · `404` si no tiene decisión vigente | `ejemplos/confianza-fichero-*.json` |

### La ficha de `/confianza/fichero`
| Campo | Qué es |
|---|---|
| `puntuacion` · `banda` | 0-100 · `alta` / `media` / `baja` |
| `razones` | Las 3 frases que más pesan. Primero lo que resta; si resta poco, lo que la respalda («el ERP espera el mismo importe al céntimo…») |
| `causa` | Qué sostiene la clasificación: «cumple las seis reglas…», «se escala por una causa clara…», «se escala sólo por dudas de lectura», «el ERP ya la da por pagada…», «contingencia» |
| `fuentes` | Desglose por fuente: `pdf`, `coherencia`, `maestro`, `erp`, `decision`, `politica`, `revisor`. Cada una con `penalizacion`, `dudas` (`[{id, texto, puntos, factor, aplicado, por_que}]`) y `a_favor` (frases) |
| `lecturas` | Plantilla: `{contraste: true, campos_distintos: []}`. Escaneada: `{n: 4, campos_distintos: ["iban"]}` |
| `metodo` · `regla` · `mismo_pdf_que` | Método de extracción, primera regla que falla, y los otros nombres del mismo PDF (copias exactas) |
| `escala` · `version` | Aviso literal de que no es una probabilidad · `confianza-1` |

`factor`: una duda de lectura cuenta a la mitad (0,5) cuando la decisión ya la corroboran el maestro y el ERP o la
sostiene una causa clara, y no cuenta (0) cuando es el propio motivo de escalar. Así no se cuenta dos veces.

## Propuesta de pantalla
1. **Lista de facturas: columna «confianza».** Un chip con el número y el color de la banda (alta verde, media ámbar,
   baja rojo). Al pasar el ratón, `razon_principal`.
2. **Filtro «revisar primero»:** `/confianza/ficheros?banda=baja` (ya viene ordenado de menor a mayor). Son las que se
   escalan sólo porque no se leyeron con seguridad: si el original está limpio, lo correcto sería PAGAR.
3. **Detalle de la factura: tarjeta «¿cuánto nos fiamos?».** El número y la banda arriba, las tres razones y, debajo,
   una fila por fuente (PDF · importes · maestro · ERP · decisión · políticas abiertas) con su penalización y sus frases.
   Hay que decir en pantalla, literal: **«Confianza en la clasificación, no probabilidad de pago.»**
4. **Panel:** las bandas por resultado de `/confianza/resumen`, en una barra apilada por resultado.
5. Si la ruta da 404 o no está registrada, la columna sale vacía («—»): la consola no puede caerse por esto.

El calendario de K1 ya la usa: `/bonus/calendario?con_confianza=true` pone la ficha de cada pago. Y el chat de K2 puede
llamar a `albertitos.confianza.puntuar(conn, file_id)`, que devuelve lo mismo que la ruta sin el campo `api`.

## Revisor LLM (opcional, apagado por defecto)
Una segunda opinión sobre si la clasificación es coherente con los hechos y los motivos, con esquema cerrado
(`de_acuerdo | desacuerdo | no_se` + una frase). Sólo entra como señal: un desacuerdo resta 15 y un acuerdo es una
frase a favor, sin puntos. El texto del PDF va delimitado como dato. Tope de 60 llamadas y ninguna a partir de las 17:30.
No escribe en la BD.
```bash
uv run python -m albertitos.confianza.revisor --maximo 60 --salida dist/ensayo/k3/revisor.json
ALBERTITOS_CONFIANZA_REVISOR=dist/ensayo/k3/revisor.json uv run python -m albertitos.console.api   # la consola lo enseña
```
Con el fichero puesto, la ficha trae `fuentes.revisor.opinion = {opinion, frase, modelo}`. Sin él, `null`. Si la
decisión ha cambiado desde la opinión, la opinión se ignora.
**Ensayo real (19/09, 15:13):** 53 llamadas sobre las 53 de banda media o baja; 52 «de acuerdo», 0 en desacuerdo y
1 timeout, degradado bien; p50 1,5 s. Confirma que ninguna clasificación contradice la norma escrita, pero no resuelve
las preguntas abiertas: juzga con la misma norma.

## Sobre la BD real (lote 1, 500 facturas; comando: `uv run python scripts/calibrar_confianza.py`)
| resultado | alta | media | baja |
|---|---:|---:|---:|
| PAGAR | 438 | 0 | 0 |
| NO_PAGAR | 9 | 0 | 0 |
| ESCALAR | 0 | 40 | 13 |

- **Ninguna ESCALAR llega a alta.** Las 53 tienen o una duda de lectura o una pregunta abierta del mentor: Q1 6, Q2 2,
  Q3 35 y Q5 2 (docs/agentes/MAPA-POLITICAS.md). Es lo que hay que resolver con el mentor, no un defecto de la métrica.
- **Las 13 de banda baja** son las que se escalan sólo porque no se leyeron con seguridad: las 5 reconciliadas del
  ADR-0011, la superpuesta del ADR-0010 y las escaneadas cuyas lecturas no coinciden en el NIF, el IBAN o el importe.

## Calibración: lo que hay, dicho como es
Sin la muestra etiquetada cerrada (hoy, `acordado` 0 de 21) **no hay verdad con que calibrar**: no se puede decir «el
X % de las de banda alta acierta». Lo que sí se ha comprobado (`scripts/calibrar_confianza.py`):
- **Contraste plantilla↔LLM:** de las 468 de plantilla, las 468 tienen su lectura de contraste en la caché y las 468
  coinciden en NIF, IBAN, pedido e importe (reproduce CONTRASTE-TOTAL, ahora factura a factura). Confirma la lectura,
  no la clasificación.
- **Mapa de políticas de I2:** los 45 ficheros en una frontera de política salen con la misma pregunta abierta, uno a uno.
  I2 las calcula ejecutando variantes de la norma; aquí se leen de la evidencia de cada decisión. Son dos caminos distintos.
- **Revisión a mano de I2:** las 6 facturas que I2 comprobó limpias contra las fuentes (sólo las frena una orden en el PDF)
  salen en banda media, como deben: su clasificación depende de la pregunta Q1.
- **Lo que ya sabíamos dudoso:** las 10 de menor confianza y las 13 de banda baja ya estaban señaladas por los hechos
  (reconciliadas, discrepancias, superpuesta) o por el mapa de I2. No es una prueba independiente, porque la puntuación
  usa los mismos avisos. Confirma que los pesos las ponen abajo.
- Hay una **tercera lectura independiente** de las 21 de la muestra (agente H2), guardada fuera del repo. Su contraste por
  banda se publicará cuando Mónica cierre la muestra, para no contaminarla.

Cuando la muestra esté cerrada: `uv run python scripts/calibrar_confianza.py` añade solo los aciertos por banda.
