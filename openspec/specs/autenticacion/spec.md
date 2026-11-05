# autenticacion Specification

## Purpose
Permite que clientes y personal tengan una cuenta con contraseña: auto-registro, inicio y cierre de sesión con un token que viaja sólo en una cookie, consulta del usuario de la sesión y cambio de contraseña, protegiendo las contraseñas con bcrypt.

## Requirements

### Requirement: Auto-registro atómico
`POST /auth/registro` SHALL crear, en una sola transacción, el usuario (con la contraseña hasheada), su rol CLIENTE vigente y su ficha de cliente con el nombre y el correo del cuerpo, y responder 201 con el usuario creado. O quedan las tres filas, o ninguna (RN-02). El registro MUST NOT escribir el token ni iniciar sesión.

#### Scenario: Registro exitoso
- **WHEN** un visitante envía `{"email": "nuevo.cliente@example.com", "nombre": "Nuevo Cliente", "password": "secreta123"}`
- **THEN** responde 201 con el id, el correo, el nombre, `activo` y `debe_cambiar_password=false`, sin `password_hash`
- **AND** existen el usuario, una asignación CLIENTE abierta y un cliente con ese correo y `usuario_id` del nuevo usuario

#### Scenario: Correo ya usado por un usuario
- **WHEN** se registra un correo que ya tiene un usuario
- **THEN** responde 409 con un mensaje propio, sin texto de la base
- **AND** no queda ninguna fila nueva en `usuario`, `asignacion_rol` ni `cliente`

#### Scenario: Correo ya usado por un cliente sin usuario
- **WHEN** se registra el correo de un cliente existente que no tiene usuario
- **THEN** responde 409 con un mensaje propio, la ficha existente no se modifica (no se apropia de ella) y no queda ningún usuario ni asignación nuevos

### Requirement: Contrato de entrada de autenticación
Los cuerpos de `/auth` SHALL rechazar con 422 los campos no declarados, y en particular el registro MUST NOT aceptar un rol. Ninguna respuesta SHALL incluir `password_hash`.

#### Scenario: Registro con rol
- **WHEN** el cuerpo del registro incluye `"rol": "ADMIN"`
- **THEN** responde 422 y no se crea nada

#### Scenario: Campos faltantes
- **WHEN** el login llega sin `password`
- **THEN** responde 422

### Requirement: Límite de 72 bytes en contraseñas
Todo campo de contraseña que se pasa a bcrypt (la del registro, la del login, la actual y la nueva del cambio) SHALL aceptar entre 1 y 72 bytes en UTF-8; si excede, MUST responder 422 y nunca 500. El límite se mide en bytes, no en caracteres.

#### Scenario: Contraseña de 73 bytes ASCII
- **WHEN** se registra con una contraseña de 73 caracteres ASCII
- **THEN** responde 422

#### Scenario: Caracteres de dos bytes
- **WHEN** el login llega con una contraseña de 37 «ñ» (74 bytes, 37 caracteres)
- **THEN** responde 422 sin consultar la base

#### Scenario: Justo 72 bytes
- **WHEN** se registra con una contraseña de 36 «ñ» (72 bytes)
- **THEN** el contrato la acepta

### Requirement: Contraseñas con bcrypt de costo configurable
Las contraseñas SHALL guardarse sólo como hash bcrypt con el costo definido en la configuración. Toda operación bcrypt MUST ejecutarse fuera del bucle de eventos y con un límite de operaciones simultáneas, y el hash de una contraseña nueva MUST calcularse antes de abrir la transacción que lo guarda.

#### Scenario: Costo tomado de la configuración
- **WHEN** se arranca con `BCRYPT_ROUNDS=10` y se registra un usuario
- **THEN** el `password_hash` guardado indica costo 10 (prefijo `$2b$10$`)

#### Scenario: Servidor atiende durante el hash
- **WHEN** varios logins se procesan a la vez
- **THEN** `GET /health/live` sigue respondiendo sin esperar a que terminen

### Requirement: Login con token en cookie
`POST /auth/login` con credenciales correctas de un usuario activo SHALL responder 200 con `{"mensaje": "Sesión iniciada", "debe_cambiar_password": <bool>, "expira_en_segundos": <duración>}` y una cookie `access_token` con `HttpOnly`, `SameSite=Lax`, `Max-Age` igual a la duración del token y `Secure` según la configuración. El cuerpo MUST NOT incluir el token.

#### Scenario: Login correcto
- **WHEN** un usuario registrado inicia sesión con su contraseña
- **THEN** responde 200 con el cuerpo indicado y `expira_en_segundos` igual a `ACCESS_TOKEN_EXPIRE_SECONDS`
- **AND** el encabezado `Set-Cookie` trae `access_token=...; HttpOnly; Max-Age=<duración>; Path=/; SameSite=lax`, sin `Secure` cuando `COOKIE_SECURE=false`

#### Scenario: Cookie segura configurable
- **WHEN** se arranca con `COOKIE_SECURE=true` y se inicia sesión
- **THEN** la cookie incluye el atributo `Secure`

#### Scenario: Usuario con cambio pendiente
- **WHEN** inicia sesión un usuario con `debe_cambiar_password=true`
- **THEN** responde 200 con `debe_cambiar_password: true`

### Requirement: Contenido del token
El token SHALL ser un JWT firmado con la clave de la configuración que contiene `sub` (id del usuario), `exp` (emisión + duración configurada) y `roles` (los roles vigentes al emitirlo). Los roles del token MUST NOT usarse para decidir permisos.

#### Scenario: Roles vigentes al emitir
- **WHEN** un usuario con rol CLIENTE vigente inicia sesión
- **THEN** el token decodificado tiene `sub` con su id, `exp` en el futuro y `roles` igual a `["CLIENTE"]`

### Requirement: Credenciales incorrectas indistinguibles
Ante un correo inexistente, una contraseña incorrecta o un usuario inactivo, el login SHALL responder 401 con el mismo cuerpo, y SHALL tardar lo mismo porque siempre ejecuta una verificación bcrypt (contra el hash del usuario o contra un hash ficticio calculado al arrancar) (RN-08).

#### Scenario: Correo existente con contraseña mala
- **WHEN** se inicia sesión con un correo registrado y una contraseña incorrecta
- **THEN** responde 401 `{"detail": "Correo o contraseña incorrectos"}` sin cookie

#### Scenario: Correo inexistente
- **WHEN** se inicia sesión con un correo que no existe
- **THEN** responde 401 con exactamente el mismo cuerpo y un tiempo de respuesta parecido al del caso anterior

### Requirement: Cierre de sesión
`POST /auth/logout` SHALL responder 200 y borrar la cookie `access_token` (cookie vencida con los mismos atributos), haya o no sesión.

#### Scenario: Logout con sesión
- **WHEN** un usuario con sesión llama a `POST /auth/logout`
- **THEN** responde 200 y `Set-Cookie` borra `access_token`, y la siguiente petición sin cookie a `GET /auth/yo` responde 401

#### Scenario: Logout sin sesión
- **WHEN** se llama a `POST /auth/logout` sin cookie
- **THEN** responde 200

### Requirement: Usuario actual desde la cookie
Las rutas que piden sesión SHALL identificar al usuario sólo con la cookie `access_token` y responder 401 si falta, si el token es inválido o venció, o si el usuario no existe o está inactivo. El encabezado `Authorization` MUST ignorarse.

#### Scenario: Sin cookie
- **WHEN** se llama a `GET /auth/yo` sin cookie
- **THEN** responde 401

#### Scenario: Token en Authorization
- **WHEN** se llama a `GET /auth/yo` sin cookie y con `Authorization: Bearer <token válido>`
- **THEN** responde 401

#### Scenario: Token alterado o vencido
- **WHEN** la cookie trae un token con la firma alterada o con `exp` pasado
- **THEN** responde 401

### Requirement: Consulta de la sesión
`GET /auth/yo` SHALL devolver el usuario de la sesión (sin `password_hash`), sus roles vigentes leídos de la base en ese momento y los roles que dice el token.

#### Scenario: Roles vigentes y del token
- **WHEN** un usuario con sesión llama a `GET /auth/yo`
- **THEN** responde 200 con `usuario`, `roles_vigentes` y `roles_token`; recién iniciada la sesión ambas listas coinciden

### Requirement: Cambio de contraseña
`POST /auth/cambiar-password` con sesión SHALL verificar la contraseña actual y, en una sola transacción, guardar el hash de la nueva, poner `debe_cambiar_password=false` y dejar una línea en `evento_seguridad` (RN-16). MUST NOT emitir un token nuevo ni invalidar sesiones abiertas.

#### Scenario: Cambio exitoso
- **WHEN** un usuario con sesión envía su contraseña actual correcta y una nueva
- **THEN** responde 200 sin `Set-Cookie`, el login con la nueva contraseña funciona, con la vieja da 401, y hay una línea nueva en `evento_seguridad` con el usuario como actor

#### Scenario: La misma cookie sigue sirviendo
- **WHEN** después del cambio se llama a `GET /auth/yo` con la cookie anterior
- **THEN** responde 200 y `debe_cambiar_password` es `false`

#### Scenario: Contraseña actual incorrecta
- **WHEN** la contraseña actual enviada no coincide
- **THEN** responde 401 `{"detail": "La contraseña actual no es correcta"}` y no cambia nada ni deja evento

#### Scenario: Sin sesión
- **WHEN** se llama sin cookie
- **THEN** responde 401
