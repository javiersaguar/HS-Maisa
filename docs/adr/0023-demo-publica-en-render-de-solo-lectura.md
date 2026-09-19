# ADR-0023 · La demo pública vive en Render y es de sólo lectura

- **Estado:** propuesto (Javier). **Fecha:** 2026-09-19 22:44 · **Dueño:** Javier · **Módulos:** console/, chat/, deploy/

## Contexto
La consola (Next, ADR-0016) está en Vercel, `https://albertitos.vercel.app`, para que el jurado del track pueda
abrirla con un enlace. Pero el puente y el chat corrían sólo en el portátil de Javier, y la consola los buscaba en
`http://127.0.0.1`. El 19/09 por la noche:
- en el portátil de Javier funcionaba sólo después de dar a Chrome 153 el permiso de «acceso a la red local»; sin
  él, «Sin conexión · Failed to fetch» (reproducido en Chromium: *Permission was denied… loopback address space*);
- en cualquier otro ordenador no hay nada en `127.0.0.1`: la consola no puede funcionar nunca.

## Alternativas consideradas
1. **Datos de ejemplo en Vercel** — funciona para todos, pero no enseña la Caja ni el chat en vivo. Se queda como
   repliegue (`NEXT_PUBLIC_USE_MOCK`), con su etiqueta.
2. **Túnel desde el portátil** (ngrok o Cloudflare) — 20 minutos, datos siempre al día. Se descarta: el portátil
   tendría que estar encendido y despierto hasta que acabe la evaluación, y la URL gratuita cambia o pone una
   página de aviso delante.
3. **(elegida) Puente y chat en Render**, dos servicios del mismo Docker, sobre una copia de sólo lectura de la BD
   publicada (`deploy/demo.db`).

## Decisión
`render.yaml` (Blueprint) con dos servicios: `albertitos-puente` (puente de lectura, **sin `--bandeja`**) y
`albertitos-chat`. Imagen `deploy/Dockerfile`: el mismo código y el mismo `uv.lock`, escuchando en
`ALBERTITOS_HOST=0.0.0.0` y en el `PORT` de Render (en el portátil, sin esas variables, todo sigue igual).
La BD sale de `scripts/exportar_demo_db.py`: copia de `dist/albertitos.db` sin `cache_llm` y sin WAL.
- **No escribe:** la bandeja está apagada. Leer una factura nueva gasta el modelo, y la comprobación del origen se
  puede falsear fuera de un navegador. La consola lo explica al jurado (`DEMO_PUBLICA` en `InvoiceDropzone.tsx`).
- **Chat con tope:** sólo acepta `https://albertitos.vercel.app`, 60 llamadas y cierre el domingo a las 14:00.
  La clave del gateway es un secreto de Render (`sync: false`), nunca va en el repo.

## Consecuencias aceptadas
- **Un tercero más con la clave del gateway** (Render, como secreto). Excepción a «secretos sólo en `.env`»,
  acotada: una clave de suscripción plana, sin coste por token, y se rota después del hackathon.
- **Datos congelados:** la demo enseña la BD del momento en que se exportó. Tras cada `make publicar` hay que
  reexportar, commit y push (Render redespliega solo).
- **Plan gratuito:** se duerme tras 15 minutos sin uso y el primer acceso tarda (medirlo). La consola lo lleva bien:
  «Sin conexión» y reintenta sola. Si molesta en la defensa, abrir el enlace unos minutos antes.
- **El contador del chat vive en el disco del contenedor:** si Render lo reinicia, vuelve a 60. El cierre de las
  14:00 sí se mantiene.
- Datos sintéticos del reto, en un repo ya público: la BD de demostración no expone nada nuevo.

## Evidencia
- Imagen construida en local (`docker build -f deploy/Dockerfile`, 4 min 13 s, 1,64 GB) y probada con
  `PORT=10000` como en Render: `/panel` 500 ficheros 438/53/9, `/ficheros`, `/traza`, `/bonus/resumen` y
  `/confianza/resumen` 200; `POST /inbox` 403; `/chat/salud` con el modelo disponible y 60 llamadas; «paga la
  factura…» se niega sin llamar al modelo.
- Tests: `tests/test_console.py` (orígenes y red local), `tests/test_chat.py` (CORS y red local).
