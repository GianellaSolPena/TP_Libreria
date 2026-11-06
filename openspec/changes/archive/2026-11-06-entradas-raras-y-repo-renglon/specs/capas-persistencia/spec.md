## MODIFIED Requirements

### Requirement: Repositorio genérico por entidad
Cada entidad SHALL accederse mediante un repositorio construido con la sesión y la clase del modelo, que ofrece al menos obtener por id, obtener todos, contar, agregar, modificar y borrar. Agregar, modificar y borrar SHALL enviar los cambios a la base sin confirmarlos; ningún repositorio MUST confirmar una transacción. Esto MUST valer también para las entidades que nacen junto con otra: los renglones de una venta MUST tener su propio repositorio, compuesto en el Unit of Work de ventas, y el registro de la venta MUST darlos de alta por ese repositorio y no por cascada desde la venta.

#### Scenario: Alta visible antes de confirmar
- **WHEN** un servicio agrega una entidad con el repositorio dentro de un Unit of Work abierto
- **THEN** la entidad recibe su id dentro del mismo bloque y la fila sólo queda guardada cuando el Unit of Work se confirma

#### Scenario: Error de base detectado dentro del bloque
- **WHEN** agregar o modificar viola una restricción de la base
- **THEN** el error se produce en ese mismo llamado al repositorio, dentro del bloque, y no al confirmar

#### Scenario: Renglones de venta por su repositorio
- **WHEN** se registra una venta válida de dos renglones (caso C-10)
- **THEN** los renglones se dan de alta por el repositorio de renglones del Unit of Work de ventas, en la misma transacción que la venta, los movimientos y el stock; la respuesta 201 es la misma que antes del cambio; y una venta rechazada (C-11, C-12) sigue sin dejar renglones

#### Scenario: Una entidad, un repositorio
- **WHEN** se comparan las clases de tabla de `parcial/app/modules` con los repositorios del mismo directorio
- **THEN** cada entidad tiene un repositorio que hereda del genérico o del de baja lógica
