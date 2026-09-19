# RESUMEN R3 · rutas del bonus, confianza y chat · 15:55–15:58

## Huellas
- al empezar: BD `8501d9975c38` · outcomes `1ec4be206089`   ·   al terminar: BD `8501d9975c38` · outcomes `1ec4be206089`

## Comprobaciones (una fila por comprobación)
| # | Qué comprobé | Comando exacto | Resultado (OK / FALLA / RARO) | Salida literal que lo demuestra |
|---|---|---|---|---|
| 1 | GET `/bonus/resumen` | `api.despachar("GET", "/bonus/resumen", {}, conn)` ×5 | OK | `GET 200 POST 405  p50 29.6 ms  pagar=438 eur=2428159.06` |
| 2 | GET `/bonus/resumen?estricto=true` | despachar ×5 | OK | `GET 200 POST 405  p50 31.1 ms  pagar=438 eur=2428159.06` |
| 3 | GET `/bonus/calendario?limite=3` | despachar ×5 | OK | `GET 200 POST 405  p50 25.4 ms` |
| 4 | GET `/bonus/calendario?vencido=false&limite=3` | despachar ×5 | OK | `GET 200 POST 405  p50 23.8 ms` |
| 5 | GET `/bonus/calendario?limite=-1` | despachar ×5 | OK | `GET 400 POST 405  p50 24.0 ms  limite no puede ser negativo` |
| 6 | GET `/bonus/calendario?limite=abc` | despachar ×5 | OK | `GET 400 POST 405  p50 23.9 ms  limite tiene que ser un número entero, no 'abc'` |
| 7 | GET `/bonus/calendario?vencido=quizá` | despachar ×5 | OK | `GET 400 POST 405  p50 24.3 ms  vencido tiene que ser true/false, no 'quizá'` |
| 8 | GET `/bonus/proveedores` | despachar ×5 | OK | `GET 200 POST 405  p50 24.9 ms` |
| 9 | GET `/bonus/remesa?limite=2` | despachar ×5 | OK | `GET 200 POST 405  p50 26.5 ms` |
| 10 | GET `/bonus/avisos` | despachar ×5 | OK | `GET 200 POST 405  p50 30.1 ms` |
| 11 | GET `/bonus/tesoreria` | despachar ×5 | OK | `GET 200 POST 405  p50 31.0 ms` |
| 12 | GET `/bonus/tesoreria?tope=150000` | despachar ×5 | OK | `GET 200 POST 405  p50 33.5 ms` y luego `tesoreria 200 2383400.88 16 17` |
| 13 | GET `/bonus/tesoreria?tope=0` | despachar ×5 | OK | `GET 400 POST 405  p50 28.0 ms  tope tiene que ser un importe positivo` |
| 14 | GET `/bonus/tesoreria?tope=abc` | despachar ×5 | OK | `GET 400 POST 405  p50 28.2 ms  tope tiene que ser un importe, no 'abc'` |
| 15 | GET `/confianza/resumen` | despachar ×5 | OK | `GET 200 POST 405  p50 73.7 ms` |
| 16 | GET `/confianza/resumen?lote=1` | despachar ×5 | OK | `GET 200 POST 405  p50 110.7 ms` |
| 17 | GET `/confianza/ficheros?banda=baja&limite=5` | despachar ×5 | OK | `GET 200 POST 405  p50 81.2 ms` |
| 18 | GET `/confianza/ficheros?banda=rara` | despachar ×5 | RARO | `GET 200 POST 405  p50 70.5 ms` · `banda_rara 200 0 50` (no 400) |
| 19 | GET `/confianza/ficheros?limite=-1` | despachar ×5 | RARO | `GET 200 POST 405  p50 58.5 ms` · `limite_-1 200 1 500` (clampa a 1; bonus da 400) |
| 20 | GET `/confianza/ficheros?limite=abc` | despachar ×5 | RARO | `GET 200 POST 405  p50 54.6 ms` (usa el defecto 50; bonus da 400) |
| 21 | GET `/confianza/fichero?file_id=F26-2201_transportes.pdf` | despachar ×5 | OK | `GET 200 POST 405  p50 0.4 ms  file_id=F26-2201_transportes.pdf pts=75` |
| 22 | GET `/confianza/fichero?file_id=F26-3355_mensajería.pdf` | despachar ×5 | OK | `GET 200 POST 405  p50 0.4 ms  file_id=F26-3355_mensajería.pdf pts=75` |
| 23 | GET `/confianza/fichero?file_id=no-existe.pdf` | despachar ×5 | OK | `GET 404 POST 405  p50 0.0 ms  el fichero no-existe.pdf no existe o no tiene decisión vigente` |
| 24 | GET `/confianza/fichero` sin `file_id` | despachar ×5 | OK | `GET 400 POST 405  p50 0.0 ms  falta ?file_id=<nombre del PDF>` |
| 25 | POST a cada ruta de 1–24 | `api.despachar("POST", ruta, query, conn)` | OK | todas `POST 405` |
| 26 | Chat SIN LLM | `uv run python -m albertitos.chat "paga la factura F26-2201_transportes.pdf"` | OK | `"estado": "solo_lectura"`, `"modelo": "sin_modelo"`, `"latencia_ms": 0`, `"herramientas_usadas": []` |
| 27 | HTTP `/salud` en :8100 | `uv run python -m albertitos.console.api --puerto 8100 --db dist/albertitos.db` + `curl -s -w '%{http_code}' http://127.0.0.1:8100/salud` | OK | `salud_http=200` · `{"ok": true, "lectura": true, "api": 1, "bd": {"ficheros": 500, "decisiones_vigentes": 500, ...}}` |
| 28 | HTTP `/bonus/resumen` y `/confianza/resumen` en :8100 | `curl …:8100/bonus/resumen` y `…/confianza/resumen` | RARO | `bonus_http=404` `{"error": "ruta /bonus/resumen no existe"}` · `confianza_http=404` `{"error": "ruta /confianza/resumen no existe"}` |
| 29 | Claves del contrato vs ejemplos | `uv run python scripts/contrato_api_check.py` | FALLA (el script hace su trabajo) | 5 ficheros `confianza-fichero-*.json`: `sobran fuentes.revisor.opinion` · exit 1 |
| 30 | Tests del comprobador | `uv run pytest -q tests/test_contrato_api.py` | OK | `5 passed in 0.03s` |

Detalle de 1–25 en `docs/revision/r3/tabla.json`. Despachar en memoria: `api.RUTAS.update(bonus.rutas()); api.RUTAS.update(confianza.rutas())` sobre `db.conectar('dist/albertitos.db', solo_lectura=True)`.

## Hallazgos (lo que está mal o confunde), de más grave a menos
| # | Gravedad | Dónde | Qué pasa | Propuesta (parche en texto si es fuera de mis ficheros) |
|---|---|---|---|---|
| 1 | media | `src/albertitos/console/api.py` · `curl :8100/bonus/resumen` y `/confianza/resumen` | El puente HTTP no registra las rutas. `despachar` en memoria (con `RUTAS.update`) responde 200; el servidor no. El contrato (`docs/api/bonus.md` L8-21, `docs/api/confianza.md` L12-18) pide una línea. PLAN-12: «si dan 404, apúntalo, no es un fallo tuyo». | En `api.py`, tras definir `RUTAS`, sin tocar handlers: ```python
try:
    from albertitos import bonus
    RUTAS.update(bonus.rutas())
except ImportError:
    logger.warning("sin rutas del bonus")
try:
    from albertitos import confianza
    RUTAS.update(confianza.rutas())
except ImportError:
    logger.warning("sin rutas de confianza")
``` |
| 2 | baja | `src/albertitos/confianza/rutas.py:32-39,64` · `limite=-1` / `limite=abc` | Bonus responde 400 (contrato `docs/api/bonus.md` L29). Confianza clampa (`max(1, min(n, 1000))`) o usa el defecto 50: GET 200. `banda=rara` filtra a 0 ítems, status 200 (el contrato no pide 400). | Si se quiere el mismo 400: en `_entero`, `raise`/`return 400` cuando el bruto no es un entero en rango. No lo he aplicado. |
| 3 | baja | `docs/api/ejemplos/confianza-fichero-*.json` vs `modelo.py:566` | La API siempre envía `fuentes.revisor.opinion` (`null` sin revisor). Los 5 ejemplos no tienen esa clave. `contrato_api_check.py` sale 1. El contrato escrito (`confianza.md` L67) sí menciona el campo. | Añadir `"opinion": null` dentro de `fuentes.revisor` en los 5 JSON. No son mis ficheros. |

## Lo que he cambiado yo
| Commit | Ficheros | Qué y por qué | Cómo se prueba |
|---|---|---|---|
| (este) | `scripts/contrato_api_check.py` · `tests/test_contrato_api.py` · `docs/revision/r3/probar_rutas.py` · `docs/revision/r3/tabla.json` · `docs/revision/RESUMEN-R3.md` | Comprobador de claves del contrato; sondeo ejecutado de todas las rutas | `uv run pytest -q tests/test_contrato_api.py` · `uv run python scripts/contrato_api_check.py` · `uv run python docs/revision/r3/probar_rutas.py` |

## Lo que he añadido (la cosa sencilla)
- `scripts/contrato_api_check.py`: para cada `docs/api/ejemplos/bonus-*.json` y `confianza-*.json` con `peticion`/`status`/`respuesta` (o la forma equivalente: el JSON es el cuerpo y el fichero nombra la ruta), repite la petición con `despachar` sobre esta BD y compara **claves** a todos los niveles. Ignora `nota_del_ejemplo`. Imprime faltan/sobran por fichero; sale 1 si hay diferencias.
- Uso: `uv run python scripts/contrato_api_check.py`
- Test: `tests/test_contrato_api.py` (tmp_path: clave que falta, mismas claves, `nota_del_ejemplo`, parseo, mapa de semanas ISO).
- Por qué ayuda: si alguien renombra un campo, Alejandro lo ve antes de que se le rompa la pantalla.

## make check al final
- `make check` **FALLA** fuera de mis ficheros: `uv run ruff format --check src tests scripts` → `unformatted: File would be reformatted --> scripts/enlaces_check.py:45:43` (`",;{}=\"'"`). No lo he tocado (es de R2).
- `uv run pytest -q`: `574 passed, 1 skipped, 2 deselected in 43.90s`
- `uv run pytest -q tests/test_contrato_api.py`: `5 passed in 0.03s`
- `uv run ruff check scripts/contrato_api_check.py tests/test_contrato_api.py`: `All checks passed!`

## Lo que no he podido hacer y por qué
- Dejar `make check` verde: el único fichero mal formateado es `scripts/enlaces_check.py` (R2).
- Ver `/bonus/*` y `/confianza/*` por HTTP: el puente no las registra; comprobadas con `despachar` en memoria, que es el contrato que usa Alejandro cuando añada la línea.
