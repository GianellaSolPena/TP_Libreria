# Design

## Context

Estado observado en `parcial/` (tras C-02):

- `app/core/database.py`: `get_session` toma la fábrica de `app.state`, **confirma** al salir y revierte con excepción (marcado `TODO C-04`).
- `editoriales`, `generos`, `autores`: `service.py` recibe `AsyncSession`, consulta con `select`, hace `session.rollback()` y lanza `HTTPException` (404/409) desde el servicio; esquemas `SQLModel` sin `extra="forbid"`; rutas con barra final (`"/"`); listados `list[...]` con `limit`/`offset`.
- `editoriales` y `generos` exponen `/{id}/libros` llamando a `libros.service.listar(session, ...)`; `autores` hace su `/{id}/libros` con `select(LibroAutor)` en su servicio.
- `libros` y `clientes` **dependen del commit de `get_session`** (sólo hacen `flush`); `ventas` confirma por su cuenta. Los tres migran en C-07.
- Unicidad en la base: `editorial.nombre` y `genero.nombre` con `uq_*` (migraciones 0001/0002). `autor` no tiene restricción de unicidad.

Restricciones: reglas duras 1, 5 y 7 de `CLAUDE.md`; PDF Ej. 3 y 6; C-03 corre en paralelo (no se tocan modelos ni migraciones).

## Goals / Non-Goals

**Goals:**
- Base reutilizable en `app/core/` (repositorios, UoW, paginación, errores) que C-05..C-07 usan sin cambios.
- `editoriales`, `generos`, `autores` como módulos de referencia del patrón de capas completo.
- `get_session` sin confirmar ni revertir, sin romper `libros`/`clientes`/`ventas`.

**Non-Goals:**
- `requiere_rol("ADMIN")` en POST/PATCH (C-06; por ahora quedan abiertos, como en el TP).
- `/{editoriales,generos,autores}/{id}/libros` con envoltorio y sin dados de baja (C-07, Q-18).
- Usar `SoftDeleteRepository` en algún módulo (lo estrena `Libro` en C-07).
- Modelos, columnas, índices o migraciones (C-03). `.http` definitivos (C-09).

## Decisions

### D1 — `BaseRepository[T]` con un único punto de filtrado
`BaseRepository(Generic[T])` recibe `session` y `model` (los genéricos se borran en runtime). Todas las lecturas parten de `_select()` / `_condiciones()`, para que la subclase con baja lógica filtre en un solo lugar y `get_all` y `count` usen **los mismos filtros**.

```python
class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]) -> None
    def _condiciones(self) -> list[ColumnElement[bool]]      # [] en la base
    async def get_by_id(self, id: int) -> T | None           # select + where id + _condiciones
    async def get_all(self, *, offset: int = 0, limit: int | None = None) -> list[T]  # order_by id
    async def count(self) -> int                              # select count(*) + _condiciones
    async def add(self, entidad: T) -> T                      # session.add + flush
    async def update(self, entidad: T, cambios: dict[str, Any]) -> T  # setattr + flush
    async def delete(self, entidad: T) -> None                # session.delete + flush
```

`get_by_id` usa `select` (no `session.get`) para aplicar `_condiciones`. Los métodos específicos de cada entidad (nombrados por lo que traen, con su precarga adentro) viven en el repositorio del módulo. Alternativa descartada: `get_all(**filtros)` genérico por kwargs; es más opaco y C-07 necesita filtros propios (ILIKE, `genero_id`) igual.

### D2 — `SoftDeleteRepository[T]` e interfaz asumida de C-03
Hereda de `BaseRepository[T]`; `_condiciones()` agrega `model.borrado_en.is_(None)`; suma `get_by_id_including_deleted(id)` (sin el filtro) y `soft_delete(entidad)` (asigna `datetime.now(UTC)` a `borrado_en` y hace `flush`). `delete` físico se hereda pero ningún servicio de entidades con baja lógica lo usa.

**Interfaz asumida (la crea C-03, no C-04)**: todo modelo usado con `SoftDeleteRepository` tiene la columna `borrado_en: datetime | None` (`timestamptz`, nula = vigente). C-04 no referencia `Libro`; sólo depende del nombre del atributo. Si C-03 usara otro nombre, se ajusta una constante (`COLUMNA_BAJA = "borrado_en"`). No se puede probar contra una tabla real hasta C-03/C-07: en C-04 se verifica que importe y tipe.

### D3 — `UnitOfWork` base y UoW por módulo
```python
class UnitOfWork:
    def __init__(self, session: AsyncSession) -> None
    async def __aenter__(self) -> Self
    async def __aexit__(self, exc_type, exc, tb) -> None:   # exc -> rollback; si no -> commit; nunca close
```
Cada módulo define `XxxUnitOfWork(UnitOfWork)` en `unit_of_work.py` y crea sus repositorios en `__init__` con la misma sesión (`self.editoriales = EditorialRepository(session)`). La dependencia que lo construye está en `router.py` del módulo (el PDF dice "el router construye el Unit of Work con una dependencia"):

```python
def get_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> EditorialesUnitOfWork: ...
UowDep = Annotated[EditorialesUnitOfWork, Depends(get_uow)]
```
Si el commit mismo falla, `__aexit__` revierte y relanza. El UoW no se reabre: una operación = un `async with`.

### D4 — `get_session` puro + dependencia transitoria
`get_session` queda: `async with factory() as session: yield session` (cierra; no confirma ni revierte; al cerrar, SQLAlchemy descarta lo no confirmado). Para `libros`, `clientes` y `ventas`, que todavía dependen del commit implícito, se agrega en `database.py` `get_session_tp` con el comportamiento anterior, comentada `# TRANSITORIO: se borra en C-07` y usada **sólo** por esos tres routers (cambio de import). Alternativa descartada: dejar el commit en `get_session` hasta C-07 (contradice el requisito de capas y el UoW confirmaría dos veces). Alternativa descartada: migrar ya libros/clientes/ventas (scope de C-07 y depende de C-03).

`editoriales`/`generos` `/{id}/libros` siguen llamando a `libros.service.listar(session, ...)` con `get_session` (sólo lectura, no necesita commit); su verificación de existencia (404) pasa por el servicio del módulo con el UoW. FastAPI cachea la dependencia por petición, así que UoW y lectura comparten la misma sesión. `autores` `/{id}/libros` mueve su consulta a `AutorRepository.listar_autorias(autor_id, offset, limit)` (precarga `joinedload(LibroAutor.libro)` dentro del método). Estas rutas conservan su respuesta `list[...]` y `limit`/`offset` hasta C-07 (excepción transitoria a la regla 1 sólo en las dos rutas que delegan en `libros`).

### D5 — Errores del dominio y traducción en el router
Nuevo `app/core/errores.py` (el PDF no lo lista en la estructura, pero sólo enumera los archivos obligatorios; KB 08 prevé "un helper/manejador común"):

- Excepciones de dominio sin HTTP: `NoEncontrado(mensaje)`, `Conflicto(mensaje)`, `PaginaInexistente(page, pages)`.
- `traducir_errores(conflicto: str, conflicto_fk: str | None = None)`: gestor de contexto (sync, se usa con `with` alrededor del `await service...` en el handler) que convierte:
  - `NoEncontrado` → 404 con su mensaje; `Conflicto` → 409 con su mensaje; `PaginaInexistente` → 422 «La página N no existe: hay M».
  - `IntegrityError` con SQLSTATE `23505` → 409 `conflicto`; `23503` → 409 `conflicto_fk` (o genérico); otro → 409 «Los datos violan una restricción». Nunca se usa `str(exc)` ni `exc.orig`.
  - Lo resuelve con `HTTPException`, cuerpo `{"detail": "<mensaje>"}` (igual que el TP).

Así la traducción está visiblemente en el router (p. 9) y el mensaje propio es por operación. Alternativa descartada: `app.exception_handler(IntegrityError)` global en `main.py`: no sabe qué entidad chocó y obligaría a un mensaje genérico. El SQLSTATE se lee con `getattr(exc.orig, "sqlstate", None)` (patrón del TP, compatible con asyncpg vía el adaptador de SQLAlchemy).

Mensajes: «Ya existe una editorial con ese nombre», «Ya existe un género con ese nombre», «Editorial no encontrada», «Género no encontrado», «Autor no encontrado» (los del TP, SU-03).

### D6 — Paginación
`app/core/paginacion.py`:
- `ParametrosPagina` (dataclass o modelo) con `page: Annotated[int, Query(ge=1)] = 1` y `size: Annotated[int, Query(ge=1, le=100)] = 20`; alias `PaginaDep = Annotated[ParametrosPagina, Depends()]`. `page` también se acota `le=2**31-1` para que `offset` nunca desborde.
- `Pagina(BaseModel, Generic[T])`: `items: list[T]`, `total`, `page`, `size`, `pages`.
- `calcular_paginas(total, size) = max(1, ceil(total / size))` y `offset = (page - 1) * size`.
- Flujo en el servicio, dentro de un solo `async with uow`: `total = count()` → `pages` → si `page > pages` lanza `PaginaInexistente` → `get_all(offset, limit=size)`. El orden evita leer filas para una página que no existe.
- El servicio devuelve `Pagina[Entidad]` sin conocer HTTP; el router declara `response_model=Pagina[EditorialRead]` (Pydantic valida desde atributos).

### D7 — Contratos y rutas
- Esquemas de entrada como `pydantic.BaseModel` con `model_config = ConfigDict(extra="forbid")` (contratos separados de las tablas; se dejan de heredar de `SQLModel`). Textos `min_length=1`. Los `Update` conservan el validador del TP que rechaza `null` explícito; el servicio aplica `model_dump(exclude_unset=True)` vía `repo.update`.
- Salidas `XxxRead` con `from_attributes=True`.
- Ids de ruta con un alias común `IdPath = Annotated[int, Path(ge=1, le=2_147_483_647)]`, definido en `app/core/errores.py` junto a la política de entrada inválida. Id `<= 0` → 422 (fuera de contrato: los ids son `serial`); `> int4` → 422 (evita `DataError` → 500).
- Rutas: `@router.post("")`, `@router.get("")`, `@router.get("/{editorial_id}")` con `prefix="/editoriales"`. Con barra final FastAPI responde 307 hacia la ruta sin barra (comportamiento por defecto, aceptable según IN-05).
- PATCH sin campos (`{}`) → 200 sin cambios (no hay regla en el PDF que lo prohíba).
- Rutas extra del TP conservadas según la propuesta de Q-10: `GET /autores` (paginado), `GET /{recurso}/{id}`, `PATCH /generos/{id}`.

## Risks / Trade-offs

- [Cambio de forma de los listados y de las rutas] → los `.http` del TP (`test/C-0x`) que usan `/editoriales/` o `limit` dejan de coincidir; se rehacen en C-09. Mitigación: verificación manual en este change.
- [Dependencia transitoria `get_session_tp`] → dos formas de obtener sesión conviviendo hasta C-07. Mitigación: comentario `TRANSITORIO` y tarea explícita en C-07 para borrarla; `grep get_session_tp` debe quedar vacío al cerrar C-07.
- [POST/PATCH del catálogo sin autorización] → cualquiera puede crear editoriales hasta C-06, igual que en el TP. Aceptado: autorización es C-06.
- [`SoftDeleteRepository` sin probar contra la base] → se valida recién en C-07. Mitigación: interfaz asumida explícita (D2).
- [Q-10 sigue abierta] → si la cátedra pide quitar las rutas extra, se borran handlers sin tocar capas.
- [Archivo `app/core/errores.py` fuera de la lista del PDF] → la estructura del PDF lista los obligatorios; un archivo de apoyo adicional no la contradice. Si se prefiere no agregarlo, el contenido puede ir en `app/core/unit_of_work.py`, a costa de mezclar responsabilidades.
