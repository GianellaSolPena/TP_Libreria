## MODIFIED Requirements

### Requirement: Detalle de venta con cantidad fija de consultas
El detalle de una venta (`GET /ventas/{id}` y la respuesta de `POST /ventas`), con su cliente, sus renglones y el libro de cada renglón, SHALL resolverse con un número fijo de consultas que MUST NOT crecer con la cantidad de renglones. El libro de cada renglón MUST mostrarse aunque esté dado de baja.

#### Scenario: Dos y cuatro renglones (caso C-15)
- **WHEN** con `SQL_ECHO=true` el mismo usuario pide el detalle de una venta con 2 renglones y luego el de una venta con 4 renglones
- **THEN** la consola muestra la misma cantidad de consultas para las dos peticiones

#### Scenario: Libro dado de baja en una venta vieja
- **WHEN** se pide el detalle de una venta que incluye un libro dado de baja después de venderse
- **THEN** responde 200 con el título de ese libro en su renglón y la misma cantidad de consultas que cualquier otro detalle

#### Scenario: Evidencia entregable
- **WHEN** se revisa `parcial/evidencia/`
- **THEN** contiene el fragmento de consola con las consultas del detalle de la venta 1 de los datos iniciales (2 renglones) y de una venta de 4 renglones creada en el caso C-15 después de `python seed.py`, pedidos por el mismo usuario, sin datos de prueba de changes anteriores

### Requirement: Ninguna lectura depende de la carga perezosa
Ninguna relación de los modelos SHALL cargarse en forma diferida al accederla: si una lectura accede a una relación que no fue precargada, el sistema MUST fallar de forma explícita en lugar de emitir una consulta. Todas las respuestas verificadas en los casos de prueba MUST seguir respondiendo igual.

#### Scenario: Relación no precargada
- **WHEN** un método de lectura devuelve una entidad sin precargar una relación y algo intenta recorrerla
- **THEN** no se emite ninguna consulta diferida: si los datos no están ya en la sesión, la lectura falla con un error que identifica la relación no precargada

#### Scenario: Casos anteriores sin regresión
- **WHEN** se corren los archivos de casos C-01..C-16 de `parcial/test/`, cada uno precedido de `python seed.py`
- **THEN** cada petición responde con el código y el contenido esperados de su comentario y ninguna termina en 500
