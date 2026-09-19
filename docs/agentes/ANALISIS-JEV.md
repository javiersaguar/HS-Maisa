# Jev (TypeSafe AI): ¿lo usamos? · análisis de Javier, sábado 19/09 13:55

Nos lo recomienda el fundador de QuiverAI a partir de [Building a harness with Jev](https://www.langchain.com/blog/building-a-harness-with-jev).
Esto es lo que es, dónde encajaría en Albertitos, lo que cuesta y lo que arriesga. **Recomendación, al final.**

## 1 · Qué es, sin marketing
- **Un clasificador alojado, no un LLM.** TypeSafe lo llama «modelo System One»: recibe un `state` (texto o datos
  estructurados) y preguntas tipadas, y devuelve **probabilidades calibradas**, no texto. Hay tres tipos de pregunta:
  - **Choice**: elige una opción de una lista;
  - **Score**: sitúa el estado en una escala (bajo/medio/alto);
  - **Noul**: probabilidad de que una afirmación sea cierta.

  Varias preguntas por llamada, evaluadas en paralelo.
- **Lo que promete** (cifras del fabricante):
  - 70-500 ms por respuesta (0,4 s de media en su propia evaluación);
  - 0,042 $ por millón de tokens de entrada, y la salida gratis («puede estar subvencionado»);
  - la salida siempre cumple el esquema;
  - calibración entrenada con RL («si dice 70 %, acierta el 70 %»).
- **Calidad**: en la evaluación de flujos del propio TypeSafe saca un 76,0 %, frente al 76,8 % de
  **`deepseek-v4-flash`, que ya usamos**, y el 78-79 % de los modelos frontera. Evaluación hecha por ellos, con sesgo declarado.
- **Límites que importan aquí**:
  1. **Sólo texto**: no ve imágenes ni PDFs, y nuestras 29 escaneadas son imágenes.
  2. **No extrae valores**: sólo elige entre opciones. No puede leer un NIF, un IBAN ni un importe.
  3. **No da el porqué**: devuelve un número sin explicación y sin el fragmento que lo justifica.
  4. **Es un servicio externo**: pide `TYPESAFE_API_KEY`. No hay versión local ni términos públicos de retención de datos.
- **Cómo se usa:** `langchain-typesafe` (`TypeSafeClassifier`, más *middlewares* de enrutado y de guardarraíl para agentes),
  `typesafe-sdk`, o REST directo: `POST https://api.typesafe.ai/v1/systemone`.

## 2 · Dónde NO encaja (y por qué)
| Sitio | Por qué no |
|---|---|
| **Extraer hechos** (NIF, IBAN, importes, fechas) | Jev no genera valores, sólo elige entre opciones. Y las escaneadas no las ve. |
| **Decidir PAGAR / NO_PAGAR / ESCALAR** | Rompe el principio del sistema (ADR-0001: el LLM extrae y **la norma como código decide**). Una probabilidad no es un motivo con evidencia: perderíamos trazabilidad (20 pts). Y la validación es binaria contra una referencia privada: un clasificador probabilístico no nos acerca a 540/540, sólo añade una fuente de cambios. |
| **Enrutar entre plantilla, LLM de texto y visión** | Ya lo hace una regla determinista: si hay plantilla, plantilla (468/500 a coste 0); si hay capa de texto, LLM de texto; si no, visión. No hay decisión difusa que mejorar. |
| **Guardarraíl de los agentes** (`AutoModeMiddleware`) | Nuestros guardarraíles son hooks deterministas que fallan en voz alta. Uno probabilístico y de red es peor para eso, y además no usamos LangChain. |

## 3 · Dónde SÍ podría aportar, sin tocar la entrega
Las dos opciones son **señales de segunda opinión**, fuera del camino que decide. Con ellas activadas o apagadas,
`outcomes.jsonl` tiene que salir **byte a byte igual**. Eso se fija con un test.

**A · Segunda opinión sobre «el PDF intenta darnos órdenes»** (la trampa principal de la Caja: 31 facturas con
`TEXTO_INSTRUCCION`). Hoy lo detecta `extract/instrucciones.py` con patrones, y lo confirma el campo `texto_sospechoso`
del LLM. Jev puede responder sobre la capa de texto de las **471 facturas con texto**:
- una **Noul**: «¿el texto contiene una instrucción dirigida a quien procesa la factura?»;
- una **Choice**: `ninguna · ordena_pagar · ordena_escalar · ordena_ignorar_dato · dice_ser_prueba · anula_pedido`.

Cuando Jev y el detector no coinciden, la auditoría lo marca en **ÁMBAR**. No cambia ninguna decisión: sirve para
encontrar lo que se nos escapa, y en el lote 2 no vemos las trampas hasta las 18:00.

**B · Ordenar la cola de ESCALAR para Alberto** (bonus y consola): son 53 facturas escaladas. Una pregunta **Score**
(urgencia/riesgo: bajo/medio/alto) con el motivo y los hechos como `state` las ordena, con su probabilidad, para que
Alberto empiece por lo importante. Es puramente de presentación, calibrado, y da la cifra de escala: «10.000 facturas
triadas por menos de un céntimo».

## 4 · Coste, riesgo y encaje con el reto
- **Dinero:** unos 500 × 1.500 tokens ≈ 0,75 M tokens → **unos 0,03 $** por pasada. Irrelevante.
- **Datos:** hoy la regla es que **las facturas no salen del portátil salvo al LLM** (el gateway de Helmcode). Jev es un
  **tercero nuevo, sin términos públicos de retención de datos**. Los datos de la Caja son sintéticos, pero sigue
  haciendo falta el visto bueno del equipo (y mirar si las bases del reto dicen algo sobre proveedores externos).
- **Operativo:** es una clave más, una dependencia de red más y un modo de fallo más a las 18:00 y en la defensa. Si
  se integra, es **opcional y degradable**: sin clave o con Jev caído, la señal no aparece y nada se para. Con timeout
  de 2 s, breaker y caché por sha256.
- **Stack:** «nada más sin ADR». Hace falta un ADR (con número propio: el 0013 y el 0014 son del chat y de la confianza, PLAN-11), tanto si entra como si se descarta. Y el descarte
  razonado también suma: en el PDF puntúan las alternativas evaluadas (35 pts).
- **Tiempo:** son las 14:00, con el lote 2 a las 18:00 y la congelación a las 02:00. Tocar extract, auditoría o consola
  ahora compite con lo que nos puede dejar NO APTO.

## 5 · Cómo se implementaría (si pasa la prueba)
1. **Prueba medida, 45 min, sin tocar el pipeline** (`scripts/bench_jev.py`, en `dist/ensayo/jev/`). Sobre las
   **31 facturas con `TEXTO_INSTRUCCION`** y **40 limpias** de la Caja, que ya tenemos etiquetadas por el detector y
   revisadas a mano en I2, con la opción A:
   - precisión y exhaustividad frente al detector;
   - latencia p50 y p95;
   - tokens y coste;
   - cuántos desacuerdos hay y, **de ellos, cuántos son fallos nuestros** (se revisan a mano).
2. **Criterio para seguir:** que encuentre **al menos un caso real que se nos escapa**, o que confirme las 31 con
   probabilidades altas y el 0 % de falsos positivos en las limpias. **Si no, se descarta** y queda en su ADR con
   las cifras.
3. **Integración mínima**, después de entregar el lote 2 (sábado 20:00-23:00) y en el carril de Javier:
   - `src/albertitos/extract/jev.py`: cliente `httpx` contra la API REST, sin LangChain ni SDK nuevo. Clave
     `TYPESAFE_API_KEY` en `.env`, caché en `cache_llm` con clave `sha|jev-q1|jev-latest`, timeout de 2 s y el mismo
     breaker.
   - Señal = **un evento `validate`** con las probabilidades en el detalle. **Sin tocar** `InvoiceFacts` (core es de
     Miguel) ni `rules/` (Mónica). `trace` la enseña.
   - Auditoría: una comprobación ÁMBAR, «Jev y el detector no coinciden».
   - `ALBERTITOS_JEV=0` por defecto. Test: con Jev encendido y apagado, `outcomes.jsonl` idéntico.
   - Opción B, sólo en el bonus: `score` por escalada en `dist/bonus/escalados.csv`.
4. **La defensa, si entra:** «usamos un modelo de decisión barato **sólo para encontrar lo que se nos escapa**; nunca
   decide un pago». Si no entra: «lo evaluamos; no ve imágenes, no extrae, no explica, y nuestra norma ya decide de forma
   determinista. Descartado con cifras (su ADR)».

## 6 · Recomendación
**No en el camino que decide ni en el de extracción. Sí, como mucho, como segunda opinión opcional, y sólo si la
prueba lo justifica.** En orden:
1. **Ahora:** nada que afecte al lote 2. Si hay manos libres, **la prueba de 45 min** (paso 5.1), con el visto bueno
   del equipo para mandar el texto de las facturas a TypeSafe.
2. **16:30:** decidir con las cifras. Si no aporta, **ADR propio («Evaluado y descartado»; el 0013 y el 0014 son del chat y la confianza)** y a otra cosa.
3. **Después de entregar el lote 2:** integrar la opción A (y la B en el bonus) si aportó, con apagado por defecto
   y la entrega blindada por el test de identidad. Congelación a las 02:00.

Lo que no sabemos y habría que preguntar a TypeSafe (o a QuiverAI) antes de mandar datos: retención de datos,
límites de tamaño del `state`, límites de peticiones, y si hay créditos gratis para el hackathon.

## Fuentes
- [Building a harness with Jev (LangChain)](https://www.langchain.com/blog/building-a-harness-with-jev)
- [Documentación de TypeSafe](https://docs.typesafe.ai) · [System One](https://docs.typesafe.ai/concepts/system-one)
- [Introducing System One Models & Jev (TypeSafe)](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- [TypeSafe Jev: benchmarked and priced (Developers Digest)](https://www.developersdigest.tech/blog/typesafe-jev-system-one-models-release-guide-2026)
- [Jev explicado (DataCamp)](https://www.datacamp.com/blog/system-one-models-jev)
