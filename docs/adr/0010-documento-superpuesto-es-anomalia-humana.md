# ADR-0010 · Un documento superpuesto lo mira una persona

- **Estado:** aceptado
- **Número:** escrito como ADR-0009 en la rama de Mónica (commit `b97b648`); renumerado al mergear porque el 0009 ya era la contingencia.
- **Fecha:** 2026-09-19 09:05 · **Dueño:** Mónica · **Módulos:** rules/

## Contexto
29 de los 500 PDFs de la Caja no tienen capa de texto y se leen con visión. Al aprovechar la segunda
lectura de cada escaneada (commit `b678cfd`, bitácora del 19/09 04:05), el extractor detecta cuándo un
fragmento del documento nombra a **otro** proveedor del maestro — razón social o NIF exacto — y lo
publica como `Aviso.DOCUMENTO_SUPERPUESTO`, con el fragmento y el proveedor en el evento.

Hoy salta en **1 de las 29**: `scan_025.pdf`, una factura de Limpiezas Turia (P004) en la que asoma un
trozo que nombra a Electricidad Montcada (P006). El resto de reglas de la v3 pasan para ese fichero,
así que sin consumir el aviso la factura se paga. La auditoría de entrega la marcaba en rojo.

La pregunta que quedaba abierta era de la norma, no del extractor: ¿ese aviso es una de las anomalías
que la R6 manda a un humano?

## Alternativas consideradas
1. **Ignorarlo en la norma** — el aviso queda como información de traza y `scan_025.pdf` sale PAGAR.
   Reparto 444 PAGAR / 47 ESCALAR / 9 NO_PAGAR. Se descarta: pagaríamos una factura de la que no
   sabemos con certeza qué documento es, que es justo lo que la R6 existe para evitar.
2. **Tratarlo como NO_PAGAR** — se descarta: no hay ninguna violación objetiva comprobada contra el
   ERP ni contra el maestro. La frontera de la v3 reserva NO_PAGAR para lo comprobado (pedido ya
   PAGADA); un documento confuso es exactamente una duda, y una duda se escala.
3. **(elegida) Entra en `ANOMALIAS_HUMANO`** — la R6 falla y la factura sale ESCALAR con el motivo
   `v3.R6: anomalía que debe ver una persona: documento_superpuesto`.

## Decisión
`Aviso.DOCUMENTO_SUPERPUESTO` es una anomalía que debe ver una persona. Se implementa añadiéndolo al
conjunto `ANOMALIAS_HUMANO` de `src/albertitos/rules/norma_v3.py`, que ya consume `regla_6_anomalias`.

## Consecuencias aceptadas
- Un ESCALAR más de trabajo para Alberto hoy. Es el lado barato del error: un ESCALAR de más le cuesta
  minutos, un PAGAR de más cuesta dinero y la validación.
- Si el lote 2 del sábado trae varias escaneadas con documentos superpuestos, el porcentaje de ESCALAR
  sube y la auditoría puede sacar un ámbar de reparto. Es el comportamiento buscado, no un fallo.
- El cambio es **in situ sobre la v3**: la etiqueta de versión no cambia, así que el linaje no detecta
  por sí solo que la norma es otra. Las decisiones ya tomadas hay que reprocesarlas explícitamente
  (`reprocess --todo`, o aplicar este cambio antes del reprocesado) o quedarían con la norma vieja.
- `scan_023.pdf` no es detectable: ninguna de sus lecturas nombra a otro proveedor. Sigue en ESCALAR
  por otras reglas, pero este ADR no lo cubre.

## Evidencia
- Medido por Javier en una copia aislada (`dist/ensayo/e2.db`, BD real intacta, 0 tokens): el detector
  salta en 1 de 29 escaneadas; `reprocess --impacted` recalcula 29 de 500 y cambia 1. Sin este cambio,
  `scan_025.pdf` pasa de ESCALAR a PAGAR.
- Con el cambio, el reparto del lote 1 se mantiene en **443 PAGAR · 48 ESCALAR · 9 NO_PAGAR** (v3,
  ERP v1, maestro `80911e429c6c`) y la auditoría de entrega pasa de ROJO a verde con un ámbar.
- Test: `tests/test_rules.py`, caso `(dict(avisos=[Aviso.DOCUMENTO_SUPERPUESTO]), "v3.R6")`.
- Petición y recomendación de Javier en `docs/agentes/BITACORA.md`, entrada del 19/09 04:05
  (commits `b678cfd`, `511c44a`); comandos de aplicación al final de `docs/agentes/AUDITORIA-ENTREGA.md`.

## Pendiente
La frontera general NO_PAGAR / ESCALAR sigue siendo una pregunta para el mentor y tendrá su propio ADR.
Si la respuesta ensancha NO_PAGAR, este caso se revisa: hoy encaja en ESCALAR por ser una duda, no una
violación comprobada.
