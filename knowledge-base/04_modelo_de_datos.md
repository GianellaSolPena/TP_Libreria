# Modelo de Datos

> Los **nombres de tablas y columnas son obligatorios** (los casos de prueba y la corrección los usan). Se pueden **agregar** columnas, no quitar ni renombrar las indicadas. Las tablas `editorial`, `genero`, `autor`, `libro_autor` y `perfil_cliente` **no cambian** respecto del TP. Todas las fechas nuevas son `timestamptz`. Dinero: `NUMERIC` en BD y `Decimal` en Python, nunca `float`. **Cada FK nueva lleva índice** (PostgreSQL no lo crea solo). La navegación se declara en los dos extremos.

## Dominios
- **Catálogo**: editorial, genero, autor, libro, libro_autor, movimiento_stock.
- **Clientes y ventas**: cliente, perfil_cliente, venta, renglon_venta.
- **Acceso y seguridad**: usuario, asignacion_rol, intento_acceso, evento_seguridad.

## ERD (transcripción de la Figura 1, p. 5 — verificada sobre la imagen renderizada)
Rombo lleno = composición, rombo vacío = agregación, flecha = asociación. Verde = nuevas (`Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad`, `MovimientoStock`); ámbar = cambian (`Libro`: borrado lógico; `Cliente`: acceso opcional); gris = no cambian (`Editorial`, `Genero`, `Autor`, `LibroAutor`, `PerfilCliente`, `Venta`, `RenglonVenta`).
```
Venta 1 ◆── composición ── 1..* RenglonVenta          (una venta nace con sus renglones)
RenglonVenta 0..* ── asociación ──> 1 Libro
Venta 0..* ── asociación ──> 1 Cliente
Libro 0..* ◇── agregación ── 1 Editorial              (rombo dibujado en el extremo Libro)
Libro 0..* ◇── agregación ── 0..1 Genero              (genero_id nulo)
Libro 1 ──── 1..* LibroAutor 0..* ──── 1 Autor        (rol, orden)
Cliente 1 ── "1 a 1" ── 0..1 PerfilCliente
Cliente 0..1 ── "acceso opcional" ──> 0..1 Usuario     (cliente.usuario_id nulo y UNIQUE)
Usuario 1 ── "roles con vigencia" ── 0..* AsignacionRol
«appendOnly» MovimientoStock 0..* ── asociación ──> 1 Libro
MovimientoStock 0..* ── "origen" ──> 0..1 Venta        (venta_id nulo: alta/reposición no tienen venta)
MovimientoStock 0..* ── "actor" ──> 1 Usuario          (usuario_id OBLIGATORIO: multiplicidad 1)
IntentoAcceso, EventoSeguridad: SIN relaciones (evento_seguridad.actor es texto, no FK)
```
`otorgada_por` (nulo) figura en la tabla pero **no está dibujada** en la Fig. 1: si se la declara FK a `usuario`, lleva su índice (ver Q-17). La venta no guarda quién la registró: eso queda en `movimiento_stock.usuario_id` (la venta 1 del seed "registrada por vendedor@example.com").

Tipos que muestra la figura: `datetime` (-> `timestamptz`) en `cuando`, `desde`, `vence_en`, `revocada_en`, `borrado_en`, `venta.fecha`; `Decimal` (-> `NUMERIC`) en `precio`, `total`, `precio_unitario`; `int` en `stock`, `cantidad`, `orden`; `bool` en `activo`, `debe_cambiar_password`, `exito`; `str` en `email`, `ip`, `nombre`, `motivo`, `actor`, `accion`, `password_hash`; `AsignacionRol.rol` tipado como `Rol` (enumeración ADMIN/VENDEDOR/CLIENTE, garantizada en la base por CHECK).

## Entidades nuevas y modificadas (según el PDF)
| Tabla | Columnas | Restricciones |
|---|---|---|
| `usuario` (nueva) | id, email, nombre, password_hash, activo, debe_cambiar_password | `email` UNIQUE |
| `asignacion_rol` (nueva) | id, usuario_id, rol, desde, vence_en (nulo), revocada_en (nulo), otorgada_por (nulo) | CHECK rol IN (ADMIN, VENDEDOR, CLIENTE); **índice único parcial** (usuario_id, rol) WHERE `revocada_en IS NULL` (`postgresql_where`) |
| `intento_acceso` (nueva) | id, cuando, email, ip, exito | Índice (email, ip, cuando) |
| `evento_seguridad` (nueva) | id, cuando, actor (texto), accion | Sin restricciones extra |
| `cliente` (cambia) | + `usuario_id` (nulo permitido) | `usuario_id` UNIQUE; `email` sigue UNIQUE. `Cliente.usuario` devuelve un objeto, no lista |
| `libro` (cambia) | + `borrado_en` (timestamptz, nulo) | **índice único parcial** (isbn) WHERE `borrado_en IS NULL` **en lugar** del UNIQUE; siguen CHECK `precio > 0` y `stock >= 0` |
| `movimiento_stock` (nueva) | id, libro_id, venta_id (nulo), usuario_id, cantidad, motivo, cuando | CHECK `cantidad <> 0`; **sólo agregado** (disparador) |

### Nulabilidad, índices y relaciones exigidas (derivado de la tabla p. 5-6 y del párrafo p. 6)
- **Nulo permitido sólo donde el PDF dice "(nulo)"**: `asignacion_rol.vence_en`, `.revocada_en`, `.otorgada_por`; `movimiento_stock.venta_id`; `cliente.usuario_id`; `libro.borrado_en`. Todo lo demás `NOT NULL` (incluido `movimiento_stock.usuario_id`, multiplicidad 1 en la Fig. 1).
- **Fechas nuevas `timestamptz`** (`DateTime(timezone=True)`): `asignacion_rol.desde/vence_en/revocada_en`, `intento_acceso.cuando`, `evento_seguridad.cuando`, `movimiento_stock.cuando`, `libro.borrado_en`.
- **Índice en cada FK nueva** (PostgreSQL no lo crea solo): `asignacion_rol.usuario_id` (el índice único parcial `(usuario_id, rol) WHERE revocada_en IS NULL` no cubre las filas revocadas, así que va un índice propio), `asignacion_rol.otorgada_por` (si es FK), `movimiento_stock.libro_id`, `movimiento_stock.venta_id`, `movimiento_stock.usuario_id`; `cliente.usuario_id` queda cubierto por su UNIQUE.
- **Índice compuesto** `intento_acceso (email, ip, cuando)` (el conteo de RN-07 filtra por esas tres columnas).
- **Restricciones con nombre**: CHECK `rol IN ('ADMIN','VENDEDOR','CLIENTE')`; CHECK `cantidad <> 0`; índice único parcial de `asignacion_rol` y de `libro.isbn` con `postgresql_where`; siguen `ck_libro_precio_positivo` (`precio > 0`) y `ck_libro_stock_no_negativo` (`stock >= 0`).
- **Navegación en los dos extremos** (`back_populates`): `Usuario.asignaciones` ↔ `AsignacionRol.usuario`; `Usuario.cliente` ↔ `Cliente.usuario` (**objeto**, no lista: `uselist=False`); `Usuario.movimientos` ↔ `MovimientoStock.usuario`; `Libro.movimientos` ↔ `MovimientoStock.libro`; `Venta.movimientos` ↔ `MovimientoStock.venta`. Si `otorgada_por` es FK, su relación necesita `foreign_keys` explícito (dos FKs a `usuario`).
- **Módulo de cada modelo** (p. 9): `Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad` en `usuarios/models.py`; `MovimientoStock` (y `LibroAutor`) en `libros/models.py`; `PerfilCliente` en `clientes/models.py`; `RenglonVenta` en `ventas/models.py`.

Tablas existentes que no cambian (gris en la Fig. 1; nombres y restricciones reales de la migración 0001/0002 del TP): `editorial(id, nombre, pais)` con `uq_editorial_nombre`; `genero(id, nombre)` con `uq_genero_nombre`; `autor(id, nombre, nacionalidad)`; `libro_autor(libro_id, autor_id, rol, orden)` PK compuesta con `ck_libro_autor_orden_positivo` (orden >= 1) y `ck_libro_autor_rol_valido` (rol IN autor, coautor, traductor, ilustrador), índice `ix_libro_autor_autor_id`; `perfil_cliente(id, cliente_id, telefono nulo, direccion nula)` con `uq_perfil_cliente_cliente_id`; `venta(id, cliente_id, fecha timestamptz, total NUMERIC(12,2))` con `ck_venta_total` (total >= 0); `renglon_venta(id, venta_id, libro_id, cantidad, precio_unitario NUMERIC(10,2))` con `ck_renglon_venta_cantidad` (> 0) y `ck_renglon_venta_precio` (> 0). `libro` hoy: `precio NUMERIC(10,2)`, `stock int`, `editorial_id NOT NULL`, `genero_id` nulo, **`uq_libro_isbn`** (UNIQUE común que la 0003 debe reemplazar).

## Invariantes que explica el PDF
- **ISBN**: con borrado lógico, un UNIQUE común impediría recargar un ISBN dado de baja y la base respondería "ya existe" de un libro que no se ve. Por eso la unicidad es sólo entre vigentes (índice único parcial, igual herramienta que `asignacion_rol`).
- **Roles**: `usuario` no tiene columna `rol`; rol vigente = fila no revocada y no vencida. Reasignar un rol vencido cierra la fila anterior y abre una nueva.
- **Stock**: `libro.stock` = suma de `movimiento_stock.cantidad` de ese libro, **siempre**. Es la igualdad que se verifica tras cada caso de venta; se rompe si algo escribe el stock sin dejar movimiento. Una sola vía de escritura (punto único, RN-11).
- **Sólo agregado**: disparador (migración 4, a mano) rechaza UPDATE y DELETE sobre `movimiento_stock` "venga de donde venga". Los movimientos no se corrigen: se compensan con otro. Consecuencia práctica: `seed.py` y la limpieza de tests no pueden "vaciar" con `DELETE FROM movimiento_stock`; usan `TRUNCATE ... RESTART IDENTITY CASCADE` (los disparadores `FOR EACH ROW` de DELETE no se disparan con TRUNCATE; el PDF sólo exige rechazar UPDATE y DELETE).
- **intento_acceso**: se cuenta por (email, ip, ventana de 60 s); un login correcto "reinicia la cuenta" (las filas quedan pero dejan de contar).

## Migraciones (Ejercicio 2)
| N.º | Origen | Contenido |
|---|---|---|
| 0001 | TP | esquema inicial (existente) |
| 0002 | TP | agrega `genero` y `libro.genero_id` (existente) |
| 0003 | **`alembic revision --autogenerate`**, leída antes de aplicar, con comentario que lo diga; corregida a mano si hace falta (comentario explica) | tablas de acceso, `movimiento_stock`, cambios en `cliente` y `libro` (dropear `uq_libro_isbn`, crear el índice único parcial de `isbn`) |
| 0004 | **escrita a mano** | función + disparador de sólo-agregado sobre `movimiento_stock` (RN-12) |

`alembic upgrade head` sobre base vacía, `alembic downgrade base` y otra vez `upgrade head` deben funcionar. Los revision ids actuales son `"0001"` y `"0002"` (convención del TP).

## Seed data inicial (`seed.py`, vacía las tablas y carga como mínimo)
| Qué | Datos |
|---|---|
| Usuarios | admin@example.com y admin2@example.com (ADMIN), vendedor@example.com (VENDEDOR), ana@example.com (CLIENTE), nuevo@example.com (VENDEDOR, con cambio de contraseña obligatorio) |
| Editoriales, géneros, autores | Los del TP: 3 editoriales, 3 géneros, 6 autores |
| Libros | Cinco, con stock actual: Rayuela 10, Antología de la literatura fantástica 5, Ficciones 8, Respiración artificial 3, Bestiario 1 |
| Clientes | Lucía Fernández (con perfil) y Tomás Ríos, sin usuario; Ana Paz, con el usuario ana@example.com |
| Venta | La 1, de Lucía, registrada por vendedor@example.com: 1 Rayuela y 2 Ficciones, total 69000.00 |
| Movimientos | Un "Stock inicial" por libro. Rayuela y Ficciones se cargan con 11 y 10 ejemplares; la venta 1 deja dos movimientos de salida (-1 y -2); stock coincide con la suma de movimientos en los cinco libros |
| Historial de seguridad | Una línea con actor `SISTEMA`: "Carga de los datos iniciales" |

Comprobación aritmética del PDF: Rayuela 11-1=10, Ficciones 10-2=8; total 69000.00 implica precio Rayuela 25000 y Ficciones 22000 (1x25000 + 2x22000 = 69000). Eso **contradice** el `seed.sql` del TP (Ficciones a 18000): ver IN-03 en `10_preguntas_abiertas.md`.
