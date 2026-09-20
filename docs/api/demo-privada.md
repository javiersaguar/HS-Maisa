# Acceso a la demo y bandeja temporal

Con ALBERTITOS_CLAVE_DEMO configurada, enviar X-Albertitos-Clave en las consultas
al puente y al chat, incluido POST /inbox. Falta de clave o valor incorrecto: 401
con error «clave incorrecta o ausente». Salud, raíz y OPTIONS siguen públicos.
La salud añade requiere_clave para que el cliente sepa si debe pedirla.

GET /inbox conserva sus campos y añade:
- efimera: booleano; mostrar el aviso de espacio de pruebas si es true.
- limite_arranque: máximo de admisiones (40 por defecto).
- recibidos_arranque: admisiones reservadas, incluidos fallos posteriores.
- restantes_arranque: plazas todavía disponibles.

El servidor rechaza con 409 una petición que sobrepase el cupo completo, sin
escribir sus PDF ni ejecutar la CLI. No admite parcialmente un envío.
Los límites de 20 PDF por petición y 10 MB por PDF siguen vigentes.

La bandeja de Render desaparece de la vista al reiniciar y no se comparte con
el proceso del chat. Nunca sustituye la entrega ni la instantánea de origen.
Despliegue, rotación, marcha atrás y pruebas: ../../deploy/README.md.
