# Spec Delta

## ADDED Requirements

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
