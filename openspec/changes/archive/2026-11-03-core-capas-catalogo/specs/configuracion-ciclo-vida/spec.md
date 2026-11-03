# Spec Delta

## MODIFIED Requirements

### Requirement: Una sesión por petición
Cada petición que use la base SHALL recibir su propia sesión, creada sin expirar los objetos al confirmar, y la sesión SHALL cerrarse al terminar la petición. La dependencia que entrega la sesión MUST NOT confirmar ni revertir: la confirmación y la reversión pertenecen al Unit of Work de la operación.

#### Scenario: Rutas existentes siguen funcionando
- **WHEN** se ejecuta una petición de lectura y una de alta de los módulos existentes (por ejemplo `GET /editoriales` y `POST /editoriales`)
- **THEN** responden correctamente y el alta queda guardada

#### Scenario: La sesión no confirma por su cuenta
- **WHEN** una petición modifica datos sin cerrar normalmente un Unit of Work
- **THEN** los cambios no quedan guardados al terminar la petición
