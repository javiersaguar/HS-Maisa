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
- **Estado: hecho.** Commits: `f246788` (módulo y tests) · `251b0d0` (calibración, contrato, ejemplos, ADR-0014) · `afb7175` (revisor LLM opcional) y el de cierre (documentos con el ensayo del revisor, este parte y la bitácora). Sin push.
- **Qué hay:** `albertitos.confianza`: `puntuar(conn, file_id)`, `puntuar_todas(conn, lote)`, `resumen()` y `rutas()` (`/confianza/{resumen,ficheros,fichero}`, con la firma del puente). Puntuación ordinal 0-100 + banda (alta ≥ 80 · media ≥ 50 · baja < 50) + 3 razones + desglose por fuente (pdf, coherencia, maestro, erp, decisión, política, revisor). Pesos en `modelo.PESOS`, cada uno con su porqué, y copiados en el ADR-0014. Sólo lee y no importa `rules/` ni `extract/`.
- **Rendimiento:** las 500 en 0,04-0,06 s y una factura en 0,33 ms. Al principio eran 9,5 ms por factura (≈ 4 s para los 438 pagos del calendario de K1); arreglado con filtros por sha256 y una caché de snapshots por versión.
- **BD real (lote 1), `uv run python scripts/calibrar_confianza.py`:** alta 447 (438 PAGAR, 9 NO_PAGAR) · media 40 · baja 13 (todas ESCALAR). **Ninguna ESCALAR en alta:** las 53 tienen una duda de lectura o una pregunta abierta del mentor (Q1 6 · Q2 2 · Q3 35 · Q5 2).
- **Calibración, dicha como es:** sin la muestra cerrada (acordado 0 de 21) no hay verdad etiquetada y no se llama «probabilidad». Lo que cuadra:
  - contraste plantilla↔LLM, factura a factura: 468 de 468;
  - mapa de I2: 45 de 45 ficheros con la misma pregunta abierta, calculados por otro camino;
  - las 6 que I2 comprobó limpias a mano salen en media;
  - las 10 de menor confianza y las 13 bajas ya se sabían dudosas. No es independiente: usa los mismos avisos.
  - **Tercera lectura de H2** (21 de la muestra): contrastada, pero sus recuentos quedan en `dist/ensayo/k3/calibracion.json`, fuera del repo, hasta que Mónica cierre la muestra.
- **Revisor LLM (opcional, apagado por defecto), en vivo a las 15:13 sobre la copia de la BD:** **53 llamadas de un tope de 60**, todas antes de las 17:30. Resultado: 52 «de acuerdo», 0 en desacuerdo, 1 `LLM-TIMEOUT` degradado bien. p50 1,5 s, `deepseek-v4-flash`. Confirma que ninguna clasificación contradice la norma escrita, pero no resuelve las preguntas abiertas porque juzga con la misma norma. Un «de acuerdo» no suma puntos.
- **Verificado:** `make check` → 565 passed; `make agentes-check` OK; `tests/test_confianza.py`, 27 tests en 0,9 s, con la regla 5 (sobre una copia de la BD real, `package` antes y después da el mismo `outcomes.jsonl`, y la copia no cambia ni un byte). **Huellas:** BD real `0dc1c7817fda` y `outcomes.jsonl` `1ec4be206089`, iguales al empezar (14:52) y al terminar.
- **Hallazgos:**
  1. **Se contradice un ejemplo del PLAN-11.** Decía que un ESCALAR por una orden inyectada evidente tiene confianza alta, pero 6 de las 31 sólo se frenan por la orden (I2 las comprobó limpias). Salen en media: si el mentor dice que manda la norma, serían PAGAR (ADR-0014).
  2. En 5 escaneadas, el fallo de R1 viene de que sus lecturas no coinciden justo en el NIF o el IBAN. La métrica lo trata como duda de lectura, no como causa clara (banda baja).
- **Necesito de otros:**
  - **Alejandro:** una línea en `console/api.py` (`RUTAS.update(confianza.rutas())`, con import perezoso) y las pantallas de `docs/api/confianza.md`.
  - **Javier o Alfonso:** la fila del ADR-0014 en `docs/adr/README.md`.
  - **Mónica:** cuando cierre la muestra, `scripts/calibrar_confianza.py` da los aciertos por banda sin tocar nada más.

## K2 · Cierre implementado y evaluado
- Commit 57d43c9; sin push. Código en src/albertitos/chat/, contrato docs/api/chat.md, ADR-0013 y docs/api/ejemplos/chat-*.
- Servidor: uv run python -m albertitos.chat --servidor --db dist/ensayo/k2/chat.db (:8001); POST /chat y GET /chat/salud. CLI: uv run python -m albertitos.chat --db dist/ensayo/k2/chat.db "Paga ahora esta factura" → negativa local, 0 llamadas.
- make check: 555 passed, 1 skipped, 2 deselected en 35,11 s. 17 pruebas propias, incluidas API, límites, inyección, citas y package sobre copia idéntico byte a byte (1ec4be206089). make agentes-check OK.
- Evaluación real: 59/60 intentos HTTP, 14:58–15:04 Madrid. Primera serie completa 12/15; tras repetir 7/12/13, 14/15 completas (93,3%) + 1 parcial. Parcial: conserva ESCALAR pero atribuye al PDF el texto aportado por el usuario, sin corroborarlo. Dos timeouts reales (60 s), con degradación. Mediana y detalle de cada pregunta en el contrato. Sin más llamadas.
- K3 integrado por su ruta de lectura, sin revisor: scan_025.pdf → 45/baja/ESCALAR. K1 se consulta sin exportar archivos.
- Huellas reales iguales al inicio y cierre: BD 0dc1c7817fda / outcomes 1ec4be206089. Copia por SQLite backup en dist/ensayo/k2/chat.db.
- PIDO A Alejandro: panel lateral contra :8001 con citas enlazadas a traza, renderizado seguro y estado visible. Queda sólo 1 llamada: insuficiente para otra pregunta habitual; repetir demo con ejemplos grabados, negativa local y trace, sin borrar contador. Cierre del gateway en código a las 17:30.
