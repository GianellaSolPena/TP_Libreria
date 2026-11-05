# Design

## Context

Motivo y alcance: ver `proposal.md`. Requisitos: `specs/libros-stock`, `specs/clientes`, `specs/ventas` y los deltas de `autorizacion`, `capas-persistencia` y `errores-api`.

Estado actual de `parcial/` (observado):
- `libros`, `clientes`, `ventas`: servicios del TP que reciben `AsyncSession`, hacen `flush`/`rollback` y lanzan `HTTPException`; `ventas.service.crear` hace `session.commit()` explícito, no descuenta stock ni crea movimientos. Rutas con barra final y listados `limit`/`offset` en lista plana. `libros` no tiene `repository.py` ni `unit_of_work.py`; `clientes` tiene `ClienteRepository` (lo usa `UsuariosUnitOfWork` en el registro de C-05); `ventas` no tiene repositorio.
- Routers de esos módulos: dependencia `get_session_tp` (confirma al salir, «TRANSITORIO: se borra en C-07») mientras `requiere_rol` → `get_usuario_actual` usa `get_session`: **dos sesiones por petición** (C-06 D10). `GET /ventas/{id}` con `personal` a nivel de router (C-06 QA-07).
- `editoriales`/`generos` exponen `GET /{id}/libros` con `libros.service.listar` y lista plana (marcado TRANSITORIO); `autores` con `AutorRepository.listar_autorias` y lista plana.
- Core disponible: `BaseRepository`/`SoftDeleteRepository` (C-04, `SoftDeleteRepository` aún sin uso), `UnitOfWork`, `Pagina`/`PaginaDep`/`calcular_paginas`/`PaginaInexistente`, `traducir_errores` (23505/23503 → 409, `NoEncontrado` 404, `Conflicto` 409), `IdPath` (int4), `SesionActual(usuario, roles_vigentes, roles_token)`, `solo_admin`, `personal`, `UsuarioActualDep`. El logger `app` ya tiene handler propio en `main.py` (visible con uvicorn).
- Esquema (C-03): `libro.borrado_en` + `ux_libro_isbn_vigente` parcial, CHECK `stock >= 0`, `movimiento_stock` con `usuario_id` NOT NULL, CHECK `cantidad <> 0` y disparador 0004 que rechaza UPDATE/DELETE (ERRCODE `restrict_violation`). Nada de C-07 necesita cambios de esquema.
- `test/seed.sql` del TP inserta libros con `stock` sin movimientos y ya no es compatible con la invariante; lo retira C-09.

Restricciones: reglas duras de `CLAUDE.md` (capas, sin pytest, rutas en `parcial/`), Ej. 3/5/6/8 del PDF (el PDF manda), decisiones de C-04 (patrón de módulo, traducción en el router), C-05 (D8: el bloque de lectura de la dependencia libera la conexión) y C-06 (D1-D4, matriz).

## Goals / Non-Goals

**Goals:**
- Una sola sesión por petición en todo el sistema; ningún `commit`/`rollback`/`AsyncSession` en servicios ni routers (salvo DD-09).
- RN-10 en un solo bloque: o quedan venta, renglones, descuentos y movimientos, o nada.
- Una única función que escribe `libro.stock`, que siempre agrega el movimiento en la misma transacción.
- Control de dueño en el servicio de `GET /ventas/{id}`.

**Non-Goals:**
- Cantidad fija de consultas verificada con `SQL_ECHO` y repaso de N+1 (C-08; aquí sólo se conserva la precarga que ya existe).
- `seed.py`, `.http` definitivos C-01..C-16 y retiro de `seed.sql` (C-09).
- Anulación/devolución de ventas, ajustes manuales de stock, filtros extra en listados (el PDF no los pide).
- Concurrencia como requisito evaluado ("No se evalúa la concurrencia", PDF p. 2); sólo se evita lo que no cuesta diseño extra (D4, QA-01).

## Decisions

### D1 — Una sola sesión: se borra `get_session_tp`
Los tres routers construyen su UoW con `get_uow(session: Annotated[AsyncSession, Depends(get_session)])`, igual que `editoriales` (C-04). Como `get_usuario_actual` depende de la misma `get_session` y FastAPI la cachea por petición, autorización y UoW comparten sesión y conexión (Ej. 6, sección 6.7). `get_session_tp` se borra de `app/core/database.py`; `grep -rn get_session_tp parcial/app` debe quedar vacío.
- Los servicios dejan de lanzar `HTTPException`: lanzan `NoEncontrado`/`Conflicto`/`SinPermiso` y el router envuelve con `traducir_errores(...)`.

### D2 — Repositorios y Unit of Work por módulo
| Módulo | Repositorios (archivo) | UoW compone |
|---|---|---|
| `libros` | `LibroRepository(SoftDeleteRepository[Libro])`, `LibroAutorRepository`, `MovimientoStockRepository` (`libros/repository.py`) | libros, autorías, movimientos, + `EditorialRepository`, `GeneroRepository`, `AutorRepository` (sólo `get_by_id` para el 404 de `/{x}/{id}/libros`) |
| `clientes` | `ClienteRepository` (existe), `PerfilClienteRepository` (`clientes/repository.py`) | clientes, perfiles, + `VentaRepository` (para `/clientes/{id}/ventas`) |
| `ventas` | `VentaRepository` (`ventas/repository.py`; renglones por cascada de la relación) | ventas, + `ClienteRepository`, `LibroRepository`, `MovimientoStockRepository` |

- Composición entre módulos: ya hay precedente (`UsuariosUnitOfWork` usa `ClienteRepository`). Los repositorios sólo importan modelos, y cada UoW importa repositorios: no hay ciclos de importación.
- Métodos con nombre por lo que traen y precarga adentro (Ej. 6): `LibroRepository.get_detalle(id)` (editorial, género, autorías+autor; filtra baja), `listar_vigentes(filtros, offset, limit)` + `contar_vigentes(filtros)` con **los mismos filtros** (`titulo` ILIKE ligado `%texto%`, `genero_id`, `editorial_id`, `autor_id` vía `EXISTS` sobre `libro_autor`), `get_vigentes_por_ids(ids)`; `VentaRepository.get_detalle(id)` (cliente + renglones + libro **sin** filtro de baja, porque la precarga por relación no pasa por `_condiciones()` del repositorio), `listar(offset, limit, cliente_id=None)` + `contar(cliente_id=None)`, `get_dueno(id)` (sólo `cliente.usuario_id`, ver D7); `MovimientoStockRepository.listar_de_libro(...)` + `contar_de_libro(...)`; `ClienteRepository.get_con_perfil(id)`, `get_por_usuario(usuario_id)`.
- `MovimientoStockRepository` sobreescribe `update` y `delete` para lanzar `NotImplementedError` (sólo agregado también en el código; la base lo garantiza igual con el disparador).

### D3 — Punto único de escritura de stock
`LibroRepository.aplicar_movimiento(libro_id, cantidad, motivo, usuario_id, venta_id=None) -> int | None` es **el único código que escribe `libro.stock`**:
1. `UPDATE libro SET stock = stock + :cantidad WHERE id = :id AND borrado_en IS NULL AND stock + :cantidad >= 0 RETURNING stock` (sentencia ORM `update(Libro)` con parámetros ligados).
2. Si no devuelve fila → `None` (libro dado de baja o stock insuficiente; el servicio decide el mensaje con lo que ya leyó).
3. Si devuelve el stock nuevo → agrega `MovimientoStock(libro_id, venta_id, usuario_id, cantidad, motivo)` con `flush` y sincroniza el atributo `stock` del objeto `Libro` en memoria si está en la sesión (para que la respuesta muestre el valor nuevo sin otra consulta).
- Lo usan el alta (`+stock_inicial`, «Stock inicial»), la reposición (`+n`, «Reposición») y la venta (`-cantidad`, «Venta»). El alta inserta el libro con `stock=0` y después aplica el movimiento, así ni siquiera el INSERT escribe stock por fuera del punto único.
- `stock_inicial == 0` → no se llama (un movimiento de 0 violaría `CHECK cantidad <> 0`; la invariante 0 == suma vacía se cumple). Ver QA-03.
- Motivos como constantes del módulo `libros` (`MOTIVO_STOCK_INICIAL`, `MOTIVO_REPOSICION`, `MOTIVO_VENTA`; Q-07, ver QA-02).
- Por qué un `UPDATE` condicional y no "leer, restar en Python, escribir": ver D4.
- Alternativa descartada: un "servicio de stock" separado que reciba los repositorios — agrega una capa que el PDF no nombra; el repositorio es donde 08 ubica el punto único ("`libros` (repositorio/UoW)").

### D4 — Concurrencia del stock (riesgo explícito, QA-01)
El PDF describe la actualización perdida (dos ventas del último ejemplar leen `stock = 1` y escriben 0) y dice que no se evalúa. Opciones:
- (A) Leer-modificar-escribir con el ORM: literal al PDF; deja la actualización perdida (el CHECK impide negativos pero se vende un ejemplar inexistente y `stock` deja de coincidir con `SUM(movimientos)`, porque hay dos movimientos y un solo descuento).
- (B) `SELECT ... FOR UPDATE` de los libros antes de descontar: correcto, pero es "el bloqueo que la evita, tema de la próxima clase".
- (C) **Elegida (recomendada)**: `UPDATE` atómico condicional de D3. La base calcula `stock + cantidad` sobre el valor confirmado más reciente y toma el bloqueo de fila sólo durante la transacción de la venta; no hay lectura previa que pueda quedar vieja, así que la invariante `stock == SUM(movimientos)` se mantiene también con ventas simultáneas. No requiere niveles de aislamiento ni reintentos.
- Interbloqueo: dos ventas con los mismos libros en distinto orden podrían esperarse mutuamente; el servicio aplica los movimientos **ordenados por `libro_id`** para que todas tomen los bloqueos en el mismo orden.

### D5 — Registro de la venta (RN-09, RN-10) en un bloque
Router: `POST /ventas` con `personal` (router de personal), recibe `UsuarioActualDep` (misma instancia cacheada) y `BackgroundTasks`. Servicio `crear(uow, datos, actor)`:
```
async with uow:
    libros = await uow.libros.get_vigentes_por_ids(ids)       # una consulta; filtra baja
    faltan = ids - libros.keys() → Conflicto("Los libros [..] no existen o están dados de baja")
    renglones = [RenglonVenta(libro_id, cantidad, precio_unitario=libros[id].precio)]
    total = Σ cantidad × precio_unitario                       # Decimal
    venta = await uow.ventas.add(Venta(cliente_id, total, renglones=renglones))
        # cliente inexistente → 23503 en este flush → 409 "El cliente indicado no existe"
    for r in sorted(renglones, key=libro_id):
        if await uow.libros.aplicar_movimiento(r.libro_id, -r.cantidad, MOTIVO_VENTA, actor.id, venta.id) is None:
            raise Conflicto(f"No hay stock suficiente de «{titulo}»: hay {stock}, se pidieron {n}")
    detalle = await uow.ventas.get_detalle(venta.id)           # dentro del bloque, antes del commit
return detalle                                                 # el UoW confirmó al salir
```
- Cliente inexistente: lo detecta la FK (23503) sin consulta previa (05 §Manejo de errores: "FK inexistente 23503 → 409 en `POST /ventas`"); el router pasa `conflicto_fk="El cliente indicado no existe"`. Libros: hace falta leerlos igual (precio), así que la inexistencia o baja sale de esa lectura.
- Si un libro pasa la lectura pero se da de baja o se queda sin stock entre la lectura y el `UPDATE`, `aplicar_movimiento` devuelve `None` → 409 igual (el mensaje usa el stock leído).
- Cualquier excepción sale del `async with` → rollback de venta, renglones, descuentos y movimientos (RN-10); no queda ninguna escritura.
- El detalle se lee dentro del bloque (los `flush` ya lo hicieron visible en la transacción) para no abrir una transacción nueva después del commit.

### D6 — Aviso del comprobante (Ej. 8)
`avisar_comprobante(venta_id)` en `ventas/service.py`: `await asyncio.sleep(0.5)` + `logger.info("Comprobante de la venta %s enviado al cliente", venta_id)` con `logging.getLogger(__name__)` (cuelga de `app`, que ya tiene handler en `main.py`). El router lo agenda con `background_tasks.add_task(...)` **después** de que `service.crear` devolvió: si el servicio lanzó (409) o el commit falló, la línea `add_task` no se ejecuta → sin aviso. Starlette corre la tarea después de enviar la respuesta. La tarea no usa la sesión de la petición (ya cerrada).

### D7 — `GET /ventas/{id}` sin `requiere_rol` (RN-14, PDF p. 18)
El router de ventas se parte en `router_personal` (`dependencies=[Depends(personal)]`: `POST /ventas`, `GET /ventas`) y `router_autenticado` (sin rol: `GET /ventas/{id}`, `GET /mis-ventas`), ambos en el grupo `protegido` (control del cambio obligatorio). Servicio `obtener(uow, venta_id, sesion)`:
1. `es_personal = {VENDEDOR, ADMIN} & set(sesion.roles_vigentes)` (roles de la base, ya cargados por D1 de C-06; nunca `roles_token`).
2. Si no es personal: `dueno = await uow.ventas.get_dueno(venta_id)` (consulta liviana `venta JOIN cliente → cliente.usuario_id`); venta inexistente → `NoEncontrado` (404, QA-08); `dueno != sesion.usuario.id` → `SinPermiso("No podés ver una venta de otro cliente")` → 403.
3. Recién entonces `get_detalle(venta_id)` (404 si no existe, para el personal).
- Orden pedido por el PDF: "primero quién es y qué relación tiene con la venta, y recién después qué se devuelve": el detalle completo nunca se carga para quien no puede verlo.
- `SinPermiso` es un error de dominio nuevo en `app/core/errores.py`; `traducir_errores` lo traduce a 403.
- `GET /mis-ventas`: `cliente = clientes.get_por_usuario(usuario.id)`; sin ficha → página vacía (`total` 0, `pages` 1; QA-09); con ficha → `ventas.listar(cliente_id=...)` paginado.

### D8 — Libros: contratos y operaciones
- `LibroCreate` (`extra="forbid"`): `isbn`, `titulo` (no vacíos), `precio: Decimal(gt=0, max_digits=10, decimal_places=2)`, `stock_inicial: int(ge=0, le=2**31-1)`, `editorial_id`, `genero_id | None` (ids con `ge=1, le=2**31-1`), `autores: list[LibroAutorCreate]` con `min_length=1` (Fig. 1: `Libro 1 ── 1..* LibroAutor`; QA-04) y sin `autor_id` repetidos.
- Alta en un bloque: `libros.add(Libro(..., stock=0))` → `autorias.add(...)` por autor → `aplicar_movimiento(+stock_inicial, MOTIVO_STOCK_INICIAL, actor.id)` si > 0 → `get_detalle`. ISBN vigente repetido → 23505 → «Ya existe un libro vigente con ese ISBN»; editorial/género/autor inexistente → 23503 → «La editorial, el género o algún autor indicado no existe».
- `LibroUpdate` (`extra="forbid"`): sólo `titulo`, `precio` (PDF: "título y precio; el stock no"; QA-05); `null` → 422; `get_by_id` (filtra baja) → 404; `update(..., exclude_unset)`.
- `DELETE`: `get_by_id` (filtra baja) → 404; `soft_delete`; router `status_code=204`, sin cuerpo.
- `reponer`: `ReponerIn {cantidad: int(ge=1, le=2**31-1)}` (`extra="forbid"`); `get_by_id_including_deleted` → `None` 404; `borrado_en` → `Conflicto("No se puede reponer un libro dado de baja")` 409; `aplicar_movimiento(+n, MOTIVO_REPOSICION, actor.id)`. Respuesta `ReposicionRead {libro: LibroRead, movimiento: MovimientoRead}` (QA-10).
- `GET /libros/{id}/movimientos`: `get_by_id_including_deleted` → 404 sólo si no existe (QA-07); `Pagina[MovimientoRead]` ordenado por `cuando, id`.
- Catálogo: `GET /libros` → `Pagina[LibroRead]`; `GET /libros/{id}` → `get_detalle` (filtra baja → 404, Q-19). `titulo` se pasa como parámetro ligado (`ilike` con `%texto%`); `' OR '1'='1` es sólo texto → 0 resultados.
- `/{editoriales,generos,autores}/{id}/libros`: el router de cada módulo construye el `LibrosUnitOfWork` y llama a `libros.service.listar_por(...)`, que verifica existencia del padre (404) y lista con el mismo método filtrado de `GET /libros`; respuesta uniforme `Pagina[LibroRead]` (QA-06, QA-11). Se quitan los bloques TRANSITORIO de los tres routers y `AutorRepository.listar_autorias` si queda sin uso.

### D9 — Clientes
- Contratos con `extra="forbid"` (`usuario_id` no viaja: el vínculo sólo lo crea el registro, C-05). `ClienteUpdate`: `nombre`, `email`; `null` → 422.
- 409 de correo por UNIQUE (`uq_cliente_email`) sin consulta previa; `PATCH` con `email` de un cliente con usuario vinculado → 409 (QA-12 revisada).
- `POST /clientes/{id}/perfil`: `get_by_id` del cliente → 404 (recurso de la ruta); luego `perfiles.add` → segundo perfil 23505 → 409 «El cliente ya tiene un perfil». La unicidad sigue siendo de la base; la lectura previa es por el 404, no por la unicidad.
- `GET /clientes` (Q-10, conservada en C-06) y `GET /clientes/{id}/ventas` → `Pagina[...]` (QA-06).

### D10 — Errores nuevos en `app/core/errores.py`
- `SinPermiso(mensaje)` → 403.
- En `traducir_errores`, además de `IntegrityError`: `DBAPIError` con SQLSTATE `22003` (`numeric_value_out_of_range`) → 409 «El valor supera el máximo permitido» (p. ej. `stock + n` > int4 en una reposición, o un `total` que no entra en `NUMERIC(12,2)`). Hoy terminaría en 500 (RN-15). Se captura `DBAPIError` sólo para ese SQLSTATE y se re-lanza el resto.
- La violación del disparador (`restrict_violation`, 23001) no debería ocurrir (D2: el repositorio no ofrece update/delete); si ocurriera, `IntegrityError` → 409 genérico.

### D11 — Rutas sin barra final y montaje en `main.py`
`libros`: `router_publico` (`GET ""`, `GET "/{id}"`) y `router_admin` (`POST ""`, `PATCH`/`DELETE "/{id}"`, `POST "/{id}/reponer"`, `GET "/{id}/movimientos"`); `clientes`: un router con `personal`; `ventas`: `router_personal` y `router_autenticado`. `main.py` incluye `libros.router_publico` en `abierto` y el resto en `protegido`. `GET /libros/{id}/movimientos` (protegido) y `GET /libros/{id}` (abierto) no chocan: distinto path.

### D12 — Verificación sin pytest
`parcial/test/libros_clientes_ventas.http`. Como `seed.py` llega en C-09, la cabecera documenta el arranque (mismo método que `autorizacion.http` de C-06): registro de un ADMIN y dos clientes con usuario (Ana y otra), psql para darle ADMIN, alta de un VENDEDOR por `POST /usuarios` + cambio de contraseña; luego por API: editoriales/géneros/autores necesarios, cinco libros con `stock_inicial` (Rayuela 10 a 25000.00, Bestiario 1, etc.; los precios del PDF donde los fija, IN-03), clientes. Casos: C-06 (parte propia), C-10, C-11, C-12 (tres variantes), C-13, más 422 de contrato, `/mis-ventas` y movimientos. Tras cada caso de venta, una consulta psql en comentario:
```sql
SELECT l.id, l.stock, COALESCE(SUM(m.cantidad), 0) AS suma
FROM libro l LEFT JOIN movimiento_stock m ON m.libro_id = l.id
GROUP BY l.id HAVING l.stock <> COALESCE(SUM(m.cantidad), 0);   -- esperado: 0 filas
```
Se ajustan rutas con barra en `auth.http` y `autorizacion.http`. La concurrencia (D4) se demuestra opcionalmente con dos `psql` (una transacción sostiene un `UPDATE libro` mientras se envía la venta) o se justifica por lectura; no es caso del PDF.

## Risks / Trade-offs

- [Actualización perdida del stock] → UPDATE condicional atómico (D3/D4); si el usuario elige (A) en QA-01, queda documentado como limitación aceptada por el PDF.
- [Interbloqueo entre ventas con los mismos libros] → movimientos aplicados en orden de `libro_id` (D4).
- [Atributo `stock` desactualizado en memoria tras el UPDATE de D3] → el repositorio sincroniza el valor devuelto por `RETURNING` en el objeto de la sesión; las lecturas de detalle usan `populate_existing` como hoy.
- [Venta rechazada deja escrituras] → todas las escrituras en un `async with`; ningún `commit` intermedio (repositorios sólo `flush`); el `Conflicto` de stock se lanza dentro del bloque. Verificado con C-11 + consulta de la invariante.
- [Aviso de una venta no confirmada] → `add_task` después de que el servicio devolvió (D6); un fallo del commit en `__aexit__` propaga antes.
- [Libro dado de baja en el detalle de ventas viejas] → `get_detalle` de ventas precarga `RenglonVenta.libro` por relación, sin el filtro de `SoftDeleteRepository` (C-13: "la venta vieja sigue mostrando el título").
- [ISBN reutilizado] → `ux_libro_isbn_vigente` (C-03) hace de garante; el 409 sale del 23505, sin consulta previa.
- [Movimientos modificados desde la app] → `MovimientoStockRepository` sin `update`/`delete` (D2) + disparador 0004 en la base.
- [Desborde int4/NUMERIC] → contratos acotados a int4 y SQLSTATE 22003 → 409 (D10).
- [Cliente dueño por `cliente.usuario_id`] → una ficha sólo se vincula por el registro (C-05) o el seed (C-09); un cliente cargado por el personal no tiene usuario y nadie lo ve como "propio".
- [BREAKING en rutas y contratos] → los `.http` del TP (`C-0x_*.http`, `seed.sql`) quedan rotos hasta C-09; se actualizan `auth.http` y `autorizacion.http` en este change.
- [Cantidad de consultas del detalle] → se conserva `joinedload`/`selectinload`; la medición con `SQL_ECHO` es C-08.

## Migration Plan

Sin migraciones: el esquema de C-03 cubre todo. Verificación: `alembic upgrade head` y `alembic check` (autogenerate sin diferencias) desde `parcial/`. Despliegue: reiniciar uvicorn. **BREAKING** de rutas y contratos (ver proposal). Rollback: revertir el commit; los movimientos ya escritos quedan (sólo agregado) y siguen cumpliendo la invariante con el stock que dejaron.

## Open Questions

**RESUELTAS (2026-11-05)**: el usuario aceptó la recomendación de QA-01..QA-12; las specs ya las reflejan y no requieren ajuste. Falta el visto bueno explícito para el apply (governance ALTO).

- **QA-01 (concurrencia de stock)** — ¿UPDATE atómico condicional (C) o leer-modificar-escribir literal (A)? **Recomendación: (C)**, mantiene `stock == SUM(movimientos)` también con ventas simultáneas sin bloqueos explícitos ni reintentos; el PDF no lo evalúa pero tampoco lo prohíbe. (B) `FOR UPDATE` queda descartada por ser el tema de la próxima clase y más código.
- **QA-02 (Q-07, `motivo`)** — **Recomendación**: textos fijos «Stock inicial» (lo cita el PDF), «Reposición» y «Venta» (el vínculo con la venta queda en `venta_id`). Alternativa: «Venta N» o motivo libre enviado por el ADMIN al reponer.
- **QA-03 (`stock_inicial` = 0)** — **Recomendación**: se admite y no se crea movimiento (CHECK `cantidad <> 0`). Alternativa: exigir `stock_inicial >= 1`.
- **QA-04 (autores obligatorios)** — La Fig. 1 dibuja `Libro 1 ── 1..* LibroAutor`; el TP admitía lista vacía. **Recomendación**: `autores` con al menos uno (422 si viene vacío).
- **QA-05 (`PATCH /libros/{id}`)** — **Recomendación**: sólo `titulo` y `precio` (texto literal del PDF); `isbn`, `editorial_id`, `genero_id` → 422. El 409 de la tabla queda sólo para rechazos genéricos de la base. Alternativa: conservar los campos del TP salvo `stock` (el 409 sería por ISBN repetido).
- **QA-06 (Q-18, listados sin `page`/`size` en la tabla)** — **Recomendación**: envoltorio con `page`/`size` opcionales en `/{editoriales,generos,autores}/{id}/libros`, `/libros/{id}/movimientos` y `/clientes/{id}/ventas` (Ej. 3: "los listados devuelven el envoltorio").
- **QA-07 (Q-19 y movimientos)** — **Recomendación**: `GET`/`PATCH`/`DELETE /libros/{id}` de un dado de baja → 404; `GET /libros/{id}/movimientos` de un dado de baja → 200 (es historial de auditoría para el ADMIN); reponer un dado de baja → 409 (RN-13, PDF).
- **QA-08 (`GET /ventas/{id}` inexistente para un cliente)** — **Recomendación**: 404 para todos (la tabla admite 200/403/404). Alternativa: 403 para quien no es personal, para no revelar qué ids existen.
- **QA-09 (`/mis-ventas` sin ficha de cliente)** — **Recomendación**: 200 con página vacía (la tabla sólo admite 200/422). Alternativa: 404.
- **QA-10 (respuesta de reponer y su cuerpo)** — **Recomendación**: cuerpo `{"cantidad": n}` (motivo fijo, QA-02) y respuesta `{libro, movimiento}` (C-13: "Reposición 200 con su movimiento").
- **QA-11 (forma de `/autores/{id}/libros`)** — Hoy devuelve autorías (libro + rol + orden). **Recomendación**: `Pagina[LibroRead]` como los otros dos listados. Alternativa: `Pagina` de autorías (conserva rol y orden).
- **QA-12 (correo del cliente vinculado a un usuario)** — **REVISADA (2026-11-05)**: tras detectar el riesgo de divergencia entre `cliente.email` y `usuario.email`, el usuario eligió rechazar con 409 el `PATCH` de `email` sobre un cliente con usuario (el correo es la credencial de login). Decisión original (cambiar sólo `cliente.email`) descartada.

Al cerrar: registrar las QA resueltas en `knowledge-base/10_preguntas_abiertas.md` (Q-07, Q-18, Q-19 como resueltas) y marcar C-07 en `CHANGES.md`.
