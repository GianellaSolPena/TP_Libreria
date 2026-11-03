# Proposal

## Why

El PDF (Ej. 6, p. 8-9 y 11) exige que todos los módulos pasen a capas Router → Service → UoW → Repository → Model y que los servicios dejen de recibir la sesión; el Ej. 3 exige contratos separados con `extra="forbid"`, PATCH parcial y listados con el envoltorio `{items, total, page, size, pages}`. Hoy `parcial/` conserva el patrón del TP: los servicios reciben `AsyncSession`, hacen `rollback()`, lanzan `HTTPException` y `get_session` confirma la transacción. C-04 construye la base común (repositorios genéricos, Unit of Work, paginación y traducción de errores) y la aplica primero al catálogo de referencia (editoriales, géneros, autores) para que C-05..C-07 la reutilicen.

## What Changes

- **Nuevo** `app/core/repository.py`: `BaseRepository[T]` (constructor con sesión y clase del modelo; `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`; `add`/`update`/`delete` hacen `flush()`, nunca `commit()`) y `SoftDeleteRepository[T]` (hereda; filtra los dados de baja; agrega `get_by_id_including_deleted` y `soft_delete`). Se deja listo pero sin uso: lo estrena `Libro` en C-07.
- **Nuevo** `app/core/unit_of_work.py`: `UnitOfWork` base como gestor de contexto asincrónico (confirma al salir, revierte con excepción, no cierra la sesión).
- **Nuevo** `app/core/paginacion.py`: parámetros `page`/`size` reutilizables, envoltorio genérico `Pagina[T]` y cálculo de páginas (cero resultados = una página vacía; página de más → 422 «La página N no existe: hay M»).
- **Nuevo** `app/core/errores.py` (no figura en la estructura del PDF; ver design): errores del dominio y un traductor que usa el router (`IntegrityError` → 409 con mensaje propio, sin texto de la base).
- **BREAKING (interno)** `get_session` deja de confirmar y revertir: sólo entrega y cierra la sesión; confirma el UoW. Para no romper `libros`, `clientes` y `ventas` (que migran en C-07) se agrega una dependencia transitoria con el comportamiento viejo, marcada para borrar en C-07.
- **Refactor** de `editoriales`, `generos`, `autores` a `schemas` / `repository` / `unit_of_work` / `service` / `router`: contratos Pydantic con `extra="forbid"`, PATCH con `exclude_unset`, ids de ruta acotados a `int4`, rutas sin barra final (IN-05), listados paginados.
- **BREAKING (API)** `GET /editoriales`, `/generos`, `/autores` devuelven el envoltorio en lugar de una lista y aceptan `page`/`size` en lugar de `limit`/`offset`; las rutas pasan de `/editoriales/` a `/editoriales`.
- Se conservan las rutas del TP que el PDF no lista (`GET /autores`, `GET /{editoriales,generos,autores}/{id}`, `PATCH /generos/{id}`) según la propuesta de Q-10.

Fuera de alcance: autorización ADMIN de los POST/PATCH (C-06), `/{editoriales,generos,autores}/{id}/libros` con envoltorio y filtro de baja (C-07, Q-18), modelos y migraciones (C-03), archivos `.http` (C-09).

## Capabilities

### New Capabilities
- `capas-persistencia`: repositorios genéricos (`BaseRepository[T]`, `SoftDeleteRepository[T]`), Unit of Work base y por módulo, y el reparto de responsabilidades entre router, servicio, UoW y repositorio.
- `paginacion-listados`: envoltorio `{items, total, page, size, pages}`, límites de `page`/`size` y página inexistente → 422.
- `errores-api`: traducción de errores del dominio y de la base a códigos HTTP con mensajes propios; ninguna entrada inválida termina en 500.
- `catalogo-referencias`: alta, consulta, modificación parcial y listado de editoriales, géneros y autores.

### Modified Capabilities
- `configuracion-ciclo-vida`: el requisito "Una sesión por petición" pasa a exigir que `get_session` no confirme ni revierta (lo hace el Unit of Work).

## Impact

- Código: `parcial/app/core/{repository,unit_of_work,paginacion,errores,database}.py`; `parcial/app/modules/{editoriales,generos,autores}/*`; cambio de una línea de import en los routers de `libros`, `clientes`, `ventas` (dependencia transitoria).
- API: listados de editoriales/géneros/autores cambian de forma (envoltorio) y de parámetros; rutas sin barra final (con barra, FastAPI responde 307 a la ruta sin barra).
- Sin cambios de esquema ni dependencias nuevas. Sin dependencia de C-03: `SoftDeleteRepository` asume la columna `borrado_en` que crea C-03 (interfaz en design.md).
- Verificación manual (los `.http` definitivos llegan en C-09): 409 por nombre duplicado, 422 por campo extra, PATCH parcial, listado paginado y página de más.
