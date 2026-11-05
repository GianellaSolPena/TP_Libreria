# Spec Delta

## MODIFIED Requirements

### Requirement: Alta de editoriales, géneros y autores
`POST /editoriales` (`nombre`, `pais`), `POST /generos` (`nombre`) y `POST /autores` (`nombre`, `nacionalidad`) SHALL crear el recurso y responder 201 con su representación incluido el `id`. Son rutas del grupo protegido sólo para ADMIN: sin sesión MUST responder 401 y sin el rol ADMIN vigente (o con el cambio de contraseña pendiente) MUST responder 403, sin crear nada. El contrato MUST rechazar campos no declarados y textos vacíos con 422.

#### Scenario: Alta correcta
- **WHEN** un ADMIN envía `POST /generos` con `{"nombre": "Poesía"}` y no existe
- **THEN** responde 201 con `{"id": <nuevo>, "nombre": "Poesía"}`

#### Scenario: Nombre de género duplicado
- **WHEN** un ADMIN envía `POST /generos` con un nombre que ya existe
- **THEN** responde 409 con «Ya existe un género con ese nombre»

#### Scenario: Texto vacío
- **WHEN** un ADMIN envía `POST /autores` con `nombre` vacío
- **THEN** responde 422

#### Scenario: Alta sin sesión
- **WHEN** se envía `POST /editoriales` sin cookie
- **THEN** responde 401 y no se crea nada

#### Scenario: Alta por un vendedor
- **WHEN** un VENDEDOR envía `POST /generos` con su cookie
- **THEN** responde 403 y no se crea nada

### Requirement: Modificación parcial
`PATCH /editoriales/{id}`, `PATCH /autores/{id}` y `PATCH /generos/{id}` SHALL modificar sólo los campos enviados y responder 200 con el recurso actualizado; son rutas del grupo protegido sólo para ADMIN (sin sesión MUST responder 401; sin el rol ADMIN vigente o con cambio pendiente, 403). Un campo enviado como `null` o no declarado MUST responder 422; un id inexistente MUST responder 404; un nombre que choca con otro guardado MUST responder 409.

#### Scenario: PATCH parcial
- **WHEN** un ADMIN envía `PATCH /editoriales/1` con `{"pais": "Chile"}`
- **THEN** responde 200, cambia `pais` y `nombre` queda igual

#### Scenario: PATCH con null
- **WHEN** un ADMIN envía `PATCH /autores/1` con `{"nombre": null}`
- **THEN** responde 422 y no cambia nada

#### Scenario: PATCH a un nombre existente
- **WHEN** un ADMIN envía `PATCH /editoriales/1` con el `nombre` de la editorial 2
- **THEN** responde 409 y la editorial 1 queda igual

#### Scenario: PATCH por un cliente
- **WHEN** un usuario con sólo CLIENTE envía `PATCH /autores/1` con su cookie
- **THEN** responde 403 y no cambia nada
