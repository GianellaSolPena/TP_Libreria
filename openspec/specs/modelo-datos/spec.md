# modelo-datos Specification

## Purpose

Define la estructura persistente que el parcial agrega al modelo del TP —acceso y seguridad, movimientos de stock, borrado lógico de libros y acceso opcional del cliente— con las restricciones que la base garantiza por sí misma, de modo que ningún dato inválido quede guardado aunque la aplicación falle.

## Requirements

### Requirement: Nombres de tablas y columnas del PDF
El esquema SHALL contener las tablas `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad` y `movimiento_stock` con exactamente las columnas que nombra el PDF, y `cliente.usuario_id` y `libro.borrado_en` agregadas. MUST NOT renombrarse ni quitarse ninguna tabla o columna existente del TP; `editorial`, `genero`, `autor`, `libro_autor`, `perfil_cliente`, `venta` y `renglon_venta` quedan iguales.

#### Scenario: Tablas nuevas presentes
- **WHEN** se aplica el esquema completo y se listan las tablas
- **THEN** existen `usuario(id, email, nombre, password_hash, activo, debe_cambiar_password)`, `asignacion_rol(id, usuario_id, rol, desde, vence_en, revocada_en, otorgada_por)`, `intento_acceso(id, cuando, email, ip, exito)`, `evento_seguridad(id, cuando, actor, accion)` y `movimiento_stock(id, libro_id, venta_id, usuario_id, cantidad, motivo, cuando)`

#### Scenario: Tablas del TP intactas
- **WHEN** se compara la definición de `editorial`, `genero`, `autor`, `libro_autor`, `perfil_cliente`, `venta` y `renglon_venta` con la de la migración 0002
- **THEN** columnas, tipos y restricciones son los mismos

### Requirement: Nulabilidad según el PDF
Sólo SHALL admitir nulo las columnas que el PDF marca "(nulo)": `asignacion_rol.vence_en`, `asignacion_rol.revocada_en`, `asignacion_rol.otorgada_por`, `movimiento_stock.venta_id`, `cliente.usuario_id` y `libro.borrado_en`. Toda otra columna nueva MUST ser NOT NULL, incluida `movimiento_stock.usuario_id`.

#### Scenario: Movimiento sin actor rechazado
- **WHEN** se inserta una fila en `movimiento_stock` con `usuario_id` nulo
- **THEN** la base rechaza la inserción por violación de NOT NULL

#### Scenario: Movimiento sin venta aceptado
- **WHEN** se inserta un movimiento válido con `venta_id` nulo (alta o reposición)
- **THEN** la base lo acepta

### Requirement: Tipos de fechas y dinero
Toda fecha nueva (`desde`, `vence_en`, `revocada_en`, `cuando`, `borrado_en`) SHALL ser `timestamptz`. El dinero MUST seguir siendo `NUMERIC` en la base y `Decimal` en Python, nunca `float`.

#### Scenario: Fechas con zona
- **WHEN** se consulta el tipo de cada columna de fecha nueva en el catálogo de PostgreSQL
- **THEN** todas son `timestamp with time zone`

### Requirement: Usuario con correo único y sin columna de rol
`usuario.email` SHALL ser único y la tabla `usuario` MUST NOT tener columna de rol: los roles viven sólo en `asignacion_rol`.

#### Scenario: Correo repetido rechazado
- **WHEN** se insertan dos usuarios con el mismo `email`
- **THEN** la base rechaza el segundo por violación de unicidad

### Requirement: Rol restringido a los tres valores
`asignacion_rol.rol` SHALL aceptar sólo `ADMIN`, `VENDEDOR` o `CLIENTE`, garantizado por un CHECK en la base.

#### Scenario: Rol desconocido rechazado
- **WHEN** se inserta una asignación con `rol = 'GERENTE'`
- **THEN** la base la rechaza por violación del CHECK

### Requirement: Una sola asignación abierta por usuario y rol
La base SHALL impedir dos filas de `asignacion_rol` con el mismo `(usuario_id, rol)` y `revocada_en` nulo, mediante un índice único parcial; las filas revocadas MUST NOT contar para esa unicidad.

#### Scenario: Segunda asignación abierta rechazada
- **WHEN** un usuario ya tiene una asignación `VENDEDOR` con `revocada_en` nulo y se inserta otra `VENDEDOR` abierta para el mismo usuario
- **THEN** la base la rechaza por violación de unicidad

#### Scenario: Reasignación tras revocar aceptada
- **WHEN** la asignación `VENDEDOR` anterior tiene `revocada_en` con fecha y se inserta una nueva `VENDEDOR` abierta
- **THEN** la base la acepta y conserva la fila revocada

### Requirement: ISBN único sólo entre libros vigentes
`libro.isbn` SHALL ser único sólo entre las filas con `borrado_en` nulo (índice único parcial), en lugar del UNIQUE común del TP. Los CHECK `precio > 0` y `stock >= 0` MUST seguir vigentes.

#### Scenario: Recargar un ISBN dado de baja
- **WHEN** existe un libro con ISBN `X` y `borrado_en` con fecha, y se inserta otro libro vigente con ISBN `X`
- **THEN** la base lo acepta

#### Scenario: Dos vigentes con el mismo ISBN
- **WHEN** existe un libro vigente con ISBN `X` y se inserta otro libro vigente con ISBN `X`
- **THEN** la base lo rechaza por violación de unicidad

#### Scenario: Restricciones de libro conservadas
- **WHEN** se inserta un libro con `precio = 0` o con `stock = -1`
- **THEN** la base lo rechaza por violación del CHECK correspondiente

### Requirement: Acceso opcional del cliente
`cliente.usuario_id` SHALL ser nulo, único y referencia a `usuario`; `cliente.email` MUST seguir siendo único. Desde el modelo, `Cliente.usuario` SHALL devolver un único objeto (o nada), no una lista.

#### Scenario: Dos clientes con el mismo usuario
- **WHEN** se asigna el mismo `usuario_id` a dos clientes
- **THEN** la base rechaza el segundo por violación de unicidad

#### Scenario: Varios clientes sin usuario
- **WHEN** se insertan dos clientes con `usuario_id` nulo
- **THEN** la base acepta ambos

#### Scenario: Navegación a objeto
- **WHEN** se carga un cliente con usuario y se accede a `Cliente.usuario`
- **THEN** se obtiene un `Usuario` y no una lista

### Requirement: Movimiento de stock con cantidad distinta de cero
`movimiento_stock.cantidad` SHALL ser distinta de cero (CHECK); `libro_id` y `usuario_id` MUST referenciar filas existentes y `venta_id`, si no es nulo, también.

#### Scenario: Cantidad cero rechazada
- **WHEN** se inserta un movimiento con `cantidad = 0`
- **THEN** la base lo rechaza por violación del CHECK

#### Scenario: Libro inexistente rechazado
- **WHEN** se inserta un movimiento con un `libro_id` que no existe
- **THEN** la base lo rechaza por violación de clave foránea

### Requirement: Índices de búsqueda y de claves foráneas
Cada clave foránea nueva SHALL tener un índice que la cubra (`asignacion_rol.usuario_id`, `asignacion_rol.otorgada_por`, `movimiento_stock.libro_id`, `movimiento_stock.venta_id`, `movimiento_stock.usuario_id`; `cliente.usuario_id` cubierta por su UNIQUE), e `intento_acceso` MUST tener el índice compuesto `(email, ip, cuando)`.

#### Scenario: Índices presentes
- **WHEN** se listan los índices de las tablas nuevas y modificadas
- **THEN** cada columna de FK nueva aparece como primera columna de algún índice y existe el índice `(email, ip, cuando)` en `intento_acceso`

### Requirement: Historial de seguridad y accesos sin relaciones
`intento_acceso` y `evento_seguridad` MUST NOT tener claves foráneas: `evento_seguridad.actor` es texto libre (admite `SISTEMA`) e `intento_acceso.email` guarda el correo intentado aunque no exista usuario.

#### Scenario: Intento con correo inexistente
- **WHEN** se inserta un intento de acceso con un correo que no corresponde a ningún usuario
- **THEN** la base lo acepta

#### Scenario: Evento del sistema
- **WHEN** se inserta un evento con `actor = 'SISTEMA'`
- **THEN** la base lo acepta

### Requirement: Navegación en los dos extremos
Cada relación nueva SHALL declararse en ambos modelos: `Usuario`↔`AsignacionRol`, `Usuario`↔`Cliente` (objeto en los dos lados), `Usuario`↔`MovimientoStock`, `Libro`↔`MovimientoStock` y `Venta`↔`MovimientoStock`.

#### Scenario: Navegación recíproca
- **WHEN** se carga un movimiento con su libro, su usuario y su venta, y desde cada uno se recorre la colección de movimientos
- **THEN** el movimiento original aparece en `Libro.movimientos`, `Usuario.movimientos` y `Venta.movimientos`
