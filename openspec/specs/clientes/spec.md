# clientes Specification

## Purpose
Permite al personal (VENDEDOR, ADMIN) dar de alta, consultar y modificar clientes, cargar su perfil y ver sus ventas, con la unicidad del correo garantizada por la base (PDF Ej. 3, RN-01).

## Requirements

### Requirement: Alta de cliente
`POST /clientes` (VENDEDOR, ADMIN) SHALL recibir `nombre` y `email` y responder 201 con el cliente (`id`, `nombre`, `email`, `perfil` nulo). El contrato MUST rechazar con 422 los campos no declarados (incluido `usuario_id`), textos vacíos y un correo mal formado. Un correo ya usado por otro cliente MUST responder 409 «Ya existe un cliente con ese correo», detectado por la base y sin consulta previa, sin dejar fila.

#### Scenario: Alta correcta
- **WHEN** un VENDEDOR envía `POST /clientes` con `{"nombre":"Rosa Díaz","email":"rosa@example.com"}`
- **THEN** responde 201 con el `id` nuevo y `perfil` nulo

#### Scenario: Correo repetido
- **WHEN** se envía `POST /clientes` con el correo de un cliente existente
- **THEN** responde 409 «Ya existe un cliente con ese correo» y no se crea nada

#### Scenario: Cliente intenta dar de alta
- **WHEN** un usuario con sólo CLIENTE envía `POST /clientes`
- **THEN** responde 403

### Requirement: Consulta y listado de clientes
`GET /clientes/{id}` (VENDEDOR, ADMIN) SHALL responder 200 con el cliente y su perfil (o `perfil` nulo), o 404 si no existe. `GET /clientes` (VENDEDOR, ADMIN; ruta del TP conservada) SHALL responder el envoltorio de paginación de los clientes ordenados por `id`.

#### Scenario: Cliente con perfil
- **WHEN** el personal pide `GET /clientes/{id}` de un cliente con perfil
- **THEN** responde 200 con `perfil` con `telefono` y `direccion`

#### Scenario: Cliente inexistente
- **WHEN** el personal pide `GET /clientes/9999`
- **THEN** responde 404

### Requirement: Modificación parcial de cliente
`PATCH /clientes/{id}` (VENDEDOR, ADMIN) SHALL modificar sólo los campos enviados entre `nombre` y `email` y responder 200 con el cliente. Un campo no declarado o enviado como `null` MUST responder 422; un id inexistente MUST responder 404; un correo de otro cliente MUST responder 409 sin cambios. Si el cliente tiene usuario vinculado, enviar `email` MUST responder 409 «El correo de un cliente con cuenta no se puede cambiar» sin cambios (el correo es la credencial de login y `cliente.email` y `usuario.email` no divergen); `nombre` sí se puede cambiar.

#### Scenario: Correo de un cliente con cuenta
- **WHEN** el personal envía `PATCH /clientes/{id}` con `email` sobre un cliente que tiene usuario
- **THEN** responde 409 «El correo de un cliente con cuenta no se puede cambiar» y el cliente y su usuario quedan igual

#### Scenario: Cambio de nombre
- **WHEN** el personal envía `PATCH /clientes/1` con `{"nombre":"Lucía F."}`
- **THEN** responde 200 con el nombre nuevo y el correo sin cambios

#### Scenario: Correo de otro cliente
- **WHEN** el personal envía `PATCH /clientes/1` con el correo del cliente 2
- **THEN** responde 409 y el cliente 1 queda igual

### Requirement: Perfil del cliente
`POST /clientes/{id}/perfil` (VENDEDOR, ADMIN) SHALL crear el perfil del cliente con `telefono` y `direccion` opcionales y responder 201. Un cliente inexistente MUST responder 404; un segundo perfil para el mismo cliente MUST responder 409 «El cliente ya tiene un perfil», detectado por la base, sin dejar fila.

#### Scenario: Primer perfil
- **WHEN** el personal envía `POST /clientes/2/perfil` con `{"telefono":"351-555-0000"}` y el cliente no tiene perfil
- **THEN** responde 201

#### Scenario: Segundo perfil
- **WHEN** repite el pedido
- **THEN** responde 409 «El cliente ya tiene un perfil» y sigue habiendo un solo perfil

#### Scenario: Perfil de un cliente inexistente
- **WHEN** el personal envía `POST /clientes/9999/perfil`
- **THEN** responde 404

### Requirement: Ventas de un cliente
`GET /clientes/{id}/ventas` (VENDEDOR, ADMIN) SHALL responder el envoltorio de paginación (`page`, `size` opcionales) de las ventas del cliente ordenadas por `id`, cada una con `id`, `fecha`, `total` y su cliente. Un cliente inexistente MUST responder 404.

#### Scenario: Cliente con una venta
- **WHEN** el personal pide las ventas de un cliente que tiene una venta
- **THEN** responde 200 con `total` 1

#### Scenario: Cliente sin ventas
- **WHEN** el personal pide las ventas de un cliente sin ventas
- **THEN** responde 200 con `items` vacío, `total` 0 y `pages` 1
