# intentos-acceso Specification

## Purpose
Deja constancia de cada intento de login, aunque la petición falle, y lo usa para frenar la adivinación de contraseñas: tras varios fallos seguidos desde la misma dirección, el login se rechaza sin verificar la contraseña.

## Requirements

### Requirement: Registro de cada intento de login
Cada login que llega a verificar la contraseña, correcto o fallido, SHALL dejar una fila en `intento_acceso` con el correo enviado, la IP del cliente, el instante (`timestamptz`) y `exito`. La fila MUST escribirse en una sesión y una transacción propias que se confirman siempre, también cuando la petición termina en 401.

#### Scenario: Fallo registrado
- **WHEN** un login responde 401 por contraseña incorrecta
- **THEN** existe en `intento_acceso` una fila con ese correo, la IP del cliente y `exito=false`

#### Scenario: Éxito registrado
- **WHEN** un login responde 200
- **THEN** existe una fila con `exito=true`

#### Scenario: Correo inexistente también se registra
- **WHEN** se intenta un login con un correo que no tiene usuario
- **THEN** existe una fila con ese correo y `exito=false`

### Requirement: Límite de intentos fallidos
Si hay 5 o más intentos fallidos con el mismo correo desde la misma IP en los últimos 60 segundos, posteriores al último login correcto de ese correo e IP, el login SHALL responder 429 con `Retry-After` y MUST NOT calcular ni verificar ningún hash (RN-07). El chequeo SHALL ser lo primero que hace el login y costar una consulta.

#### Scenario: Sexto intento bloqueado
- **WHEN** se hacen seis logins fallidos seguidos con el mismo correo desde la misma IP
- **THEN** los cinco primeros responden 401 y el sexto 429 con `Retry-After` (segundos, entero >= 1) en pocos milisegundos
- **AND** `intento_acceso` tiene exactamente los cinco fallos de ese correo e IP

#### Scenario: Bloqueo con la contraseña correcta
- **WHEN** tras cinco fallos se envía la contraseña correcta dentro de los 60 segundos
- **THEN** responde 429 igualmente (no se verifica la contraseña)

#### Scenario: Ventana vencida
- **WHEN** pasaron más de 60 segundos desde los fallos que provocaron el bloqueo
- **THEN** el login vuelve a verificar la contraseña y responde 200 o 401 según corresponda

#### Scenario: Login correcto reinicia la cuenta
- **WHEN** hay cuatro fallos, luego un login correcto y luego otro fallo, todo dentro de 60 segundos
- **THEN** el último responde 401 (no 429) y las filas anteriores siguen en la tabla

#### Scenario: Otra IP u otro correo
- **WHEN** el correo bloqueado intenta desde otra IP, o otro correo desde la misma IP
- **THEN** el límite no aplica

### Requirement: El rechazo por límite no se registra
La respuesta 429 MUST NOT agregar filas a `intento_acceso`, de modo que seguir intentando durante el bloqueo no lo extiende.

#### Scenario: Insistir durante el bloqueo
- **WHEN** se envían tres logins más mientras rige el bloqueo
- **THEN** los tres responden 429 y la cantidad de filas de ese correo e IP no cambia
