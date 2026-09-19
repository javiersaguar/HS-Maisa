# Parte de fin de ciclo · ciclo 11 (bonus)

Cada agente rellena SU sección al terminar (o si lleva > 20 min bloqueado). Cifras, comandos literales y su salida, rutas.
Partes anteriores en `partes/` (… · 09: I1-I2 · 10: J1-J5).

## K1 · Calendario continuado y sus datos para la consola
- **Estado: terminado.** Commits: `be179cd` (tesorería, proveedores, programa y rutas) · `fbf5b68` (contrato, ejemplos, BONUS, ADR-0012) · el de `con_confianza`. Sin push.
- **Huellas**: BD real `0dc1c7817fda` → `0dc1c7817fda`; `outcomes.jsonl` `1ec4be206089` → `1ec4be206089`.
- **A · Tesorería** (`bonus/tesoreria.py`):
  - por semana ISO, lo pagado, lo acumulado y lo vencido;
  - por proveedor, facturas, importe, vencidas y primera y última fecha de pago;
  - `programa(tope)`, que reparte la remesa por antigüedad sin pasar del tope, sin trocear facturas (un pago mayor que el tope sale solo, marcado) y dice las semanas necesarias;
  - CLI `--tope-semanal`, que añade `tesoreria.json`, `proveedores.csv` y las secciones «Tesorería» y «Por proveedor» a `calendario.html`.
- **Cifras sobre una copia de la BD real** (`uv run python -m albertitos.bonus --db dist/ensayo/k1/copia.db --salida dist/ensayo/k1/bonus --tope-semanal 150000`, 0,20 s):
  - 438 PAGAR, **2.428.159,06 €**;
  - vencido 2.383.400,88 € y en plazo 44.758,18 €, que suman el total al céntimo;
  - 11 proveedores, cuya suma da 2.428.159,06 €;
  - con 150.000 €/semana, **al día en 16 semanas** y todo pagado en 17.
- **B · Lote 2:** cada `Pago` lleva `lote` y el calendario incluye todos los lotes vigentes. En la BD del ensayo general de J1 (lote 2 simulado) las 10 del lote 2 son ESCALAR, porque son copias de pedidos del lote 1, así que no aportan pagos; y el lote 1 baja a 427 PAGAR por lo mismo. Un PAGAR del lote 2 está cubierto con un test sintético (`c.pdf`, lote 2).
- **C · Rutas:** `bonus.rutas()` → `/bonus/{resumen,calendario,proveedores,remesa,avisos,tesoreria}`, con la firma del puente.
  - Filtros de `calendario`: `semana`, `proveedor`, `lote`, `vencido`, `limite` y `con_confianza`. Todas aceptan `estricto`.
  - Respuestas: 400 si un parámetro está mal y 409 si la BD no tiene decisiones.
  - `calcular_conn` usa la conexión del puente y la deja sin transacción abierta (hay test).
  - Rendimiento: ~0,02 s por ruta con la BD caliente.
- **D · Contrato:** `docs/api/bonus.md`: registro con una línea, convenciones, cada ruta, las cifras de hoy y la pantalla propuesta. Lleva el aviso obligatorio de los IBAN sintéticos. Hay 7 ejemplos reales en `docs/api/ejemplos/bonus-*.json`, generados con las propias rutas.
- **E · Confianza:** `?con_confianza=true` adjunta lo que devuelva `albertitos.confianza.puntuar(conn, file_id)` de K3, tal cual. Sin el módulo, sale `null` con una nota (hay test con K3 ausente y con un K3 falso). A las 15:00, K3 aún no lo ha publicado.
- **Verificado:**
  - `uv run pytest tests/test_bonus.py -q` → **26 passed**.
  - Test de la regla 5 (`test_el_bonus_no_cambia_la_entrega_ni_la_bd`): bonus entero sobre una copia de la BD real → la BD no cambia ni un byte y `package` da el mismo `outcomes.jsonl`.
  - Batería completa: `uv run pytest -q` → **521 passed**.
  - `make check` **falla por lint en `src/albertitos/chat/`** (K2, en curso y sin commitear: UP041 `socket.timeout`). No es mío y no lo he tocado. `make agentes-check` → OK.
- **Hallazgo:** las horas de mis dos primeras entradas en la bitácora eran erróneas; corregidas en la tercera.
- **Necesito de otros:**
  - **Alejandro:** la línea `RUTAS.update(bonus.rutas())` y las pantallas de `docs/api/bonus.md`, con el aviso de los IBAN siempre visible.
  - **K2:** que use `calcular_conn` o las rutas en vez de `calcular(ruta)`.
  - **K3:** con `puntuar(conn, file_id)` publicado, la confianza aparece sola en el calendario.

## K2 · Chat con Alberto, de sólo lectura, con Helmcode
_(pendiente)_

## K3 · Métrica de confianza por factura
_(pendiente)_
