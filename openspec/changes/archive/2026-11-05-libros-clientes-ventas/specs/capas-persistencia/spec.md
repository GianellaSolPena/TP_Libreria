# Spec Delta

## MODIFIED Requirements

### Requirement: Un Unit of Work por módulo con la misma sesión
Cada módulo SHALL tener su Unit of Work, que compone los repositorios que sus operaciones necesitan —aunque pertenezcan a otros módulos—, todos con la misma sesión de la petición. Cada petición MUST usar una sola sesión, compartida por las dependencias de autenticación y autorización y por el Unit of Work.

#### Scenario: Repositorios comparten transacción
- **WHEN** una operación usa dos repositorios del mismo Unit of Work
- **THEN** ambos escriben en la misma transacción y se confirman o revierten juntos

#### Scenario: Venta que compone repositorios de otros módulos
- **WHEN** el registro de una venta escribe la venta, descuenta el stock de los libros y agrega los movimientos
- **THEN** todas esas escrituras van por el Unit of Work de ventas, en una sola transacción, y un rechazo en cualquiera de ellas revierte todas

#### Scenario: Sin sesión transitoria
- **WHEN** se busca en `parcial/app` una dependencia de sesión distinta de la única que entrega la sesión de la petición
- **THEN** no existe ninguna

### Requirement: Reparto de responsabilidades por capa
El router SHALL construir el Unit of Work con una dependencia y pasarlo al servicio sin abrirlo; el servicio SHALL abrirlo con `async with` y aplicar las reglas; el servicio MUST NOT recibir ni usar la sesión, construir su Unit of Work, confirmar ni revertir. Esto MUST cumplirse en todos los módulos, con la única excepción del registro de intentos de acceso.

#### Scenario: Revisión de servicios migrados
- **WHEN** se buscan referencias a la sesión, `commit(` o `rollback(` en los servicios y routers de todos los módulos
- **THEN** no aparece ninguna, salvo el registro de intentos de acceso documentado
