# Prompt · rediseño del chat «AlbertitosAI» (sábado 19/09, tras el lote 2)

Para un agente en `/home/javier/proyectos/HS-Maisa-chat`, rama `javier/chat` (hoy igual que `main`, `11c8b99`).
Incluye lo que merece la pena de las mejoras de Alejandro (`docs/agentes/chat-mejoras/`), con estas decisiones de Javier:

| Propuesta de Alejandro | Decisión | Por qué |
|---|---|---|
| Prompt de «resolución» (decisión primero, qué se contrastó, avisos traducidos, confianza en banda) | **Sí, pero compacto** | Javier quiere respuestas directas y firmes, no prosa larga |
| `DESCRIPCIONES` nuevas de buscar_facturas, traza y confianza | **Sí** | Guían el orden buscar → traza → confianza |
| `Presupuesto` por entorno del patch | **No** | El nuestro (ventana, tope, contador) ya lo cubre mejor |
| `FichaResolucion.tsx` (la verdad de la BD bajo la respuesta) | **Sí, compacta** | Separa la explicación (el modelo) de la decisión persistida: trazabilidad |
| `ChatComposer.tsx` (chips tipados) | **Sí, como atajos** | El texto libre sigue siendo lo normal |
| «Qué se consultó: buscar → traza → confianza» | **No** | Javier no quiere enseñar las herramientas |
| 429 → «Ya hay una consulta en curso» | **Sí** | Barato y claro |
| Historial sólo con turnos en vivo | Ya está | `ChatPanel.tsx`, `historial()` |

---

```
Eres el agente de diseño del chat de Albertitos. Carpeta /home/javier/proyectos/HS-Maisa-chat, rama javier/chat.
No cambies de rama, no hagas push ni merge. Commits pequeños con rutas explícitas ("chat: …", "console-web: …"),
sin mencionar IA ni Co-Authored-By. Lee primero docs/agentes/PROMPT-CHAT-DISENO.md (la tabla de decisiones) y
docs/agentes/chat-mejoras/ (las mejoras de Alejandro; si esa carpeta no existe, pídesela a Javier y empieza por
los puntos 1, 2 y 4).

PROHIBIDO: llamar al modelo (el gateway es del lote 2), leer .env, escribir en dist/albertitos.db, dist/entrega/,
data/ o src/albertitos/{core,pipeline,rules,extract}/. Prueba con las respuestas grabadas
(NEXT_PUBLIC_CHAT_GRABADAS / lib/mock/chat) y con "paga la factura X", que se niega sin modelo.
Sin dependencias nuevas: animaciones con CSS/Tailwind (keyframes en globals.css), nada de framer-motion.
Respeta prefers-reduced-motion (sin animación, mismo resultado). Nunca renderices HTML del modelo.

1 · Nombre. El chat se llama "AlbertitosAI": cabecera del panel, botón flotante (aria-label y tooltip), texto de
    ayuda, docs/api/chat.md y console-web/README.md. El prompt del sistema también: "Eres AlbertitosAI, el
    asistente de consulta de Alberto…".

2 · Sin modelo ni herramientas a la vista.
    - EstadoModelo.tsx: "En vivo" sin nombre de modelo. Nada de "respaldo" visible.
    - MensajeChat.tsx: quita la línea de modelo y la de herramientas_usadas (líneas ~111-113). Mantén la etiqueta
      de estado (grabada, degradada, sólo lectura): la honestidad de "respuesta grabada" NO se quita.
    - El backend sigue devolviendo modelo, respaldo y herramientas_usadas (los tests y la traza los usan); sólo
      se dejan de pintar, ni siquiera en un title o tooltip.

3 · Contador de llamadas restantes, bonito y animado.
    - Backend (src/albertitos/chat/agente.py y api.py): la respuesta de POST /chat añade "llamadas_restantes"
      (int o null), leída de Presupuesto.estado() tras contestar. Sin llamadas extra. Test en tests/test_chat.py.
      Documéntalo en docs/api/chat.md y en lib/api/chat.ts (campo opcional: un servidor viejo no lo manda).
    - Front: un componente ContadorLlamadas en la cabecera: pastilla con icono, número y una barra fina
      restantes/tope (el tope es llamadas_restantes de la primera salud o un nuevo campo "max_llamadas" en
      /chat/salud si lo añades con test). Color por tramo: verde > 50 %, ámbar 20-50 %, rojo < 20 %.
    - Cuando baja, el número cuenta hacia abajo suave (requestAnimationFrame, ~600 ms, ease-out) y aparece un
      "−N" que sube y se desvanece. Sin tope o sin ventana, la pastilla dice por qué (describirMotivo).

4 · Respuestas cortas, directas y firmes (backend).
    - SISTEMA: parte del de docs/agentes/chat-mejoras/SISTEMA-nuevo.txt y compáctalo:
      * primera frase: la decisión vigente (PAGAR, NO_PAGAR o ESCALAR) y el motivo principal, sin preámbulo
        ("Según los datos…", "Claro", "Buena pregunta" prohibidos);
      * luego como mucho 2-3 frases cortas con lo contrastado que importa (NIF, pedido, asiento ERP, avisos);
        si reglas_fallidas está vacío: "Ninguna regla lo impide.";
      * tope: unas 60 palabras para una factura, 90 para preguntas globales; listas, como mucho 5 elementos
        y "y N más" (con truncamiento, nunca como lista completa);
      * tono afirmativo: sin "parece", "podría", "quizá" cuando el dato viene de una herramienta; si falta un
        dato, se dice en una frase;
      * confianza sólo como banda y causa, nunca porcentaje;
      * CONSERVA intacto el párrafo de instruccion_en_pdf de C1 (B5) y todas las defensas de inyección; los
        tests de test_chat.py que miran esas frases tienen que seguir pasando.
    - herramientas.py: DESCRIPCIONES de buscar_facturas, traza y confianza con los textos de Alejandro.
    - Test: SISTEMA contiene la regla de brevedad y sigue conteniendo las frases de B5.
    - Front: si una respuesta pasa de ~5 líneas, se corta con degradado y "Ver más" (no es la solución, es la red).

5 · Animaciones leves (todas ≤ 250 ms salvo el contador, y apagadas con prefers-reduced-motion).
    - Mensaje nuevo: fade + translateY(6px) → 0. El del asistente entra un pelín después del indicador.
    - Mientras piensa: tres puntos que laten en una burbuja, en lugar del spinner.
    - Panel: se abre deslizando desde la derecha con fade; el botón flotante hace un pulso suave una sola vez
      la primera vez que el chat está en vivo.
    - Citas y ficha: aparecen con un stagger de 40 ms.

6 · Ficha de resolución (de Alejandro, compacta). Copia consola/FichaResolucion.tsx a components/chat/.
    - Sólo para la PRIMERA cita: ResultadoBadge, proveedor, importe, motivo principal y enlace a la traza,
      releído de GET /ficheros/:id (la verdad de la BD, no la prosa). El resto de citas, chips-enlace; con 20,
      "puede haber más".
    - hooks/useConfianza.ts, ConfianzaChip y los tokens text-ink/border-line están en la rama de Alejandro y NO
      en main: si no los tienes, sin línea de confianza y con los colores actuales. No traigas su rama.

7 · Composer. Copia consola/ChatComposer.tsx, pero el textarea libre es lo principal: los chips (Factura · Pedido ·
    Proveedor · Semana · Confianza) van encima como atajos que rellenan la pregunta y enseñan "Se preguntará:
    «…»". Enter envía, Shift+Enter salta línea, el textarea crece hasta 4 líneas, contador de caracteres sólo
    cerca de MAX_MENSAJE. Un 429 sale como "Ya hay una consulta en curso; espera a que termine".

8 · Mejoras pequeñas que suman en la defensa:
    - estado vacío con 3-4 preguntas sugeridas (las de SUGERENCIAS) como chips;
    - botón "Copiar" en cada respuesta y "Nueva conversación" en la cabecera (vacía el historial);
    - en móvil / ventana estrecha el panel ocupa el ancho completo;
    - foco visible, aria-live="polite" en la lista de mensajes, Escape cierra (ya está).

9 · Cierre.
    - uv run pytest tests/test_chat.py -q · make check · en console-web: pnpm lint, pnpm exec tsc --noEmit y
      pnpm build, todo en verde.
    - Prueba visual con respuestas grabadas: capturas del panel vacío, respondiendo, con la ficha y con el contador
      bajando (Playwright si lo tienes; si no, descríbelo).
    - PARTE.md: tu sección con lo hecho, lo descartado y por qué, y los comandos con su salida. Una línea en
      BITACORA.md con la hora real (date).
```
