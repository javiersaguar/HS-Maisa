# ADR-0024 · Clave compartida y bandeja efímera para la demo

Estado: propuesto; backend desplegado y probado; integración visual de A2 pendiente.
Responsable: Javier (A3). Fecha: 20/09/2026.

## Contexto
La demo pública era sólo de consulta. Se quiere permitir probar PDF durante la
defensa sin cambiar las decisiones ni los archivos de entrega publicados.
El tiempo disponible no permite incorporar una gestión completa de usuarios.

## Alternativas
1. Mantener consulta pública sin subidas: mínimo riesgo y marcha atrás.
2. Clave compartida en ambos servicios, con copia temporal para subidas.
3. Usuarios y permisos individuales con almacenamiento persistente: más trazabilidad,
   pero exige implementación y operación que no caben en este ciclo.

## Decisión
Elegimos la segunda para la demo privada; la primera sigue siendo el valor por defecto.
ALBERTITOS_CLAVE_DEMO se guarda únicamente en Render y viaja por HTTPS en
X-Albertitos-Clave. A1 valida la cabecera; salud y OPTIONS quedan públicos.
La misma clave protege puente y chat. No se incorpora al código del navegador.
El puente sólo abre la bandeja cuando hay clave y existe la puerta de A1.
Cada proceso copia deploy/demo.db a un directorio temporal nuevo mediante backup
SQLite. Cuarenta admisiones por arranque, configurables con ALBERTITOS_BANDEJA_MAX;
también cuentan los fallos para evitar reintentos de coste ilimitado.
El bloqueo de trabajos y el contador comparten candado.

## Consecuencias
No hay identidad individual, revocación por usuario ni persistencia de las subidas.
Quien conozca la clave puede consumir el cupo; CORS no sustituye la autenticación.
Un reinicio o varias réplicas reinician/multiplican el cupo: usar una sola instancia.
El chat conserva su instantánea separada y no ve la bandeja temporal del puente.
La consola debe avisar de que las pruebas desaparecen al reiniciar.
La marcha atrás elimina sólo la variable en ambos servicios y requiere redespliegue.
Ni la BD de producción ni JSONL/PDF de entrega se escriben desde este mecanismo.

## Evidencia
deploy/test_auth_deploy.py comprueba arranque sin clave, fallo cerrado sin puerta,
copia nueva tras reinicio, conservación byte a byte del original, cupo y errores
de configuración, rechazo sin escritura ni ejecución al agotarlo.
Los tests de A1 comprueban las rutas y cabeceras de autenticación.
Render, 20/09 09:25 Madrid: ambos servicios requieren clave; GET /panel, POST /inbox
y POST /chat sin clave o con una incorrecta responden 401. CORS permite la cabecera.
POST /inbox con e02_P002.pdf devuelve 202, y su detalle conserva 2450.00 USD,
ESCALAR y v4.R7. Es copia exacta: reutiliza los hechos, no hace extracción nueva.
Tras 21 admisiones, otro envío de 20 responde 409 y mantiene 19 plazas disponibles.
Pendiente: comprobar pantalla de A2, aviso temporal y navegación pública tras integrarla.

## Resumen para el plan (5 líneas)
La demo admite una clave compartida opcional en Render, común a puente y chat.
Sin clave conserva la consulta pública y no permite subir PDF.
Con clave el puente trabaja sobre una copia efímera de la instantánea.
Se limitan las admisiones a 40 por arranque y se avisa de la pérdida al reiniciar.
La reversión elimina la clave y redespliega; la entrega publicada permanece intacta.
