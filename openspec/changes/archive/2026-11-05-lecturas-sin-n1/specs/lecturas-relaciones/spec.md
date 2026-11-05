# Spec Delta

## Purpose

Garantiza que las lecturas con datos de relaciones se resuelven con carga anticipada declarada en el repositorio, con una cantidad de consultas que no crece con los datos relacionados, sin carga perezosa y sin bloquear el bucle de eventos (Ej. 8 del parcial).

## ADDED Requirements

### Requirement: Carga anticipada declarada en el repositorio
Toda respuesta que incluya datos de una relación (editorial y género del libro, autorías con su autor, perfil del cliente, cliente de la venta, renglones con su libro) SHALL obtenerlos con carga anticipada declarada dentro del método de repositorio que hace la lectura. Ni el servicio ni el router MUST declarar la precarga ni recorrer una relación que el repositorio no haya cargado.

#### Scenario: Listado de libros con editorial y género
- **WHEN** se pide `GET /libros?size=20` con `SQL_ECHO=true`
- **THEN** la consola muestra una consulta de conteo y una sola consulta de la página (libros con su editorial y su género), sin una consulta adicional por libro

#### Scenario: Detalle de libro con varios autores
- **WHEN** se pide el detalle de un libro con un autor y después el de un libro con tres autores
- **THEN** ambos detalles emiten la misma cantidad de consultas

#### Scenario: Listado de clientes con perfil
- **WHEN** el personal pide `GET /clientes` con varios clientes, algunos con perfil
- **THEN** la página se resuelve sin una consulta adicional por cliente

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
- **THEN** contiene el fragmento de consola con las consultas del detalle de una venta de 2 renglones y de otra de 4

### Requirement: Ninguna lectura depende de la carga perezosa
Ninguna relación de los modelos SHALL cargarse en forma diferida al accederla: si una lectura accede a una relación que no fue precargada, el sistema MUST fallar de forma explícita en lugar de emitir una consulta. Todas las respuestas verificadas en los casos de los changes anteriores MUST seguir respondiendo igual.

#### Scenario: Relación no precargada
- **WHEN** un método de lectura devuelve una entidad sin precargar una relación y algo intenta recorrerla
- **THEN** no se emite ninguna consulta diferida: si los datos no están ya en la sesión, la lectura falla con un error que identifica la relación no precargada

#### Scenario: Casos anteriores sin regresión
- **WHEN** se re-ejecutan los casos `.http` de autenticación, autorización, libros, clientes y ventas
- **THEN** cada petición responde con el mismo código y cuerpo esperados que antes del cambio

### Requirement: Handlers asincrónicos sin llamadas bloqueantes
Todos los handlers de rutas SHALL declararse `async def` y MUST NOT ejecutar llamadas bloqueantes en el bucle de eventos; el cálculo y la verificación de bcrypt MUST correr fuera del bucle, y el aviso del comprobante MUST esperar con una pausa asincrónica.

#### Scenario: Revisión de handlers
- **WHEN** se revisan los routers de todos los módulos
- **THEN** cada función decorada como ruta es `async def` y ninguna llama a `time.sleep`, a E/S sincrónica ni a bcrypt directamente
