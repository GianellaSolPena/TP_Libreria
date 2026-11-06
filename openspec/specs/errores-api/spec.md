# errores-api Specification

## Purpose

Define cómo la API convierte los errores del dominio y los rechazos de la base en códigos HTTP con mensajes propios, sin exponer texto interno de la base ni terminar en 500 por una entrada inválida (RN-15, PDF p. 9 y requisitos no funcionales).

## Requirements

### Requirement: Rechazo de la base traducido a 409
Una violación de restricción de la base (unicidad, clave foránea u otra) SHALL responder 409 con un mensaje propio de la operación. La unicidad MUST garantizarla la base, sin una consulta previa que la verifique.

#### Scenario: Nombre duplicado
- **WHEN** se da de alta una editorial con un nombre que ya existe
- **THEN** responde 409 con «Ya existe una editorial con ese nombre» y no se guarda nada

### Requirement: Sin texto interno de la base
Ninguna respuesta de error MUST incluir el texto del error de la base, nombres de restricciones, tablas o columnas, ni una traza.

#### Scenario: Cuerpo del 409
- **WHEN** una alta responde 409 por unicidad
- **THEN** el cuerpo sólo contiene el mensaje propio, sin `uq_`, `duplicate key`, `DETAIL` ni nombres de tablas

### Requirement: Recurso de la ruta inexistente
Si el recurso identificado por la ruta no existe, la respuesta SHALL ser 404 con un mensaje propio.

#### Scenario: Id inexistente
- **WHEN** se pide `GET /editoriales/9999` y no existe
- **THEN** responde 404 con «Editorial no encontrada»

### Requirement: Entrada inválida responde 422
Un cuerpo con campos no declarados, con tipos o valores fuera de contrato, o un parámetro de ruta no entero o fuera del rango de un entero de 32 bits SHALL responder 422 sin llegar a la base; ninguna entrada inválida MUST terminar en 500.

#### Scenario: Campo extra en el cuerpo
- **WHEN** se envía `POST /generos` con `{"nombre": "Ensayo", "id": 7}`
- **THEN** responde 422 y no se crea nada

#### Scenario: Id fuera de rango
- **WHEN** se pide `GET /autores/99999999999`
- **THEN** responde 422, no 500

#### Scenario: Id no entero
- **WHEN** se pide `GET /generos/abc`
- **THEN** responde 422

### Requirement: Desborde numérico de la base traducido a 409
Si una entrada que cumple el contrato produce en la base un valor numérico fuera del rango de su columna (por ejemplo, un stock que supera el máximo de un entero de 32 bits tras una reposición, o un total de venta que no entra en su columna), la operación SHALL responder 409 con un mensaje propio, sin texto de la base, sin dejar escrituras y nunca 500.

#### Scenario: Reposición que desborda el stock
- **WHEN** un ADMIN repone un libro con una `cantidad` válida para el contrato pero que, sumada al stock actual, supera el máximo de un entero de 32 bits
- **THEN** responde 409 con un mensaje propio y el stock y los movimientos no cambian

### Requirement: Permiso decidido por la operación
Cuando una operación determina que el usuario identificado no puede acceder al recurso pedido (por ejemplo, una venta que no es suya), la respuesta SHALL ser 403 con un mensaje propio, sin incluir datos del recurso.

#### Scenario: Venta ajena
- **WHEN** una usuaria con sólo CLIENTE pide el detalle de una venta de otro cliente
- **THEN** responde 403 con un mensaje propio y el cuerpo no contiene datos de la venta

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
