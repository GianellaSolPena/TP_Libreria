# autorizacion Specification

## Purpose

Decide quién puede usar cada ruta: distingue 401 (no se sabe quién es) de 403 (se sabe y no puede), autoriza con los roles vigentes en la base en cada petición, bloquea a quien tiene el cambio de contraseña pendiente y reparte las rutas en un grupo abierto y uno protegido según la matriz de permisos del PDF (Ej. 5, RN-04, RN-06).

## Requirements

### Requirement: 401 contra 403
Toda ruta que pide sesión SHALL responder 401 cuando no puede identificar al usuario (sin cookie `access_token`, token inválido o vencido, usuario inexistente o inactivo, o sólo `Authorization: Bearer`) y 403 cuando el usuario está identificado pero no puede usar la ruta (rol vigente insuficiente, cambio de contraseña pendiente o, en `GET /ventas/{id}`, una venta que no es suya ni es personal). El 401 MUST evaluarse antes que cualquier 403, y ninguno de los dos MUST ejecutar la operación pedida.

#### Scenario: Sin sesión en una ruta protegida
- **WHEN** se envía `POST /libros` sin cookie
- **THEN** responde 401

#### Scenario: Vendedor que crea un libro
- **WHEN** un usuario con rol vigente VENDEDOR envía `POST /libros` con su cookie
- **THEN** responde 403 y no se crea ningún libro

#### Scenario: Usuario desactivado con token vigente
- **WHEN** la cookie trae un token válido de un usuario con `activo = false`
- **THEN** responde 401

#### Scenario: Parámetro no entero con sesión
- **WHEN** un ADMIN con sesión pide `PATCH /editoriales/abc`
- **THEN** responde 422 sin ejecutar el handler

### Requirement: Roles vigentes leídos de la base en cada petición
La autorización SHALL decidirse con los roles vigentes del usuario en `asignacion_rol` leídos en cada petición: filas con `revocada_en` nulo y `vence_en` nulo o posterior al momento de la petición. Los roles que trae el token MUST ser sólo informativos y no MUST conceder ni negar permisos. La lectura MUST usar la misma sesión de base que la operación de la petición: una petición autenticada MUST NOT abrir una segunda sesión para su operación.

#### Scenario: Revocar un rol con la sesión abierta
- **WHEN** un VENDEDOR con sesión abierta pide `GET /ventas` con éxito (200), un ADMIN le revoca VENDEDOR y el vendedor repite el pedido con la misma cookie
- **THEN** el segundo pedido responde 403 sin esperar a que el token venza

#### Scenario: Diferencia visible en la sesión
- **WHEN** tras la revocación el vendedor pide `GET /auth/yo` con la misma cookie
- **THEN** responde 200 con `roles_vigentes` sin VENDEDOR y `roles_token` todavía con VENDEDOR

#### Scenario: Rol vencido
- **WHEN** un usuario tiene VENDEDOR con `vence_en` ya pasado y pide `GET /ventas`
- **THEN** responde 403

#### Scenario: Una sola sesión por petición autenticada
- **WHEN** se revisan las dependencias de cualquier ruta de libros, clientes o ventas
- **THEN** la autorización y el Unit of Work de la operación reciben la misma sesión de la petición

### Requirement: Cambio obligatorio de contraseña
Mientras un usuario tenga `debe_cambiar_password = true`, toda ruta del grupo protegido SHALL responder 403 con un mensaje propio que indique que debe cambiar la contraseña; las rutas de `/auth` y las que no piden sesión MUST seguir funcionando. El valor MUST leerse de la base en cada petición, de modo que tras el cambio la misma cookie sirva sin iniciar sesión de nuevo.

#### Scenario: Bloqueado salvo /auth
- **WHEN** un VENDEDOR con cambio pendiente pide `GET /ventas` con su cookie
- **THEN** responde 403 con el mensaje del cambio obligatorio

#### Scenario: /auth sigue disponible
- **WHEN** el mismo usuario pide `GET /auth/yo` y luego `POST /auth/cambiar-password` con datos válidos
- **THEN** responde 200 en ambos y `debe_cambiar_password` queda en `false`

#### Scenario: La misma cookie sirve después del cambio
- **WHEN** tras cambiar la contraseña repite `GET /ventas` con la misma cookie
- **THEN** responde 200

#### Scenario: Rutas públicas con cambio pendiente
- **WHEN** el usuario con cambio pendiente pide `GET /libros`
- **THEN** responde 200

#### Scenario: Mis ventas con cambio pendiente
- **WHEN** un usuario con cambio pendiente pide `GET /mis-ventas` o `GET /ventas/{id}`
- **THEN** responde 403 con el mensaje del cambio obligatorio

### Requirement: Dos grupos de rutas
La aplicación SHALL repartir sus rutas en un grupo abierto y uno protegido. El grupo abierto MUST contener `GET /health/live`, `GET /health/ready`, todas las rutas de `/auth` y las consultas públicas del catálogo (`GET /libros`, `GET /libros/{id}`, `GET /editoriales`, `GET /generos`, `GET /autores`, `GET /{editoriales,generos,autores}/{id}` y `GET /{editoriales,generos,autores}/{id}/libros`); ninguna de ellas MUST exigir sesión salvo `GET /auth/yo` y `POST /auth/cambiar-password`, que piden sesión pero no llevan el control del cambio obligatorio. Toda otra ruta, incluidas `GET /libros/{id}/movimientos`, `GET /ventas/{id}` y `GET /mis-ventas`, MUST pertenecer al grupo protegido, que lleva el control del cambio obligatorio declarado una sola vez para todo el grupo. Las rutas de libros, clientes y ventas MUST declararse sin barra final.

#### Scenario: Catálogo público sin sesión
- **WHEN** se pide `GET /editoriales` sin cookie
- **THEN** responde 200

#### Scenario: Libros sin barra final
- **WHEN** se pide `GET /libros` sin cookie
- **THEN** responde 200 directamente, sin redirección

#### Scenario: Health sin sesión
- **WHEN** se pide `GET /health/live` sin cookie
- **THEN** responde 200

#### Scenario: /auth/yo pide sesión
- **WHEN** se pide `GET /auth/yo` sin cookie
- **THEN** responde 401

### Requirement: Matriz de permisos
Las rutas protegidas SHALL exigir los roles vigentes de la matriz de `knowledge-base/03`: ADMIN para `POST /editoriales`, `/generos`, `/autores`, `PATCH /editoriales/{id}`, `/generos/{id}`, `/autores/{id}`, `POST /libros`, `PATCH /libros/{id}`, `DELETE /libros/{id}`, `POST /libros/{id}/reponer`, `GET /libros/{id}/movimientos` y todas las rutas de `/usuarios` y `/eventos`; VENDEDOR o ADMIN para todas las rutas de `/clientes`, `POST /ventas` y `GET /ventas`. Un usuario sin ninguno de los roles exigidos MUST recibir 403. `GET /ventas/{id}` y `GET /mis-ventas` MUST pedir sólo sesión, sin exigir rol: en `GET /ventas/{id}` la operación decide si el usuario es personal o dueño de la venta (si no, 403), y `GET /mis-ventas` devuelve sólo lo propio.

#### Scenario: Cliente en una ruta de personal
- **WHEN** un usuario con sólo CLIENTE pide `POST /clientes` con su cookie
- **THEN** responde 403

#### Scenario: Vendedor en una ruta de ADMIN
- **WHEN** un VENDEDOR pide `GET /eventos` o `POST /libros/1/reponer` con su cookie
- **THEN** responde 403

#### Scenario: ADMIN también puede lo del vendedor
- **WHEN** un ADMIN pide `GET /ventas` con su cookie
- **THEN** responde 200

#### Scenario: Detalle de venta sin rol de personal
- **WHEN** una usuaria con sólo CLIENTE pide `GET /ventas/{id}` de una venta propia
- **THEN** responde 200, no 403
