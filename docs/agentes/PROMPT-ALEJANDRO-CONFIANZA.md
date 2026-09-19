# Prompt para el agente de Alejandro · la confianza en la consola (19/09, ~15:30)

Después de `git fetch && git merge origin/main` (trae `albertitos.confianza`, de K3). Se puede lanzar a la vez que el del
chat (`PROMPT-ALEJANDRO-CHAT.md`): no comparten ficheros.

```
Eres el agente de Alejandro en el repo Albertitos (HackSpain 2026, reto Maisa). Alejandro es el dueño de la consola: src/albertitos/console/ (puente HTTP de sólo lectura, sólo GET) y console-web/ (Next 16, React 19, Tailwind 4, recharts). Trabajas en SU rama: antes de nada, `git fetch && git merge origin/main` (nunca rebase) y `make check` en verde. En paralelo puede haber otro agente con el chat: NO toques sus ficheros (console-web/lib/api/chat.ts, console-web/components/chat/*, console-web/app/layout.tsx).

CONTEXTO: K3 ha hecho la métrica de confianza por factura. Para cada factura, una puntuación 0-100 con su banda (alta ≥ 80, media ≥ 50, baja < 50), las 3 razones que más pesan y el desglose por fuente (pdf, coherencia, maestro, erp, decision, politica, revisor). Mide cuánta seguridad hay de que la CLASIFICACIÓN (PAGAR/NO_PAGAR/ESCALAR) es la correcta. NO es la probabilidad de pagar ni una probabilidad calibrada: un ESCALAR puede tener confianza alta. Sólo lee y no cambia nada. Sobre la BD real: PAGAR 438 alta · NO_PAGAR 9 alta · ESCALAR 40 media y 13 baja. Las 13 bajas son las que se escalan sólo porque no se leyeron con seguridad: si el original está limpio, lo correcto sería PAGAR.

Lee antes: docs/api/confianza.md (ENTERO: el contrato manda), docs/api/ejemplos/confianza-*.json (respuestas reales), docs/adr/0014-*, src/albertitos/console/CLAUDE.md y, de console-web: lib/config.ts, lib/api/client.ts, lib/api/ficheros.ts (el patrón USE_MOCK → lib/mock, si no apiFetch + mappers), lib/types.ts, lib/routes.ts (ficheroHref), components/invoices/*, app/invoices/page.tsx, app/invoices/detalle/*, components/dashboard/*.

REGLAS:
- Tus ficheros: src/albertitos/console/api.py (sólo el registro), tests/test_console.py, console-web/lib/api/confianza.ts (nuevo), console-web/lib/types-confianza.ts (nuevo), console-web/lib/mock/confianza* (nuevo), console-web/components/confianza/* (nuevo), y lo justo en app/invoices/page.tsx, app/invoices/detalle/*, components/invoices/*, components/dashboard/* y app/pagos/* para enchufar los componentes. Nada de core/, pipeline/, extract/, rules/ ni confianza/.
- Nombres de campo EXACTOS del contrato. Todas las respuestas traen `api: 1`: si llega otro valor, avisa en consola (como hace client.ts con la versión del puente) y no rompas.
- Tiene que funcionar con USE_MOCK=true y sin red (mocks a partir de los ejemplos reales). Y si la ruta da 404 o no está registrada, la confianza sale como «—»: la consola NUNCA se cae por esto.
- Commits `console: qué y por qué`, sin mencionar IA. `make check` y `pnpm build` en verde.

TAREA 1 · Registro (si no lo hizo ya el prompt del bonus), en console/api.py, después de RUTAS:
    try:
        from albertitos import confianza
        RUTAS.update(confianza.rutas())
    except ImportError:
        logger.warning("sin rutas de confianza")
Test en tests/test_console.py: GET /confianza/resumen da 200 con la BD de prueba y trae `api == 1`.

TAREA 2 · lib/api/confianza.ts + lib/types-confianza.ts + mock: fetchConfianzaResumen(lote?), fetchConfianzaFicheros({banda, resultado, lote, limite, orden}), fetchConfianzaFichero(fileId). Tipos: ConfianzaResumen, ConfianzaItem {file_id, lote, resultado, regla, puntuacion, banda, razon_principal, razones}, ConfianzaFicha (con fuentes, dudas {id, texto, puntos, factor, aplicado, por_que}, a_favor, lecturas, causa, metodo, mismo_pdf_que, escala, version). Un hook useConfianzaDisponible(): una petición a /confianza/resumen al arrancar; si da 404 o error de red, false, y todo lo de confianza se oculta o sale como «—».

TAREA 3 · Componentes (components/confianza/):
  a. <ConfianzaChip puntuacion banda razon/> : el número en un chip del color de la banda (alta verde, media ámbar, baja rojo, con la paleta de la consola) y, al pasar el ratón, `razon_principal`. Accesible: el color nunca es la única señal (texto «alta/media/baja»).
  b. <ConfianzaTarjeta ficha/> : arriba el número y la banda y la frase LITERAL «Confianza en la clasificación, no probabilidad de pago.»; debajo `causa`, las 3 `razones` y una fila por fuente (PDF · importes (coherencia) · maestro · ERP · decisión · políticas abiertas · revisor) con su penalización y sus frases (`dudas[].texto` con los puntos aplicados; `a_favor`). Las dudas con `aplicado == 0` se enseñan atenuadas, con su `por_que` («no cuenta: es el propio motivo de escalar»). Si hay `mismo_pdf_que`, lo enlazas con ficheroHref.
  c. <ConfianzaBandas resumen/> : una barra apilada por resultado (PAGAR / NO_PAGAR / ESCALAR) con las tres bandas (recharts).

TAREA 4 · Dónde van:
  - Lista de ficheros (app/invoices): columna «Confianza» con el chip. UNA sola petición: /confianza/ficheros?limite=1000 y un Map por file_id (no pidas /fichero por fila). Un filtro rápido «Revisar primero» = /confianza/ficheros?banda=baja (ya viene de menor a mayor confianza): enséñalo como botón con el número (13) y la explicación «se escalan sólo porque no se leyeron con seguridad».
  - Detalle de la factura: la <ConfianzaTarjeta> con /confianza/fichero?file_id=… (404 si no tiene decisión: la tarjeta no se muestra).
  - Panel (/): <ConfianzaBandas> con /confianza/resumen.
  - /pagos (si ya existe, del prompt del bonus): pide /bonus/calendario?con_confianza=true y pon el chip en cada pago, sacado de `pago.confianza` (la misma ficha, o null → «—»).

CRITERIOS DE ACEPTACIÓN:
- Con la BD real y el puente: la lista muestra la columna; «Revisar primero» da 13, empezando por la de menor puntuación; el detalle de scan_006.pdf enseña 45 · baja, con «se escala sólo por dudas de lectura» y las dudas de PDF atenuadas; el panel da PAGAR 438 alta, NO_PAGAR 9 alta, ESCALAR 40 media + 13 baja.
- Con USE_MOCK=true, sin red, lo mismo con los ejemplos. Sin la ruta (404): «—» y nada se rompe.
- La frase «Confianza en la clasificación, no probabilidad de pago.» aparece en la tarjeta.
- `make check` y `pnpm build` en verde; test del registro.
```
