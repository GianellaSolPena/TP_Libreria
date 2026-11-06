## ADDED Requirements

### Requirement: Sustituto suelto rechazado en el contrato
Todo texto de entrada de un cuerpo (campos de texto, incluidos correos y contraseñas, en altas, PATCH, registro y login) que contenga un sustituto UTF-16 suelto (un punto de código entre U+D800 y U+DFFF, que en JSON llega como el escape `\ud800` o como los bytes `ED A0 80`) SHALL responder 422 sin llegar a la base, con la misma forma que el resto de los errores de validación del contrato (lista en `detail` con la ubicación del campo). La respuesta MUST NOT ser 500 y la petición MUST NOT dejar ninguna escritura ni registrar un intento de acceso. Los textos sin sustitutos sueltos —incluidos los que usan caracteres fuera del plano básico escritos como par de sustitutos válido, por ejemplo un emoji— MUST seguir aceptándose igual que antes.

#### Scenario: Alta de libro con sustituto suelto en el título
- **WHEN** un ADMIN envía `POST /libros` con un cuerpo válido salvo `"titulo": "a\ud800"`
- **THEN** responde 422 con `detail` que señala `["body", "titulo"]`, no 500, y no se crea el libro ni su movimiento de stock

#### Scenario: Login con sustituto suelto en la contraseña
- **WHEN** se envía `POST /auth/login` con `{"email": "admin@example.com", "password": "abc\ud800defgh"}`
- **THEN** responde 422 con `detail` que señala `["body", "password"]`, no 401 ni 500, y no se registra un intento de acceso

#### Scenario: Registro con sustituto suelto en el nombre
- **WHEN** se envía `POST /auth/registro` con un correo nuevo, una contraseña válida y `"nombre": "a\ud800"`
- **THEN** responde 422 y no se crea ni el usuario ni la ficha de cliente

#### Scenario: Teléfono del perfil con sustituto suelto
- **WHEN** el personal envía `POST /clientes/1/perfil` con `{"telefono": "1\ud800"}`
- **THEN** responde 422 y el perfil no cambia

#### Scenario: Par de sustitutos válido sin cambios
- **WHEN** un ADMIN da de alta un género con `{"nombre": "Ensayo 😀"}` (un emoji escrito como par válido)
- **THEN** la respuesta es la misma que antes del cambio (201)

### Requirement: Número no finito rechazado en el contrato
Todo campo numérico de un cuerpo (precios, cantidades, stock inicial e ids) que reciba un número JSON no finito —`NaN`, `Infinity` o `-Infinity` sin comillas, o un literal como `1e400` que desborda a infinito— SHALL responder 422 sin llegar a la base, con `detail` que señala el campo. La respuesta MUST NOT ser 500 y la petición MUST NOT dejar escrituras. Los valores entre comillas (`"NaN"`, `"1e400"`) MUST seguir respondiendo 422 como antes.

#### Scenario: Precio NaN sin comillas
- **WHEN** un ADMIN envía `POST /libros` con un cuerpo válido salvo `"precio": NaN`
- **THEN** responde 422 con `detail` que señala `["body", "precio"]`, no 500, y no se crea el libro

#### Scenario: Precio que desborda a infinito
- **WHEN** un ADMIN envía `POST /libros` con `"precio": 1e400` o `"precio": -Infinity`
- **THEN** responde 422, no 500

#### Scenario: Cantidad entera no finita
- **WHEN** el personal envía `POST /ventas` con `{"cliente_id": 1, "renglones": [{"libro_id": 1, "cantidad": NaN}]}`, o un ADMIN envía `POST /libros/1/reponer` con `{"cantidad": Infinity}`
- **THEN** responde 422, no 500, y el stock y los movimientos no cambian

### Requirement: Respuesta 422 siempre serializable
La respuesta a un error de validación del contrato SHALL poder enviarse siempre, cualquiera sea la entrada: conserva la forma `{"detail": [...]}` con `type`, `loc` y `msg` de cada error, y cuando repite la entrada (`input`) o el contexto (`ctx`) MUST reemplazar un número no finito y un texto no codificable en UTF-8 por una representación segura, sin cambiar nada de los errores cuya entrada ya era serializable. Esto MUST valer también cuando el valor problemático está en un campo no declarado (incluso en el nombre de la clave) o cuando el error repite el cuerpo entero (por ejemplo, un campo obligatorio faltante).

#### Scenario: Clave sobrante con sustituto suelto
- **WHEN** se envía `POST /auth/login` con `{"email": "a@x.com", "password": "abcdefgh", "x\ud800": 1}`
- **THEN** responde 422 (campo no declarado), no 500

#### Scenario: Falta un campo obligatorio y otro trae un no finito
- **WHEN** un ADMIN envía `POST /libros` sin `autores` y con `"precio": Infinity`
- **THEN** responde 422 con un cuerpo JSON válido, no 500

#### Scenario: 422 de una entrada común sin cambios
- **WHEN** se pide `GET /generos/abc` o se envía `POST /generos` con un campo extra
- **THEN** el cuerpo del 422 es idéntico al de antes del cambio

### Requirement: Texto que el driver no puede codificar traducido a 422
Si un texto que pasó el contrato llega igual a una consulta y el driver de la base no lo puede codificar, la operación SHALL responder 422 con un mensaje propio, sin texto de la base ni traza, sin dejar escrituras y nunca 500. Cualquier otro error de la base que no se deba a la entrada MUST NOT presentarse como 422.

#### Scenario: Texto no codificable fuera del contrato
- **WHEN** un texto con un sustituto suelto llega a una consulta sin pasar por la validación del contrato
- **THEN** responde 422 con el mismo mensaje propio que los demás datos rechazados por la base, sin `invalid input for query argument`, sin `UnicodeEncodeError` ni traza
