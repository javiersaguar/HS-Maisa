# PLAN-15 · cerrar la demo con una clave y abrir las subidas desde Vercel · domingo 20/09, 08:00 → 10:15

**Qué queremos.** Que `https://albertitos.vercel.app` deje de ser una web abierta: pide una clave, y con ella se
pueden **subir facturas** desde cualquier ordenador. Hoy la pública es de sólo lectura porque cualquiera con el
enlace podría gastar el modelo.

**Qué NO tocamos.** La entrega está publicada (`7bde01b`: 540 líneas + el PDF) y el cierre es a las **11:00**. Nada
de esto toca `outcomes*.jsonl`, `rules/`, `pipeline/`, `core/`, `extract/`, `data/` ni `docs/plan/`. Si algo sale
mal, **se borra la clave del entorno en Render y en 30 segundos volvemos al estado de ahora**.

## El contrato, fijado antes de empezar (no se negocia por el camino)
1. **Una clave compartida, no usuarios.** Variable `ALBERTITOS_CLAVE_DEMO`, secreto de Render. Nunca en el repo,
   nunca en Vercel, nunca en un `NEXT_PUBLIC_*`.
2. **Cabecera** `X-Albertitos-Clave: <clave>` en cada petición.
3. **Interruptor:** si el servidor **no** tiene `ALBERTITOS_CLAVE_DEMO`, no se exige nada y todo funciona como hoy.
   Ése es el repliegue.
4. **Siempre abiertos, sin clave:** `GET /salud` (puente) y `GET /chat/salud`. Los dos añaden un campo nuevo:
   `"requiere_clave": true|false`. Es lo que permite a la consola saber si tiene que pedirla.
5. **Fallo:** `401` con cuerpo `{"error": "clave incorrecta o ausente"}`. Nunca se dice si la clave existe o no.
6. **Comparación** con `secrets.compare_digest`, no con `==`.
7. **CORS:** `X-Albertitos-Clave` tiene que estar en `Access-Control-Allow-Headers`, o el navegador ni la manda.
8. **Subidas públicas:** la bandeja sólo se activa **si hay clave configurada**. Sin clave, `POST /inbox` sigue
   dando 409 como hoy.

## Reparto: quién puede tocar qué
| Agente | Rama | Ficheros suyos, y de nadie más |
|---|---|---|
| **A1 · la puerta** | `javier/auth-backend` | `src/albertitos/console/api.py` · `src/albertitos/chat/api.py` · `src/albertitos/console/lecturas.py` (sólo `salud`) · `tests/test_console.py` · `tests/test_chat.py` |
| **A2 · la consola** | `javier/auth-consola` | `console-web/lib/api/client.ts` · `console-web/lib/api/chat.ts` · `console-web/components/auth/*` (nuevo) · `console-web/app/layout.tsx` · `console-web/lib/config.ts` |
| **A3 · despliegue** | `javier/auth-deploy` | `render.yaml` · `deploy/*` · `src/albertitos/console/bandeja.py` · `docs/api/*` · `docs/adr/0024-clave-en-la-demo-publica.md` (nuevo) |

`docs/agentes/BITACORA.md` es de todos, sólo añadiendo al final. Nadie hace `git add -A`: rutas explícitas.

## A1 · la puerta del backend
**Objetivo:** que el puente y el chat exijan la clave, sin romper nada cuando no la hay.

1. **Función compartida.** En `console/api.py`:
   ```python
   def clave_exigida() -> str:
       return os.environ.get("ALBERTITOS_CLAVE_DEMO", "").strip()

   def clave_ok(cabecera: str | None) -> bool:
       esperada = clave_exigida()
       return not esperada or secrets.compare_digest(cabecera or "", esperada)
   ```
   El chat la importa de ahí (`from albertitos.console.api import clave_ok`) **o** la duplica en tres líneas si
   prefieres no acoplar los dos módulos; las dos opciones valen, pero dilo en el commit.
2. **Dónde se comprueba.** En el puente, en `do_GET` y `do_POST`, **después** de resolver la ruta y **antes** de
   tocar la BD; se salta para `/`, `/salud` y `OPTIONS`. En el chat, igual: se salta para `/chat/salud` y `OPTIONS`.
3. **Respuesta:** `401` y `{"error": "clave incorrecta o ausente"}`, con las cabeceras CORS que ya se mandan (si no,
   el navegador enseña un error de red en vez del 401).
4. **CORS:** añade `X-Albertitos-Clave` a `Access-Control-Allow-Headers` en los dos (`_CORS` en el puente y el
   `send_header` del chat).
5. **`/salud`:** añade `"requiere_clave": bool(clave_exigida())`. En el puente va en `lecturas.salud`; en el chat,
   en el diccionario que ya construye. **No subas `API_VERSION`**: es un campo nuevo, no un cambio de contrato.
6. **Tests** (los tuyos, en `tests/test_console.py` y `tests/test_chat.py`):
   - sin variable: todo responde como hoy y `requiere_clave` es `false`;
   - con variable: `/panel` sin cabecera → 401; con cabecera mala → 401; con la buena → 200;
   - `/salud` y `/chat/salud` responden 200 **sin** cabecera, y dicen `requiere_clave: true`;
   - el 401 lleva `Access-Control-Allow-Origin` (si no, el navegador no lo ve);
   - `POST /inbox` sin clave → 401 (no 403 de origen: la clave se comprueba antes).
7. **Cierre:** `make check` verde, commit, push, PR, y en la bitácora: «A1 listo, contrato en `main`» para que A2
   sepa que puede integrar contra el servidor de verdad.

## A2 · la consola pide la clave
**Objetivo:** que un jurado abra el enlace, escriba la clave y trabaje; y que nadie tenga que compilar nada.

1. **Al cargar:** `GET /salud` (que no pide clave). Si `requiere_clave` es `false`, la consola funciona como hoy y
   no se enseña nada. Si es `true` y no hay clave guardada, se enseña la pantalla de clave.
2. **Pantalla** (`components/auth/PuertaClave.tsx`): el nombre del producto, una frase («esta demo es privada:
   pide la clave al equipo»), un campo de tipo `password`, botón «Entrar» y un sitio para el error. Enter envía.
   Sin librerías nuevas; los colores y los componentes que ya existen.
3. **Dónde se guarda:** `sessionStorage` (se borra al cerrar la pestaña), nunca `localStorage`, nunca una cookie.
   Envuelve los accesos en `try/catch`: en navegación privada puede lanzar.
4. **Dónde se manda:** en `lib/api/client.ts`, dentro de `apiFetch`, junto a las cabeceras que ya pone (ahí pasan
   **todas** las llamadas, subidas incluidas). Y en `lib/api/chat.ts`, que usa su propio `fetch`.
5. **Si algo devuelve 401:** se borra la clave guardada y se vuelve a enseñar la pantalla, sin recargar y sin
   perder la página en la que estaba. `ApiError.isUnauthorized` ya distingue 401.
6. **Salir:** un enlace pequeño en la barra lateral, «Salir», que borra la clave y vuelve a la pantalla.
7. **Lo que no se hace:** nada de variables nuevas en Vercel, nada de meter la clave en el build, nada de
   `NEXT_PUBLIC_CLAVE`. La clave la escribe la persona.
8. **Cierre:** `npx tsc --noEmit` y `npx pnpm build` en verde; prueba a mano contra tu puente local arrancado con
   `ALBERTITOS_CLAVE_DEMO=prueba123`: sin clave no se ve nada, con la buena sí, y con una mala lo dice.

## A3 · despliegue y subidas en la pública
**Objetivo:** que la demo pública tenga clave y acepte facturas, con límites y diciendo lo que es.

1. **`render.yaml`:** añade a los dos servicios `ALBERTITOS_CLAVE_DEMO` con `sync: false` (se pega a mano en el
   panel). Al puente, arráncalo con `--bandeja` **sólo si hay clave**: como el `dockerCommand` es fijo, hazlo con
   un arranque condicional (un `sh -c` que mire la variable) o con una bandera nueva en
   `console/api.py`… **que es de A1**: si la necesitas, pídesela por la bitácora. Alternativa sin tocar nada suyo:
   dejar `--bandeja` siempre y que la bandeja compruebe la clave, que ya hace A1 en `POST /inbox`.
2. **La BD de la bandeja en Render es efímera:** cada reinicio la rehace desde `deploy/demo.db`. Que la pantalla
   lo diga («espacio de pruebas: lo que subas se borra cuando el servidor se reinicia»). El texto va en
   `console-web`, que es de A2: pídeselo en la bitácora, no lo toques.
3. **Límites:** los que ya hay (20 ficheros, 10 MB) y, además, un tope de facturas por arranque para que nadie
   agote el gateway: una variable `ALBERTITOS_BANDEJA_MAX` leída en `bandeja.py` (fichero tuyo), por defecto 40.
   Al pasarse: `409` con un mensaje claro.
4. **Prueba de verdad**, no en local: con el despliegue en marcha, subir `data/lote2/facturas/e02_P002.pdf` con
   `curl` y la cabecera de la clave, y comprobar que sale ESCALAR por la regla de moneda.
5. **ADR-0024** (`docs/adr/0024-clave-en-la-demo-publica.md`): por qué una clave compartida y no usuarios; qué
   protege de verdad (el gasto del modelo y que nadie escriba) y qué no (no es autenticación seria); el disco
   efímero; y el repliegue de un solo paso. Añádelo al índice `docs/adr/README.md`.
6. **`deploy/README.md`:** cómo se pone la clave, cómo se rota y cómo se apaga todo esto.

## Horario y puntos de encuentro
| Hora | Qué |
|---|---|
| 08:00 | Arrancan los tres. A1 y A2 trabajan contra el contrato de arriba, sin esperarse |
| **09:00** | **A1 mergea primero.** A2 y A3 traen `main` (`git merge origin/main`) y siguen |
| 09:45 | A2 y A3 mergean. Prueba conjunta: abrir Vercel **desde el móvil**, meter la clave, subir una factura |
| **10:15** | Decisión: si no está redondo, se borra `ALBERTITOS_CLAVE_DEMO` en Render y vuelve el estado de hoy |
| 11:00 | Cierre de la entrega. **Nada de esto la toca** |

## Riesgos, dichos claro
- **Una clave compartida no es un sistema de usuarios.** Sirve para que nadie ajeno gaste el modelo ni escriba.
  En la defensa hay que contarlo así, no venderlo como seguridad.
- **Lo que se suba a la pública se pierde** cuando Render reinicia. Es una demo.
- **Cuesta dos horas de gente** que podrían ir al ensayo de la defensa, que son 100 puntos. Si a las 09:45 no
  está, se para y se apaga: nadie se enfada, era un extra.
