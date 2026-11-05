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
