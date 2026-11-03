# Spec Delta

## Purpose

Define cómo la API convierte los errores del dominio y los rechazos de la base en códigos HTTP con mensajes propios, sin exponer texto interno de la base ni terminar en 500 por una entrada inválida (RN-15, PDF p. 9 y requisitos no funcionales).

## ADDED Requirements

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
