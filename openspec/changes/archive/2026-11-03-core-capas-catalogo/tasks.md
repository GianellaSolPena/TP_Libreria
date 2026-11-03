# Tasks

> Sin pytest (DD-01). Verificación con pedidos manuales (REST Client / curl) contra `uvicorn main:app` corriendo desde `parcial/`, base con `alembic upgrade head` y `test/seed.sql` cargado. Skills: `fastapi`, `async-python-patterns`.

## 1. Núcleo en `app/core/`

- [x] 1.1 Crear `parcial/app/core/unit_of_work.py` con `UnitOfWork` (D3): `__aenter__` devuelve `self`; `__aexit__` hace `rollback()` si hubo excepción y `commit()` si no (si el commit falla, revierte y relanza); nunca `close()`. Verificar: `python -c "import app.core.unit_of_work"` sin error y `grep -n "close" app/core/unit_of_work.py` vacío.
- [x] 1.2 Crear `parcial/app/core/repository.py` con `BaseRepository[T]` (D1: `_condiciones`, `get_by_id` con `select`, `get_all(offset, limit)` ordenado por `id`, `count`, `add`/`update`/`delete` con `flush()`) y `SoftDeleteRepository[T]` (D2: filtra `borrado_en IS NULL`, `get_by_id_including_deleted`, `soft_delete` con `datetime.now(UTC)`), con comentario sobre la interfaz asumida de C-03. Verificar: importa sin error y `grep -n "commit" app/core/repository.py` vacío.
- [x] 1.3 Crear `parcial/app/core/paginacion.py` (D6): `ParametrosPagina` (`page` 1..2**31-1 por defecto 1, `size` 1..100 por defecto 20), `PaginaDep`, `Pagina[T]` genérico, `calcular_paginas` (mínimo 1) y cálculo de `offset`. Verificar en un REPL: `calcular_paginas(0, 20) == 1`, `calcular_paginas(5, 2) == 3`, `calcular_paginas(4, 2) == 2`.
- [x] 1.4 Crear `parcial/app/core/errores.py` (D5, D7): `NoEncontrado`, `Conflicto`, `PaginaInexistente`, `IdPath` y el gestor `traducir_errores(conflicto, conflicto_fk=None)` (23505 → 409 propio, 23503 → 409 propio/genérico, otro IntegrityError → 409 genérico, `PaginaInexistente` → 422 «La página N no existe: hay M», `NoEncontrado` → 404), sin usar el texto de la excepción de la base. Verificar: importa sin error y `grep -n "orig)" app/core/errores.py` no muestra uso del texto (sólo `sqlstate`).
- [x] 1.5 En `parcial/app/core/database.py`, dejar `get_session` sin commit ni rollback (sólo `async with factory() as session: yield session`) y agregar `get_session_tp` con el comportamiento anterior, comentado `# TRANSITORIO: se borra en C-07` (D4). Verificar: lectura del archivo; `get_session` no contiene `commit`/`rollback`.
- [x] 1.6 Cambiar los routers de `libros`, `clientes` y `ventas` para importar `get_session_tp as get_session` (sólo el import, sin otra lógica). Verificar: `POST /libros/` y `POST /clientes/` siguen creando filas que se ven en un `GET` posterior.

## 2. Módulo `editoriales` por capas

- [x] 2.1 `schemas.py`: `EditorialCreate`/`EditorialUpdate` como `BaseModel` con `extra="forbid"` y `min_length=1`, validador de `null` en el Update; `EditorialRead` con `from_attributes`. Verificar al probar 2.5 (campo extra → 422).
- [x] 2.2 Crear `repository.py` con `EditorialRepository(BaseRepository[Editorial])` y `unit_of_work.py` con `EditorialesUnitOfWork` (`self.editoriales`). Verificar: importan sin error.
- [x] 2.3 Reescribir `service.py`: `crear`, `obtener` (lanza `NoEncontrado("Editorial no encontrada")`), `actualizar` (`exclude_unset`), `listar(uow, page, size) -> Pagina[Editorial]` (count → `PaginaInexistente` → `get_all`), cada uno abriendo el UoW con `async with`; sin `AsyncSession`, `HTTPException`, `commit` ni `rollback`. Verificar: `grep -nE "AsyncSession|HTTPException|commit|rollback" app/modules/editoriales/service.py` vacío.
- [x] 2.4 Reescribir `router.py`: dependencia `get_uow` + alias `UowDep`; rutas sin barra (`""`, `/{editorial_id}`); `IdPath`; `PaginaDep`; `response_model=Pagina[EditorialRead]` en el listado; cada handler envuelto en `traducir_errores("Ya existe una editorial con ese nombre")`. `/{editorial_id}/libros` verifica existencia con el servicio (UoW) y lista con `libros.service.listar` usando `get_session` (D4, transitorio). Verificar: `grep -n "AsyncSession" app/modules/editoriales/router.py` sólo en la ruta `/libros` transitoria.
- [x] 2.5 Verificación manual de editoriales: `POST /editoriales` → 201; mismo nombre → 409 «Ya existe una editorial con ese nombre» sin texto de la base; `{"nombre":"X","pais":"Y","id":9}` → 422; `PATCH /editoriales/1 {"pais":"Chile"}` → 200 y `nombre` igual; `PATCH` con `{"nombre": null}` → 422; `PATCH` al nombre de otra → 409; `GET /editoriales/9999` → 404; `GET /editoriales/99999999999` → 422; `GET /editoriales?size=1&page=1` → envoltorio con `pages` = total; `page` de más → 422 «La página N no existe: hay M»; `size=500` → 422; `GET /editoriales/1/libros` → 200.

## 3. Módulo `generos` por capas

- [x] 3.1 Repetir 2.1–2.4 para `generos` (`GeneroCreate`/`GeneroUpdate`/`GeneroRead`, `GeneroRepository`, `GenerosUnitOfWork`, servicio con «Género no encontrado», router con «Ya existe un género con ese nombre», `PATCH /generos/{id}` conservado por Q-10, `/{genero_id}/libros` transitorio). Verificar: mismo `grep` de 2.3 vacío en `generos/service.py`.
- [x] 3.2 Verificación manual de géneros: `POST /generos {"nombre":"Poesía"}` → 201; repetido → 409 propio; `{"nombre":"Ensayo","id":7}` → 422; `GET /generos/abc` → 422; con 3 géneros, `GET /generos?size=2&page=2` → 1 item, `total` 3, `pages` 2; `GET /generos/1/libros` → 200.

## 4. Módulo `autores` por capas

- [x] 4.1 Repetir 2.1–2.4 para `autores` (sin unicidad: 409 genérico «Los datos del autor violan una restricción»; «Autor no encontrado»; `GET /autores` paginado conservado por Q-10). `AutorRepository` agrega `listar_autorias(autor_id, offset, limit)` con `joinedload(LibroAutor.libro)` dentro del método; `/{autor_id}/libros` pasa por servicio + UoW (respuesta `list[AutorLibroRead]` con `limit`/`offset` hasta C-07). Verificar: `grep -nE "AsyncSession|HTTPException|commit|rollback|select\(" app/modules/autores/service.py` vacío.
- [x] 4.2 Verificación manual de autores: `POST /autores` → 201; `nombre` vacío → 422; `PATCH /autores/1 {"nacionalidad":"Uruguaya"}` → 200 parcial; `GET /autores/99999999999` → 422; `GET /autores` → envoltorio; `GET /autores/1/libros` → 200 con libros; `GET /autores/9999/libros` → 404.

## 5. Cierre del change

- [x] 5.1 Revisión de capas: `grep -rnE "AsyncSession|commit\(|rollback\(" app/modules/{editoriales,generos,autores}/service.py` vacío; en sus `router.py` sólo aparece `AsyncSession` en las rutas `/libros` transitorias de editoriales y géneros; `grep -rn "get_session_tp" app` sólo en `database.py` y los routers de libros/clientes/ventas.
- [x] 5.2 Arranque limpio: `uvicorn main:app` desde `parcial/` sin errores; `/docs` muestra las rutas de editoriales/géneros/autores sin barra final; `GET /health/ready` → 200.
- [x] 5.3 Sin texto de la base: provocar un 409 en cada módulo y confirmar que el cuerpo es sólo `{"detail": "<mensaje propio>"}` (sin `uq_`, `duplicate key`, `DETAIL`).

## Workflow follow-up

- `/opsx:archive core-capas-catalogo` y marcar `[x]` C-04 en `CHANGES.md`.
- En C-07: borrar `get_session_tp`, migrar `/{editoriales,generos,autores}/{id}/libros` al envoltorio y al filtro de baja lógica (Q-18).
- En C-06: proteger POST/PATCH del catálogo con `requiere_rol("ADMIN")`.
- En C-09: casos `.http` definitivos con estas rutas (sin barra, `page`/`size`).
