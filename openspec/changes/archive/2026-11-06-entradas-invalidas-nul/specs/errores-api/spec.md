# Spec Delta

## ADDED Requirements

### Requirement: Carácter nulo rechazado en el contrato
Todo texto de entrada (campos de texto de los cuerpos, incluidos correos y contraseñas, y parámetros de consulta de texto) que contenga el carácter U+0000 SHALL responder 422 sin llegar a la base, con la misma forma que el resto de los errores de validación del contrato (lista en `detail` con la ubicación del campo). La respuesta MUST NOT ser 500 y la petición MUST NOT dejar ninguna escritura. Los textos sin U+0000 MUST seguir aceptándose igual que antes.

#### Scenario: Búsqueda por título con carácter nulo
- **WHEN** se pide `GET /libros?titulo=a%00b`
- **THEN** responde 422 con `detail` que señala `["query", "titulo"]`, no 500

#### Scenario: Login con carácter nulo en el correo
- **WHEN** se envía `POST /auth/login` con `{"email": "admin\u0000@example.com", "password": "admin1234"}`
- **THEN** responde 422 con `detail` que señala `["body", "email"]`, no 401 ni 500, y no se registra un intento de acceso

#### Scenario: Alta con carácter nulo en un texto
- **WHEN** un ADMIN envía `POST /generos` con `{"nombre": "Ens\u0000ayo"}`
- **THEN** responde 422 y no se crea el género

#### Scenario: Texto válido sin cambios
- **WHEN** se pide `GET /libros?titulo=ficc` o se da de alta un género con un nombre sin U+0000
- **THEN** la respuesta es la misma que antes del cambio (200 o 201 según corresponda)

### Requirement: Error de dato de la base traducido a 422
Si una entrada que cumple el contrato es rechazada por la base como dato inválido (por ejemplo, un carácter que la codificación de la base no admite o un texto que no representa el tipo de la columna), la operación SHALL responder 422 con un mensaje propio, sin texto de la base, sin dejar escrituras y nunca 500. El desborde numérico MUST seguir respondiendo 409 y las violaciones de restricción MUST seguir respondiendo 409 con su mensaje propio; cualquier otro error de la base que no se deba a la entrada MUST NOT presentarse como 422.

#### Scenario: Dato rechazado por la base
- **WHEN** un texto con un carácter que la base no admite llega a una consulta (sin pasar por la validación del contrato)
- **THEN** responde 422 con un mensaje propio en `detail`, sin `invalid byte sequence`, SQLSTATE, nombres de tablas ni traza

#### Scenario: Unicidad sigue en 409
- **WHEN** se da de alta una editorial con un nombre que ya existe
- **THEN** responde 409 con «Ya existe una editorial con ese nombre», como antes
