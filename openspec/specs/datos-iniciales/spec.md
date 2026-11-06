# datos-iniciales Specification

## Purpose
Especificar la carga de datos iniciales de `parcial/seed.py`: catálogo, usuarios, ventas, movimientos de stock y evento `SISTEMA` del PDF, de forma reproducible (TRUNCATE con reinicio de identidades) y consistente (stock igual a la suma de movimientos).

## Requirements

### Requirement: Carga inicial reproducible con un solo comando
El proyecto SHALL incluir `seed.py` en la raíz de `parcial/`, ejecutable con `python seed.py` desde esa carpeta sobre una base en `head`, que tome la conexión de la misma configuración que la aplicación (sin credenciales en el archivo). El script MUST vaciar todas las tablas de la aplicación y reiniciar sus secuencias antes de cargar, y MUST hacer todo en una única transacción: si algo falla, la base queda como estaba. Correrlo varias veces seguidas MUST dejar el mismo estado (mismos ids y mismos datos; sólo pueden variar las marcas de tiempo de la propia carga). Antes de confirmar, el script MUST comprobar que `stock` coincide con la suma de movimientos en cada libro y, si no coincide, revertir y terminar con error. El esquema (incluida la tabla de versión de Alembic y el disparador de sólo agregado) MUST NOT modificarse.

#### Scenario: Base recién migrada
- **WHEN** se corre `alembic upgrade head` sobre una base vacía y luego `python seed.py`
- **THEN** el script termina sin error y la base contiene exactamente los datos iniciales descritos en esta capacidad

#### Scenario: Segunda corrida tras usar la API
- **WHEN** después de correr casos que crean ventas, libros, usuarios, eventos e intentos de acceso se vuelve a correr `python seed.py`
- **THEN** no queda ninguna de esas filas, los ids vuelven a empezar en 1 y los datos son los mismos que en la primera corrida

#### Scenario: Movimientos de sólo agregado
- **WHEN** el script vacía `movimiento_stock` existiendo movimientos previos
- **THEN** el vaciado se completa sin desactivar ni modificar el disparador que rechaza UPDATE y DELETE, y el disparador sigue rechazándolos después

#### Scenario: Falta la configuración
- **WHEN** se corre `python seed.py` sin `POSTGRES_PASSWORD` o sin `JWT_SECRET_KEY` en el entorno
- **THEN** el script termina con un error que nombra la variable faltante y no escribe nada

### Requirement: Catálogo inicial del PDF
La carga SHALL dejar 3 editoriales, 3 géneros y 6 autores, y 5 libros vigentes con estos ids, títulos, precios y stock actual: 1 Rayuela (ISBN `978-950-00-0001-1`, 25000.00, stock 10), 2 Antología de la literatura fantástica (ISBN `978-950-00-0002-8`, 30000.00, stock 5), 3 Ficciones (22000.00, stock 8), 4 Respiración artificial (stock 3) y 5 Bestiario (stock 1). Cada libro MUST tener al menos un autor y su editorial; los autores 3 y 4 MUST ser los coautores del cuerpo de ejemplo de `POST /libros` del PDF y la editorial 1 y el género 1 MUST existir. Ningún título salvo Ficciones MUST contener «ficc» (sin distinguir mayúsculas).

#### Scenario: Listado del ejemplo del PDF
- **WHEN** tras el seed se pide `GET /libros?size=2`
- **THEN** responde 200 con `total` 5, `pages` 3 y los libros 1 (Rayuela, 25000.00, stock 10) y 2 (Antología de la literatura fantástica, 30000.00, stock 5)

#### Scenario: Búsqueda con filtro
- **WHEN** tras el seed se pide `GET /libros?titulo=ficc&size=1`
- **THEN** responde 200 con `total` 1 y `pages` 1

#### Scenario: Cuerpo de ejemplo de alta de libro
- **WHEN** tras el seed el ADMIN envía el cuerpo de ejemplo de `POST /libros` del PDF (editorial 1, género 1, autores 3 y 4, ISBN `978-950-00-0006-6`)
- **THEN** responde 201

### Requirement: Usuarios y roles iniciales
La carga SHALL dejar cinco usuarios activos con contraseñas de mentira guardadas sólo como hash bcrypt: `admin@example.com` y `admin2@example.com` con ADMIN vigente, `vendedor@example.com` con VENDEDOR vigente, `ana@example.com` con CLIENTE vigente y `nuevo@example.com` con VENDEDOR vigente y el cambio de contraseña obligatorio pendiente. Los otros cuatro MUST NOT tener el cambio pendiente. Las asignaciones MUST quedar abiertas (sin vencimiento ni revocación). Las contraseñas en claro MUST aparecer sólo en `seed.py` (y en los casos de prueba y el README que las usan), nunca en la base ni en la aplicación.

#### Scenario: Login de cada usuario
- **WHEN** tras el seed cada usuario inicia sesión con su contraseña del seed
- **THEN** responde 200; `debe_cambiar_password` es `true` sólo para `nuevo@example.com`

#### Scenario: Roles vigentes
- **WHEN** tras el seed cada usuario pide `GET /auth/yo`
- **THEN** los roles vigentes son ADMIN para `admin` y `admin2`, VENDEDOR para `vendedor` y `nuevo`, y CLIENTE para `ana`

#### Scenario: Sin contraseñas en claro en la base
- **WHEN** se consulta `usuario.password_hash`
- **THEN** cada valor es un hash bcrypt y ninguno coincide con la contraseña en claro

### Requirement: Clientes y venta inicial
La carga SHALL dejar los clientes 1 Lucía Fernández (con perfil, sin usuario), 2 Tomás Ríos (sin perfil ni usuario) y 3 Ana Paz (vinculada al usuario `ana@example.com`), y la venta 1 de Lucía con dos renglones, 1 Rayuela a 25000.00 y 2 Ficciones a 22000.00, total 69000.00. La venta 1 MUST quedar registrada por `vendedor@example.com` a través de sus movimientos de stock. Ana Paz MUST NOT tener ventas.

#### Scenario: Detalle de la venta 1
- **WHEN** tras el seed el vendedor pide `GET /ventas/1`
- **THEN** responde 200 con la cliente Lucía Fernández, dos renglones con los precios unitarios 25000.00 y 22000.00 y total 69000.00

#### Scenario: Ana Paz ve sus ventas
- **WHEN** tras el seed `ana@example.com` pide `GET /mis-ventas`
- **THEN** responde 200 con una página vacía (`total` 0)

#### Scenario: Cuerpo de ejemplo de venta
- **WHEN** tras el seed el vendedor envía el cuerpo de ejemplo de `POST /ventas` del PDF (cliente 2, libro 1 ×2, libro 4 ×1)
- **THEN** responde 201 con los precios copiados y el total calculado

### Requirement: Stock coherente con los movimientos
La carga SHALL dejar un movimiento «Stock inicial» por libro, registrado por `admin@example.com` (Rayuela con 11 y Ficciones con 10 ejemplares, el resto con su stock actual), y dos movimientos «Venta» ligados a la venta 1 y registrados por `vendedor@example.com` (Rayuela −1, Ficciones −2). En los cinco libros `stock` MUST ser igual a la suma de sus movimientos.

#### Scenario: Invariante tras el seed
- **WHEN** tras el seed se compara `libro.stock` con `SUM(movimiento_stock.cantidad)` por libro
- **THEN** coinciden en los cinco libros y hay exactamente 7 movimientos

#### Scenario: Historial de un libro vendido
- **WHEN** tras el seed el ADMIN pide `GET /libros/1/movimientos`
- **THEN** responde 200 con «Stock inicial» +11 y «Venta» −1 ligado a la venta 1

### Requirement: Línea de sistema en el historial de seguridad
La carga SHALL dejar exactamente una fila en `evento_seguridad`, con actor `SISTEMA` y acción «Carga de los datos iniciales». El seed MUST NOT dejar filas en `intento_acceso`.

#### Scenario: Historial tras el seed
- **WHEN** tras el seed un ADMIN pide `GET /eventos`
- **THEN** responde 200 con `total` 1 y esa única línea con actor `SISTEMA`
