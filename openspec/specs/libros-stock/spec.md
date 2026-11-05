# libros-stock Specification

## Purpose
Gestiona el ciclo de vida de los libros (alta con stock inicial, modificación de título y precio, baja lógica, reposición y consulta de movimientos) y el catálogo público, con una única vía de escritura del stock que mantiene `stock == SUM(movimientos)` (PDF Ej. 3 y 6, RN-01, RN-11, RN-12, RN-13).

## Requirements

### Requirement: Alta de libro con autores y stock inicial
`POST /libros` (ADMIN) SHALL recibir `isbn`, `titulo`, `precio`, `stock_inicial`, `editorial_id`, `genero_id` (opcional) y `autores` (al menos uno, cada uno con `autor_id`, `rol` y `orden`, sin `autor_id` repetidos) y, en una sola transacción, crear el libro, sus autorías y —si `stock_inicial` es mayor que cero— un movimiento de stock de `+stock_inicial` con motivo «Stock inicial» y el usuario que hizo el alta. Responde 201 con el libro, su editorial, su género y sus autorías. El contrato MUST rechazar con 422 los campos no declarados (incluido `stock`), `precio` <= 0, `stock_inicial` negativo, `autores` vacío o con `autor_id` repetido y `rol` fuera de autor/coautor/traductor/ilustrador. Un ISBN igual al de otro libro vigente MUST responder 409 «Ya existe un libro vigente con ese ISBN»; una editorial, género o autor inexistente MUST responder 409; en ambos casos no MUST quedar ninguna fila.

#### Scenario: Alta con el cuerpo del PDF
- **WHEN** un ADMIN envía `POST /libros` con `{"isbn":"978-950-00-0006-6","titulo":"Los que aman, odian","precio":"21000.00","stock_inicial":4,"editorial_id":1,"genero_id":1,"autores":[{"autor_id":3,"rol":"coautor","orden":1},{"autor_id":4,"rol":"coautor","orden":2}]}`
- **THEN** responde 201 con `stock` 4 y las dos autorías, y existe un único movimiento del libro con `cantidad` 4, motivo «Stock inicial», `venta_id` nulo y el `usuario_id` del ADMIN

#### Scenario: Stock enviado en lugar de stock inicial
- **WHEN** un ADMIN envía `POST /libros` con `stock` en el cuerpo
- **THEN** responde 422 y no se crea nada

#### Scenario: Autor inexistente
- **WHEN** un ADMIN envía `POST /libros` con un `autor_id` que no existe
- **THEN** responde 409 con un mensaje propio, sin texto de la base, y no quedan ni el libro, ni autorías, ni movimientos

#### Scenario: Stock inicial cero
- **WHEN** un ADMIN da de alta un libro con `stock_inicial` 0
- **THEN** responde 201 con `stock` 0 y el libro no tiene movimientos

### Requirement: Modificación de título y precio
`PATCH /libros/{id}` (ADMIN) SHALL modificar sólo `titulo` y/o `precio` con los campos enviados y responder 200 con el libro. Cualquier otro campo (incluidos `stock`, `isbn`, `editorial_id`, `genero_id`), un `null` o un `precio` <= 0 MUST responder 422 sin cambiar nada. Un libro inexistente o dado de baja MUST responder 404.

#### Scenario: PATCH parcial
- **WHEN** un ADMIN envía `PATCH /libros/1` con `{"precio":"26000.00"}`
- **THEN** responde 200 con el precio nuevo y el título sin cambios

#### Scenario: PATCH del stock
- **WHEN** un ADMIN envía `PATCH /libros/1` con `{"stock": 99}`
- **THEN** responde 422 y ni el stock ni los movimientos cambian

#### Scenario: PATCH de un libro dado de baja
- **WHEN** un ADMIN envía `PATCH` sobre un libro dado de baja
- **THEN** responde 404

### Requirement: Baja lógica de libro
`DELETE /libros/{id}` (ADMIN) SHALL marcar la fecha de baja del libro sin borrar la fila y responder 204 sin cuerpo. Un libro inexistente o ya dado de baja MUST responder 404. Tras la baja, el libro MUST dejar de aparecer en el catálogo, no MUST poder venderse ni reponerse, y las ventas anteriores MUST seguir mostrándolo con su título.

#### Scenario: Baja
- **WHEN** un ADMIN pide `DELETE /libros/5`
- **THEN** responde 204, la fila sigue en la base con fecha de baja, y `GET /libros/5` responde 404

#### Scenario: Venta vieja de un libro dado de baja
- **WHEN** se da de baja un libro que figura en una venta y el personal pide el detalle de esa venta
- **THEN** el renglón sigue mostrando el título del libro

#### Scenario: Baja repetida
- **WHEN** un ADMIN pide `DELETE` sobre un libro ya dado de baja
- **THEN** responde 404

### Requirement: Reutilización del ISBN tras la baja
El ISBN SHALL ser único sólo entre libros vigentes: tras dar de baja un libro, otro libro vigente MUST poder darse de alta con el mismo ISBN; un segundo vigente con ese ISBN MUST responder 409.

#### Scenario: Recargar el ISBN dado de baja
- **WHEN** se da de baja el libro con ISBN `X` y un ADMIN envía `POST /libros` con ISBN `X`
- **THEN** responde 201

#### Scenario: Segundo vigente con el mismo ISBN
- **WHEN** a continuación un ADMIN envía otro `POST /libros` con ISBN `X`
- **THEN** responde 409 «Ya existe un libro vigente con ese ISBN»

### Requirement: Reposición de stock
`POST /libros/{id}/reponer` (ADMIN) SHALL recibir `{"cantidad": n}` con `n` entero >= 1 y, en una sola transacción, sumar `n` al stock del libro y agregar un movimiento de `+n` con motivo «Reposición» y el usuario que repone. Responde 200 con el libro (stock actualizado) y el movimiento creado. Un campo no declarado o `cantidad` < 1 MUST responder 422; un libro inexistente MUST responder 404; un libro dado de baja MUST responder 409 sin escrituras.

#### Scenario: Reponer
- **WHEN** un ADMIN pide `POST /libros/1/reponer` con `{"cantidad": 3}` y el stock era 10
- **THEN** responde 200 con `stock` 13 y el movimiento de `cantidad` 3 y motivo «Reposición»

#### Scenario: Reponer un libro dado de baja
- **WHEN** un ADMIN pide reponer un libro dado de baja
- **THEN** responde 409 y no cambia ni el stock ni los movimientos

#### Scenario: Cantidad inválida
- **WHEN** un ADMIN pide reponer con `{"cantidad": 0}`
- **THEN** responde 422

### Requirement: Consulta de movimientos de un libro
`GET /libros/{id}/movimientos` (ADMIN) SHALL responder 200 con el envoltorio de paginación (`page`, `size` opcionales) de los movimientos del libro ordenados del más antiguo al más nuevo, cada uno con `id`, `cantidad`, `motivo`, `cuando`, `venta_id` y `usuario_id`. MUST responder también para un libro dado de baja; un libro inexistente MUST responder 404.

#### Scenario: Movimientos tras alta y reposición
- **WHEN** un libro se dio de alta con `stock_inicial` 4 y se repuso 3, y un ADMIN pide sus movimientos
- **THEN** responde 200 con `total` 2: «Stock inicial» +4 y «Reposición» +3

#### Scenario: Libro inexistente
- **WHEN** un ADMIN pide `GET /libros/9999/movimientos`
- **THEN** responde 404

### Requirement: Stock sólo a través de movimientos
El stock de un libro SHALL cambiar únicamente por el alta con stock inicial, la reposición y la venta, y cada cambio MUST agregar en la misma transacción un movimiento cuya cantidad es exactamente la variación del stock, con el usuario que realizó la operación. Ninguna ruta MUST permitir escribir el stock directamente, y para todo libro MUST cumplirse en todo momento que `stock` es igual a la suma de las cantidades de sus movimientos. Los movimientos MUST NOT modificarse ni borrarse desde la aplicación.

#### Scenario: Igualdad tras las operaciones
- **WHEN** después de cualquier combinación de altas, reposiciones y ventas (exitosas o rechazadas) se consulta en psql, para cada libro, `stock` contra `SUM(movimiento_stock.cantidad)`
- **THEN** coinciden en todos los libros

#### Scenario: Stock que no puede quedar negativo
- **WHEN** una operación pediría dejar el stock de un libro por debajo de cero
- **THEN** se rechaza con 409, el stock no cambia y no queda ningún movimiento de esa operación

### Requirement: Catálogo público de libros
`GET /libros` SHALL responder sin sesión el envoltorio de paginación de los libros vigentes ordenados por `id`, con `page`, `size`, `titulo` (búsqueda parcial sin distinguir mayúsculas, con parámetros ligados) y `genero_id` opcionales, donde `total` cuenta con los mismos filtros. `GET /libros/{id}` SHALL responder sin sesión el libro con editorial, género y autorías, o 404 si no existe o está dado de baja. Los libros dados de baja MUST NOT aparecer en ninguna de las dos.

#### Scenario: Listado del PDF
- **WHEN** hay 5 libros vigentes y se pide `GET /libros?size=2`
- **THEN** responde 200 con 2 items, `total` 5, `page` 1, `size` 2 y `pages` 3

#### Scenario: Búsqueda con inyección
- **WHEN** se pide `GET /libros?titulo=' OR '1'='1`
- **THEN** responde 200 con `items` vacío y `total` 0

#### Scenario: Paginación con filtro
- **WHEN** se pide `GET /libros?titulo=ficc&size=1` y luego con `page=2`
- **THEN** el primero responde `total` 1 y `pages` 1, y el segundo 422 «La página 2 no existe: hay 1»

#### Scenario: Libro dado de baja fuera del catálogo
- **WHEN** un libro está dado de baja y se pide `GET /libros`
- **THEN** no aparece en `items` ni cuenta en `total`

### Requirement: Libros por editorial, género y autor
`GET /editoriales/{id}/libros`, `GET /generos/{id}/libros` y `GET /autores/{id}/libros` SHALL responder sin sesión el envoltorio de paginación (`page`, `size` opcionales) de los libros vigentes de esa editorial, género o autor, ordenados por `id`. Si la editorial, el género o el autor no existe MUST responder 404.

#### Scenario: Libros de un autor
- **WHEN** se pide `GET /autores/3/libros` y el autor tiene dos libros vigentes y uno dado de baja
- **THEN** responde 200 con `total` 2

#### Scenario: Editorial inexistente
- **WHEN** se pide `GET /editoriales/9999/libros`
- **THEN** responde 404
