# capas-persistencia Specification

## Purpose

Define cómo se accede a los datos y cómo se agrupan las escrituras de cada operación de negocio en una sola transacción, con responsabilidades separadas entre router, servicio, Unit of Work y repositorio (PDF Ej. 6, p. 8-9).

## Requirements

### Requirement: Repositorio genérico por entidad
Cada entidad SHALL accederse mediante un repositorio construido con la sesión y la clase del modelo, que ofrece al menos obtener por id, obtener todos, contar, agregar, modificar y borrar. Agregar, modificar y borrar SHALL enviar los cambios a la base sin confirmarlos; ningún repositorio MUST confirmar una transacción.

#### Scenario: Alta visible antes de confirmar
- **WHEN** un servicio agrega una entidad con el repositorio dentro de un Unit of Work abierto
- **THEN** la entidad recibe su id dentro del mismo bloque y la fila sólo queda guardada cuando el Unit of Work se confirma

#### Scenario: Error de base detectado dentro del bloque
- **WHEN** agregar o modificar viola una restricción de la base
- **THEN** el error se produce en ese mismo llamado al repositorio, dentro del bloque, y no al confirmar

### Requirement: Repositorio con baja lógica
Las entidades con baja lógica SHALL usar un repositorio que hereda del genérico, excluye por defecto las filas dadas de baja en obtener por id, obtener todos y contar, y agrega obtener por id incluyendo las dadas de baja y dar de baja (que marca la fecha de baja sin borrar la fila).

#### Scenario: Fila dada de baja oculta
- **WHEN** se da de baja una entidad y luego se la pide por id, en el listado o en el conteo
- **THEN** no aparece en ninguno de los tres

#### Scenario: Fila dada de baja accesible a propósito
- **WHEN** se pide por id incluyendo las dadas de baja
- **THEN** se obtiene la entidad con su fecha de baja, y la fila sigue en la base

### Requirement: Unit of Work confirma o revierte
Cada operación de negocio SHALL escribirse dentro de un Unit of Work que confirma al salir normalmente del bloque y revierte si se sale con una excepción. El Unit of Work MUST NOT cerrar la sesión, porque no la creó.

#### Scenario: Operación exitosa
- **WHEN** el bloque del Unit of Work termina sin excepción
- **THEN** todos los cambios del bloque quedan confirmados juntos

#### Scenario: Operación fallida
- **WHEN** dentro del bloque se lanza una excepción (por ejemplo, una violación de unicidad)
- **THEN** ningún cambio del bloque queda guardado y la excepción sigue hasta el router

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
