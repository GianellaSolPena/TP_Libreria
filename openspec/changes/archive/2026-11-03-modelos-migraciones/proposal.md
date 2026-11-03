# Proposal

## Why

El Ejercicio 2 del parcial (10 pts) pide los modelos nuevos (`usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`, `movimiento_stock`), los cambios en `cliente` (acceso opcional) y `libro` (borrado lógico) con todas sus restricciones —incluidos los dos índices únicos parciales— y dos migraciones nuevas: la 0003 autogenerada y leída, y la 0004 escrita a mano con el disparador de sólo agregado que el Ejercicio 7 exige (RN-12, caso C-14). Hoy `parcial/` sólo tiene el esquema del TP (0001, 0002): sin estas tablas no se pueden construir autenticación (C-05), roles (C-06) ni libros/ventas con movimientos (C-07).

## What Changes

- Nuevo `app/modules/usuarios/models.py` con `Usuario` (email UNIQUE, sin columna de rol), `AsignacionRol` (CHECK de rol ADMIN/VENDEDOR/CLIENTE, vigencia `desde`/`vence_en`/`revocada_en`, `otorgada_por`, índice único parcial `(usuario_id, rol) WHERE revocada_en IS NULL`), `IntentoAcceso` (índice `(email, ip, cuando)`) y `EventoSeguridad` (actor texto, sin FK).
- `libros/models.py`: nuevo `MovimientoStock` (`venta_id` nulo, `usuario_id` obligatorio, CHECK `cantidad <> 0`); `Libro` suma `borrado_en` y **reemplaza** el UNIQUE común de `isbn` (`uq_libro_isbn`) por un índice único parcial `WHERE borrado_en IS NULL`. **BREAKING** (esquema): un ISBN dado de baja ya no bloquea un alta nueva.
- `clientes/models.py`: `Cliente.usuario_id` nulo, UNIQUE y FK a `usuario`; `Cliente.usuario` devuelve un objeto.
- `ventas/models.py`: sólo se agrega la navegación `Venta.movimientos` (la tabla `venta` no cambia).
- Navegación en los dos extremos e índice en cada FK nueva; fechas nuevas `timestamptz`.
- `app/modules/models.py` registra `usuarios` para que Alembic vea las tablas nuevas.
- Migración **0003** generada con `alembic revision --autogenerate`, leída antes de aplicar, corregida a mano donde haga falta, con comentario que lo declara; downgrade completo.
- Migración **0004** escrita a mano: función + disparador que rechaza todo UPDATE y DELETE sobre `movimiento_stock`; downgrade lo quita.
- `parcial/test/solo_agregado.sql` para el caso C-14.

## Capabilities

### New Capabilities

- `modelo-datos`: estructura persistente del dominio que el parcial agrega o cambia (tablas de acceso y seguridad, movimientos de stock, borrado lógico de libros, acceso opcional del cliente) con sus restricciones, índices y navegación.
- `migraciones-esquema`: evolución del esquema exclusivamente con Alembic (ciclo upgrade/downgrade completo) y la garantía en la base de que `movimiento_stock` es de sólo agregado.

### Modified Capabilities

(ninguna — `configuracion-ciclo-vida`, `salud` y `tp-snapshots` no cambian)

## Impact

- Código: `parcial/app/modules/usuarios/{__init__.py,models.py}` (nuevo), `parcial/app/modules/libros/models.py`, `parcial/app/modules/clientes/models.py`, `parcial/app/modules/ventas/models.py`, `parcial/app/modules/models.py`, `parcial/migrations/versions/0003_*.py`, `parcial/migrations/versions/0004_*.py`, `parcial/test/solo_agregado.sql`.
- Interfaz hacia C-04 (repositorios): la columna de baja lógica es `libro.borrado_en` (nula = vigente). Ver design.md.
- Los servicios del TP que escriben `libro.stock` o crean libros siguen compilando, pero el stock deja de coincidir con `SUM(movimientos)` hasta C-07 (punto único de escritura).
- Fuera de alcance: repositorios/UoW/paginación (C-04), endpoints de auth/roles (C-05/C-06), escritura de movimientos y baja lógica en servicios (C-07), carga de datos (`seed.py`, C-09). `despliegue/` no se toca.
