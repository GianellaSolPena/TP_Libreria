# gestion-roles Specification

## Purpose

Permite al administrador dar de alta personal con contraseña provisoria y gestionar los roles con vigencia de cada usuario (asignar con vencimiento opcional, consultar y revocar sin borrar), garantizando una sola asignación abierta por rol (RN-03) y la autoprotección del administrador (RN-05).

## Requirements

### Requirement: Alta de personal
`POST /usuarios` (sólo ADMIN) SHALL crear un usuario de personal con `email`, `nombre`, una contraseña provisoria y un `rol` de personal (`VENDEDOR` o `ADMIN`), con `debe_cambiar_password = true`, y responder 201 con el usuario sin `password_hash`. El usuario, su asignación de rol y el evento de seguridad MUST quedar los tres o ninguno. Un correo ya usado MUST responder 409 con mensaje propio, garantizado por la unicidad de la base. El contrato MUST rechazar con 422 campos no declarados, un rol que no sea de personal y contraseñas de más de 72 bytes.

#### Scenario: Alta correcta
- **WHEN** un ADMIN envía `POST /usuarios` con `{"email": "caja@example.com", "nombre": "Caja", "password": "<provisoria>", "rol": "VENDEDOR"}`
- **THEN** responde 201 con `debe_cambiar_password = true`, sin `password_hash`, y existen el usuario, su asignación VENDEDOR abierta y una línea en `evento_seguridad`

#### Scenario: Correo repetido
- **WHEN** un ADMIN envía `POST /usuarios` con el correo de un usuario existente
- **THEN** responde 409 con mensaje propio y no queda ninguna asignación ni evento nuevos

#### Scenario: Rol no permitido
- **WHEN** el cuerpo trae `"rol": "CLIENTE"` o un campo no declarado
- **THEN** responde 422

#### Scenario: El personal nuevo debe cambiar la contraseña
- **WHEN** el usuario recién creado inicia sesión con la contraseña provisoria
- **THEN** el login responde 200 con `debe_cambiar_password = true` y las rutas protegidas le responden 403 hasta que la cambie

### Requirement: Consulta de roles de un usuario
`GET /usuarios/{id}/roles` (sólo ADMIN) SHALL responder 200 con todas las asignaciones del usuario, incluidas las revocadas y las vencidas, cada una con `rol`, `desde`, `vence_en`, `revocada_en`, `otorgada_por` y si está vigente; un usuario inexistente MUST responder 404.

#### Scenario: Historial con fila revocada
- **WHEN** a un usuario se le revocó VENDEDOR y un ADMIN pide sus roles
- **THEN** la respuesta incluye la asignación VENDEDOR con `revocada_en` informado y marcada como no vigente

#### Scenario: Usuario inexistente
- **WHEN** se piden los roles de un id que no existe
- **THEN** responde 404

### Requirement: Asignación de rol con vencimiento opcional
`POST /usuarios/{id}/roles` (sólo ADMIN) SHALL abrir una asignación del `rol` pedido para el usuario, con `vence_en` opcional, registrando quién la otorgó, y responder 201 con la asignación. `vence_en`, si viene, MUST tener zona horaria y ser futuro: sin zona o en el pasado MUST responder 422 (no 409). Un usuario inexistente MUST responder 404.

#### Scenario: Asignación sin vencimiento
- **WHEN** un ADMIN asigna VENDEDOR a un usuario que no lo tiene
- **THEN** responde 201 con `vence_en` nulo y `otorgada_por` igual al id del ADMIN

#### Scenario: Vencimiento sin zona
- **WHEN** se envía `{"rol": "VENDEDOR", "vence_en": "2030-01-01T00:00:00"}`
- **THEN** responde 422

#### Scenario: Vencimiento en el pasado
- **WHEN** se envía `{"rol": "VENDEDOR", "vence_en": "2020-01-01T00:00:00Z"}`
- **THEN** responde 422

#### Scenario: Usuario inexistente
- **WHEN** se asigna un rol a un id que no existe
- **THEN** responde 404

### Requirement: Una asignación abierta por rol
Un usuario SHALL tener a lo sumo una asignación abierta (no revocada) por rol (RN-03). Asignar un rol que el usuario ya tiene abierto y vigente MUST responder 409 con mensaje propio sin escribir nada, garantizado por la base. Asignar un rol cuya asignación abierta ya venció MUST cerrar esa fila y abrir una nueva, en la misma operación.

#### Scenario: Segunda asignación abierta
- **WHEN** un ADMIN asigna VENDEDOR a un usuario que ya lo tiene vigente
- **THEN** responde 409 y no queda ninguna fila ni evento nuevos

#### Scenario: Reasignar un rol vencido
- **WHEN** un usuario tiene VENDEDOR abierto con `vence_en` pasado y un ADMIN se lo asigna de nuevo
- **THEN** responde 201, la fila anterior queda con `revocada_en` informado y existe una fila nueva abierta y vigente

### Requirement: Revocación sin borrar
`DELETE /usuarios/{id}/roles/{rol}` (sólo ADMIN) SHALL cerrar la asignación vigente de ese rol escribiendo `revocada_en` y responder 200 con la asignación cerrada; la fila MUST conservarse. Un usuario inexistente o sin ese rol vigente MUST responder 404; un `rol` fuera de `ADMIN`, `VENDEDOR`, `CLIENTE` MUST responder 422.

#### Scenario: Revocación correcta
- **WHEN** un ADMIN revoca VENDEDOR a un vendedor
- **THEN** responde 200 y la fila sigue en `asignacion_rol` con `revocada_en` informado

#### Scenario: Rol no vigente
- **WHEN** se revoca un rol que el usuario no tiene vigente
- **THEN** responde 404

### Requirement: Autoprotección del administrador
Un administrador SHALL NOT poder revocarse su propio rol ADMIN, y ninguna revocación MUST dejar el sistema sin administradores vigentes (RN-05); en ambos casos responde 409 con mensaje propio y no escribe nada. La comprobación MUST seguir siendo correcta cuando dos revocaciones de ADMIN ocurren a la vez.

#### Scenario: El administrador no se revoca su ADMIN
- **WHEN** `admin@example.com` envía `DELETE /usuarios/<su id>/roles/ADMIN`
- **THEN** responde 409 y su asignación ADMIN sigue vigente

#### Scenario: Revocación cruzada simultánea
- **WHEN** hay exactamente dos ADMIN vigentes y cada uno revoca el ADMIN del otro al mismo tiempo
- **THEN** una revocación responde 200, la otra 409, y queda un ADMIN vigente

#### Scenario: Revocación de otro ADMIN con más administradores
- **WHEN** hay dos ADMIN vigentes y uno revoca el ADMIN del otro
- **THEN** responde 200
