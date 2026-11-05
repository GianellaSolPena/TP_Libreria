# Proposal

## Why

Libros, clientes y ventas siguen con la lógica del TP: el servicio recibe la sesión y confirma por su cuenta, la venta no descuenta stock ni deja movimientos, no hay baja lógica ni reposición, y en cada petición autenticada conviven dos sesiones (`get_session` para la autorización y `get_session_tp` para el handler, estado TEMPORAL de C-06 D10). C-07 cierra el núcleo del parcial (Ej. 6, 16 pts; parte de Ej. 3, 5 y 8): RN-09, RN-10, RN-11 y RN-13 en un solo Unit of Work, con un único punto de escritura de stock, y el control de dueño de `GET /ventas/{id}` que C-06 dejó pendiente (QA-07).

## What Changes

- **Una sola sesión por petición**: `libros`, `clientes` y `ventas` pasan al patrón de capas de C-04 (`schemas`/`repository`/`unit_of_work`/`service`/`router`); se elimina `get_session_tp` de `app/core/database.py`. Ningún servicio recibe la sesión ni confirma.
- **Libros** (ADMIN): `POST /libros` con `autores` y `stock_inicial` (libro + autorías + movimiento «Stock inicial» en un bloque); `PATCH /libros/{id}` sólo título y precio (`stock` → 422); `DELETE /libros/{id}` baja lógica 204; `POST /libros/{id}/reponer` (dado de baja → 409); `GET /libros/{id}/movimientos` paginado. El ISBN se puede volver a cargar tras la baja (índice único parcial ya creado en C-03).
- **Punto único de escritura de stock**: una sola operación del módulo `libros` cambia `libro.stock` y agrega el `movimiento_stock` con el `usuario_id` del actor; la usan el alta, la reposición y la venta. Garantiza `stock == SUM(movimientos)`.
- **Catálogo público sin dados de baja**: `GET /libros` (envoltorio, `titulo` ILIKE ligado, `genero_id`), `GET /libros/{id}` (dado de baja → 404) y `GET /{editoriales,generos,autores}/{id}/libros` con envoltorio.
- **Clientes** (VENDEDOR, ADMIN): `POST /clientes`, `GET`/`PATCH /clientes/{id}` (con perfil), `POST /clientes/{id}/perfil`, `GET /clientes/{id}/ventas` y `GET /clientes` (ruta del TP, Q-10), por capas; correo repetido → 409 por UNIQUE, sin consulta previa.
- **Ventas**: UoW de `ventas` que compone repositorios de ventas, clientes y libros; `POST /ventas` en un bloque (precio copiado, total del servidor, un movimiento negativo por renglón); 409 sin escrituras si falta stock, si el cliente o un libro no existe o si el libro está dado de baja. Aviso con `BackgroundTasks` sólo si confirmó. `GET /ventas` paginado; `GET /ventas/{id}` **sin `requiere_rol`** (el servicio decide: personal o dueño, si no 403); `GET /mis-ventas` (autenticado).
- **Errores**: nuevo error de dominio de permiso (403 decidido por el servicio) y desborde numérico de la base traducido a 409 en lugar de 500.
- **BREAKING**: las rutas de libros, clientes y ventas pierden la barra final (`/libros`, `/clientes`, `/ventas`; IN-05); los listados de esos módulos pasan de lista plana con `limit`/`offset` al envoltorio con `page`/`size`; `POST /libros` reemplaza `stock` por `stock_inicial`; `PATCH /libros/{id}` deja de aceptar `stock`, `isbn`, `editorial_id` y `genero_id`. Los `.http` existentes que usan esas rutas se ajustan.
- Sin migraciones: el esquema de C-03 ya tiene todo lo necesario (se verifica que `alembic check` no detecta diferencias).

## Capabilities

### New Capabilities
- `libros-stock`: alta, modificación, baja lógica, reposición y movimientos de libros; punto único de escritura de stock; catálogo público de libros sin dados de baja (incluye los listados por editorial, género y autor).
- `clientes`: alta, consulta, modificación, perfil y ventas de un cliente, para el personal.
- `ventas`: registro de ventas con descuento de stock en un bloque, listado, detalle con control de dueño, `/mis-ventas` y aviso del comprobante en segundo plano.

### Modified Capabilities
- `autorizacion`: la matriz pasa a incluir `GET /ventas/{id}` (personal o dueño, decidido por el servicio) y `GET /mis-ventas` (autenticado), y las rutas nuevas de libros; las rutas de libros, clientes y ventas se nombran sin barra final.
- `capas-persistencia`: el reparto por capas y la sesión única por petición alcanzan a todos los módulos; un UoW puede componer repositorios de otros módulos.
- `errores-api`: desborde de un valor numérico en la base responde 409 con mensaje propio, no 500; el permiso que decide la operación (venta ajena) responde 403.

## Impact

- Código (`parcial/` únicamente): `app/core/database.py` (se borra `get_session_tp`), `app/core/errores.py` (403 de dominio, desborde numérico), `app/modules/libros/*` (nuevos `repository.py`, `unit_of_work.py`; reescritos `schemas.py`, `service.py`, `router.py`), `app/modules/clientes/*` (nuevo `unit_of_work.py`), `app/modules/ventas/*` (nuevos `repository.py`, `unit_of_work.py`), routers de `editoriales`, `generos`, `autores` (listados `/{id}/libros`), `main.py` (montaje de los routers partidos).
- Pruebas: nuevo `parcial/test/libros_clientes_ventas.http` (casos C-06 parte propia, C-10..C-13 y la igualdad `stock == SUM(movimientos)` por psql); ajuste de rutas en `auth.http` y `autorizacion.http`. Los `.http` y `seed.sql` del TP quedan para C-09.
- Sin cambios de esquema, dependencias ni `despliegue/`.
- Desbloquea C-08 (lecturas sin N+1) y C-09 (seed y casos).
