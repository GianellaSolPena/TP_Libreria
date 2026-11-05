# Design

## Context

Ver proposal.md (Why). Estado real de `parcial/` al cerrar C-07 (revisado línea por línea; números de línea del archivo):

**Inventario de lecturas con relaciones — todas ya precargan dentro del repositorio:**

| Lectura (respuesta) | Método | Precarga actual | N+1 hoy |
|---|---|---|---|
| Detalle de venta (`GET /ventas/{id}`, `POST /ventas`) | `ventas/repository.py:16` `get_detalle` | `joinedload(Venta.cliente)` (l. 26) + `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)` (l. 27); sin filtro de baja → muestra libros dados de baja | No (2 SELECT fijos) |
| Listado de ventas, `/mis-ventas`, `/clientes/{id}/ventas` (`VentaRead` con cliente) | `ventas/repository.py:33` `listar` | `joinedload(Venta.cliente)` (l. 34) | No |
| Detalle de libro (alta, PATCH, reponer, `GET /libros/{id}`) | `libros/repository.py:22` `get_detalle` | `joinedload` editorial y género + `selectinload(autorias).joinedload(autor)` (l. 27-31) | No |
| Catálogo y `/{editoriales,generos,autores}/{id}/libros` (`LibroRead`) | `libros/repository.py:61` `listar_vigentes` | `joinedload` editorial y género (l. 74) | No |
| Cliente con perfil (alta, GET, PATCH) | `clientes/repository.py:13` `get_con_perfil` | `joinedload(Cliente.perfil)` (l. 17) | No |
| Listado de clientes | `clientes/repository.py:26` `listar_con_perfil` | `joinedload(Cliente.perfil)` (l. 29) | No |
| Usuarios, roles, eventos, movimientos | `usuarios/repository.py`, `MovimientoStockRepository` | Las respuestas no incluyen relaciones (sólo columnas; roles por `select(AsignacionRol.rol)`) | No |

**Conclusión**: la parte "precarga en el repositorio" del scope de C-08 **ya la cubrió C-07** (y C-04/C-06). No se encontró ningún N+1 real. Lo que sigue abierto:

1. Los 26 `Relationship` de `app/modules/*/models.py` usan la carga por defecto (`lazy="select"`). En async un acceso no precargado no produce N+1 sino `MissingGreenlet` → 500; no hay garantía declarativa de "ninguna lectura depende de la carga perezosa" (PDF p. 13 y p. 20).
2. No existe el caso C-15 (2 vs 4 renglones) ni `parcial/evidencia/`. El `.http` del TP `test/C-07_consultas_fijas.http` compara 1 vs 2 renglones con ids frágiles.
3. Repaso final (CHANGES C-08): verificado en lectura de código — paginación con `total` de los mismos filtros (`libros/repository.py:_filtros`, `ventas.contar(cliente_id)`), `ILIKE` con parámetro ligado, `IdPath` y `genero_id` con `le=2**31-1`, bcrypt en `to_thread`, `asyncio.sleep` en el aviso, todos los handlers `async def`. El único desvío es formal: el escenario de `capas-persistencia` pide `grep` vacío de la sesión **también en routers**, pero cada router declara `get_uow(session: AsyncSession = Depends(get_session))`, que es justamente lo que el PDF exige ("el router construye el Unit of Work con una dependencia").

Restricciones heredadas: capas y UoW de C-04/C-07 (repos con `flush`, el UoW confirma, `expire_on_commit=False`), `Pagina` con conteo aparte, errores traducidos en el router, autorización de C-06 (2 SELECT por petición autenticada: usuario + roles vigentes). Sin pytest (DD-01): la verificación son `.http` + consola.

## Goals / Non-Goals

**Goals:**
- Hacer imposible, por declaración del modelo, una carga diferida silenciosa.
- Demostrar C-15 con evidencia reproducible que no dependa de ids del seed.
- Dejar el repaso final registrado y la spec de capas coherente con el código y el PDF.

**Non-Goals:**
- Reescribir repositorios o servicios que ya precargan bien.
- Cambiar contratos de respuesta, esquema o migraciones.
- `seed.py`, renumeración definitiva C-01..C-16 y retiro de `seed.sql` / `.http` del TP (C-09).
- Escapar `%`/`_` en la búsqueda por título (no es inyección; el PDF sólo pide parámetros ligados y C-16 ya pasa).
- Contador de consultas como test automatizado (no hay pytest).

## Decisions

### D1 — Estrategia de carga por cardinalidad (se conserva la de C-07)
- **A-uno** (`Venta.cliente`, `Libro.editorial`, `Libro.genero`, `Cliente.perfil`, `RenglonVenta.libro`, `LibroAutor.autor`): `joinedload`. Un JOIN no multiplica filas, así que es seguro con `LIMIT/OFFSET` en los listados paginados.
- **Colecciones** (`Venta.renglones`, `Libro.autorias`): `selectinload` (una consulta extra con `IN (...)` de los ids padre). Se descarta `joinedload` de colecciones: multiplica filas, obliga a `.unique()` y, combinado con `LIMIT`, SQLAlchemy envuelve la consulta en una subconsulta (y un `LIMIT` sin esa envoltura cortaría renglones). Ningún listado paginado precarga colecciones hoy; si alguno lo necesitara, va con `selectinload`.
- Anidado: `selectinload(colección).joinedload(a-uno)` → la consulta de la colección ya trae el libro/autor por JOIN; total del detalle de venta = 2 SELECT, independiente de los renglones.
- `populate_existing=True` se mantiene en los `get_detalle`/`get_con_perfil`: tras escribir en el mismo bloque (alta de venta, PATCH) la lectura refresca los objetos del mapa de identidad.
- Alternativa descartada: `subqueryload` (repite la consulta padre; sin ventaja sobre `selectinload` en PostgreSQL).

### D2 — Blindaje en el modelo: `lazy="raise_on_sql"` en todas las relaciones (ver QA-01)
Se agrega `"lazy": "raise_on_sql"` a `sa_relationship_kwargs` de los 26 `Relationship` (fusionando con los kwargs existentes de `usuarios/models.py`: `foreign_keys`, `uselist`). Las opciones por consulta (`joinedload`/`selectinload`) siguen sobrescribiendo la estrategia, así que los métodos actuales no cambian.
- `raise_on_sql` en vez de `raise`: un a-uno cuyo objeto ya está en el mapa de identidad se resuelve sin SQL (no es carga perezosa ni N+1) y evita falsos positivos; cualquier acceso que necesitaría una consulta lanza `InvalidRequestError` nombrando la relación.
- Alternativa: `raiseload("*")` en cada método de repositorio. Descartada como mecanismo principal: es opt-in por consulta (un método nuevo sin la opción vuelve a la carga perezosa) y agrega ruido a todos los métodos.
- Alternativa: no tocar modelos y confiar en la revisión. Descartada: el PDF dice "Carga perezosa: Prohibida" como requisito; la declaración en el modelo lo hace verificable con un `grep` y falla temprano.
- El modelo es del dominio de C-03, pero el cambio es sólo ORM (sin DDL, Alembic no lo detecta): `alembic check`/autogenerate debe seguir sin diferencias.

### D3 — Medición de consultas: `SQL_ECHO=true` en la consola de uvicorn (ver QA-02)
- Fuente de verdad: el eco del motor (`create_async_engine(echo=SQL_ECHO)`, C-02). Se cuentan las líneas de sentencia (`SELECT`, `INSERT`, `UPDATE`) entre el inicio y el fin de cada petición; `BEGIN (implicit)`/`COMMIT` no son consultas a contar pero se dejan en la evidencia.
- Esperado para un VENDEDOR en `GET /ventas/{id}`: 2 SELECT de la sesión (usuario, roles vigentes; C-06) + 2 SELECT del detalle = **4**, igual para 2 y 4 renglones (para la dueña: +1 `get_dueno` = 5, también fijo). El número exacto se confirma en el apply; lo normativo es que sea igual en ambos detalles.
- Sin pytest (DD-01). Un contador con `event.listen(engine.sync_engine, "before_cursor_execute", ...)` queda como chequeo opcional fuera de lo entregable (QA-02).

### D4 — Caso C-15 independiente de los ids del seed
`parcial/test/C-15_detalle_consultas_fijas.http`, con las mismas precondiciones que `test/libros_clientes_ventas.http` de C-07 (servidor con `SQL_ECHO=true`, ADMIN dado por psql porque `seed.py` llega en C-09, limpieza sólo de filas con prefijo de prueba `c08.`): login de ADMIN y de VENDEDOR (`# @name`), alta de 4 libros y un cliente de prueba (ids por `{{nombre.response.body.id}}`), `POST /ventas` con 2 renglones y otro con 4 (cantidad 1), y `GET /ventas/{{ventaN.response.body.id}}` para cada una, con la respuesta y "misma cantidad de SELECT que el anterior" en comentario. Un tercer pedido opcional: dar de baja (ADMIN) un libro vendido y repetir el detalle → mismo conteo y título visible. La salida de consola se guarda en `parcial/evidencia/C-15_consultas_detalle_venta.txt`.

### D5 — Repaso final como checklist de verificación, no como refactor
Los puntos del repaso (paginación, búsqueda ligada, `int4`, `async def`, bloqueos, `grep`) se ejecutan como chequeos con comando y resultado anotado en tasks.md; sólo se corrige código si un chequeo falla. El `grep` de capas se reformula en la spec (delta de `capas-persistencia`): servicios sin ninguna referencia a la sesión; routers sólo en `get_uow`/`get_libros_uow` (y la fábrica en `get_intentos_uow`, DD-09) y sin `commit(`/`rollback(` (QA-04).

### D6 — Dependencias `get_uow` sincrónicas se mantienen (ver QA-05)
Son dependencias, no handlers; sólo construyen un objeto. FastAPI las corre en el threadpool: no bloquean el bucle. Convertirlas a `async def` es cosmético y toca 7 routers ya verificados.

## Risks / Trade-offs

- [Una precarga olvidada pasa de `MissingGreenlet` a `InvalidRequestError`, ambos 500] → es un error de programación, no de entrada; se detecta en la re-ejecución completa de los `.http` de C-05/C-06/C-07 tras el blindaje (tarea obligatoria). El beneficio es que el error nombra la relación.
- [El flush puede necesitar cargar una colección: `session.delete()` de un padre con hijos, o reasignar una relación en un objeto persistente] → hoy ningún servicio llama a `BaseRepository.delete` (libros usa baja lógica; roles se revocan con `update`) ni reasigna relaciones de objetos persistentes; `venta.renglones = [...]` es sobre una venta transitoria (sin SQL). Si en el futuro se usa `delete`, precargar la colección o declarar `passive_deletes`. Se anota en el docstring de `BaseRepository.delete` sólo si el apply lo confirma.
- [Escenario de C-03 "Navegación recíproca" deja de funcionar sin precarga] → la delta de `modelo-datos` lo reformula con precarga explícita; no hay ningún `.http` que dependa de ello.
- [Ids/stock del seed cambian en C-09] → C-15 usa ids de la respuesta; C-09 regenera la evidencia sobre `seed.py` (QA-03).
- [El conteo varía por quién consulta (personal 4, dueña 5)] → C-15 usa el mismo usuario para los dos detalles.
- [`ILIKE` con `%`/`_` del usuario actúa como comodín] → no es inyección (parámetro ligado); fuera de alcance (Non-Goals).

## Migration Plan

Sin migraciones ni cambios de esquema. Despliegue: no aplica (`despliegue/` no se toca). Reversión: quitar `"lazy": "raise_on_sql"` de los kwargs; los `.http` y la evidencia no afectan al runtime.

## Open Questions

**RESUELTAS (2026-11-05)**: el usuario aceptó la recomendación de QA-01..QA-05; las specs y tasks ya las reflejan y no requieren ajuste. Falta el visto bueno explícito para el apply (governance MEDIO).

- **QA-01 (blindaje de la carga perezosa)** — ¿(A) `lazy="raise_on_sql"` en todos los modelos, (B) `raiseload("*")` por consulta en cada método de repositorio, o (C) no tocar código y sólo documentar la revisión? **Recomendación: (A)**: una sola declaración por relación, verificable con `grep`, no depende de recordar la opción en métodos nuevos; (C) cumple en la práctica pero no deja garantía. Con (C) se eliminan las tareas del grupo 2 y la delta de `modelo-datos`.
- **QA-02 (cómo contar)** — ¿Sólo `SQL_ECHO=true` (lo que pide el PDF) o además un script con contador de eventos de SQLAlchemy? **Recomendación**: sólo `SQL_ECHO` como evidencia entregable; el contador, si se quiere, como script descartable en el scratchpad, no en `parcial/` (no es pedido y engrosa el zip).
- **QA-03 (dueño de la evidencia C-15)** — CHANGES la pone en la verificación de C-08 y en el scope de C-09. **Recomendación**: C-08 crea el `.http` C-15 y una evidencia sobre sus propios datos de prueba (`c08.`); C-09 la regenera tras `python seed.py` y renumera/retira `C-07_consultas_fijas.http` del TP.
- **QA-04 (`grep` de capas en routers)** — ¿Reformular el escenario de `capas-persistencia` (routers sólo con la sesión en la dependencia que construye el UoW) o mover la construcción del UoW fuera de los routers (p. ej. a `app/core/` o al `unit_of_work.py` de cada módulo) para que el `grep` literal dé vacío? **Recomendación: reformular** (delta incluida): el PDF exige que el router construya el UoW con una dependencia; moverla es churn en 7 módulos ya verificados.
- **QA-05 (`get_uow` sincrónicas)** — **Recomendación**: mantenerlas `def` (D6). Alternativa: `async def` por uniformidad.
