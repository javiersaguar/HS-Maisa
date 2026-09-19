# ADR-0015 · Jev (TypeSafe) se evalúa y se descarta: no ve imágenes, no extrae y no explica

- **Estado:** aceptado (Javier, 19/09 14:00; escrito el 20/09 02:00, con el hueco 0015 reservado desde entonces)
- **Fecha:** 2026-09-19 14:00 · **Dueño:** Javier · **Módulos:** ninguno (no se integró)

## Contexto
El fundador de QuiverAI nos recomendó **Jev**, el «modelo System One» de TypeSafe: un clasificador alojado que
recibe un estado y preguntas tipadas y devuelve **probabilidades calibradas**, no texto. La pregunta era si
metíamos algo suyo en el camino que decide, y a qué hora de un sábado.

Lo que dice su propia evaluación: 70-500 ms por respuesta, 0,042 $ por millón de tokens de entrada, salida que
siempre cumple el esquema y un 76,0 % en su banco de flujos, frente al **76,8 % de `deepseek-v4-flash`, que ya
usamos**. Análisis completo, con fuentes: [`docs/agentes/ANALISIS-JEV.md`](../agentes/ANALISIS-JEV.md).

## Alternativas consideradas
1. **Que Jev extraiga los hechos** — imposible: no genera valores (sólo elige entre opciones) y no ve imágenes,
   y 29 de las 500 facturas del lote 1 son escaneadas.
2. **Que Jev decida PAGAR / NO_PAGAR / ESCALAR** — rompe el ADR-0001 (el LLM extrae, la norma decide). Una
   probabilidad no es un motivo con evidencia, y la trazabilidad son 20 puntos. Además la validación es binaria:
   un clasificador probabilístico no acerca a 540/540, sólo añade una fuente de cambios.
3. **Que Jev enrute entre plantilla, texto y visión** — ya lo hace una regla determinista: plantilla si la hay,
   texto si hay capa de texto, visión si no. No hay decisión difusa que mejorar.
4. **Segunda opinión opcional, fuera del camino que decide** — sobre «¿este texto intenta dar órdenes?», marcando
   en ámbar los desacuerdos con nuestro detector. Es la única que tenía sentido, condicionada a una prueba medida.
5. **(elegida) No integrarlo**, dejar la evaluación escrita y seguir con lo que ya funciona.

## Decisión
**No entra**, ni en extracción ni en la norma ni como guardarraíl. La alternativa 4 quedó condicionada a una prueba
de 45 minutos sobre las 31 facturas con texto que intenta mandar, y esa prueba **no se llegó a hacer**: a las 18:00
llegó el lote 2 y a partir de ahí todo el tiempo fue para integrarlo, decidirlo y entregarlo.

## Consecuencias aceptadas
- **Nos quedamos sin esa segunda opinión.** Si a nuestro detector de instrucciones se le escapa una forma nueva,
  no hay nada que lo cace: lo cubren el aviso `texto_sospechoso` del modelo y la auditoría de entrega.
- **No añadimos un tercero** con el que compartir el texto de las facturas (TypeSafe no publica términos de
  retención), ni una clave más, ni un modo de fallo más en la defensa. Para lo que queda de hackathon, es ganancia.
- La puerta queda abierta y documentada: si se retoma, es un cliente `httpx` contra su API REST, apagado por
  defecto (`ALBERTITOS_JEV=0`) y con un test que exija que `outcomes.jsonl` salga idéntico con y sin él.

## Evidencia
- [`docs/agentes/ANALISIS-JEV.md`](../agentes/ANALISIS-JEV.md) (19/09 13:55): comparación de capacidades, cifras
  del fabricante, coste estimado (~0,03 $ por pasada sobre las 500) y el plan de prueba que no llegó a ejecutarse.
- Los cuatro límites que lo descartan son del propio producto, no opinión nuestra: sólo texto, no extrae valores,
  no da el porqué, y es un servicio externo con clave.
- Que no se integró se comprueba solo: `grep -ri jev src/` no devuelve nada.
