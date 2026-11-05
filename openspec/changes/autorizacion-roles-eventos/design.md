# Design

## Context

Motivo y alcance: ver `proposal.md`. Requisitos: `specs/autorizacion`, `specs/gestion-roles`, `specs/eventos-seguridad` y el delta de `specs/catalogo-referencias`.

Estado actual de `parcial/` (observado):
- `app/core/dependencies.py` (C-05): `get_usuario_actual` ya cumple el 401 completo (sólo `request.cookies`, token inválido/vencido, usuario inexistente o inactivo) y carga el usuario dentro de `async with UnitOfWork(session)` con la sesión de `get_session` (la misma que usan los `get_uow` de los routers; FastAPI la cachea por petición). Devuelve `SesionActual(usuario, roles_token)`; **no** lee roles vigentes.
- `AsignacionRolRepository.roles_vigentes(usuario_id)` existe (`revocada_en IS NULL AND (vence_en IS NULL OR vence_en > ahora)`); `GET /auth/yo` lo llama en su propio bloque.
- Modelos (C-03): `AsignacionRol` con CHECK de rol, índice único parcial `ux_asignacion_rol_usuario_rol_abierta (usuario_id, rol) WHERE revocada_en IS NULL`, `otorgada_por` FK a `usuario` con índice (Q-17 resuelta así en C-03); `EventoSeguridad(cuando, actor texto, accion)`; fechas `timestamptz`.
- `BaseRepository.add/update` hacen `flush()`; `UnitOfWork` confirma al salir, revierte con excepción, no cierra la sesión; `traducir_errores` traduce 23505 → 409 con mensaje propio, `NoEncontrado` → 404, `Conflicto` → 409, `PaginaInexistente` → 422.
- `main.py` incluye todos los routers directamente en `app`, sin grupos. Los routers de `editoriales`, `generos` y `autores` mezclan GET públicos y POST/PATCH en un mismo `APIRouter`. `libros`, `clientes` y `ventas` siguen con el patrón del TP (`get_session_tp`, transitorio hasta C-07; rutas con barra final). `libros` todavía no tiene `DELETE`, `reponer` ni `movimientos` (C-07); no existe `/mis-ventas` (C-07) ni `seed.py` (C-09).

Restricciones: reglas duras de `CLAUDE.md` (capas, roles de la base, 401 ≠ 403, hash antes del UoW, sin pytest), Ej. 5 y Ej. 7 del PDF (el PDF manda), y las decisiones de C-05 (D1, D8, D12).

## Goals / Non-Goals

**Goals:**
- Una sola consulta de roles por petición autenticada, con la misma sesión que el UoW y sin retener la conexión.
- El control del cambio obligatorio declarado una única vez en `main.py`; imposible "olvidarlo" en una ruta protegida nueva.
- RN-03 garantizado por la base (no por un SELECT previo) y RN-05 correcto ante dos revocaciones simultáneas.
- Cada escritura de seguridad y su evento en un solo bloque UoW.

**Non-Goals:**
- Reescribir libros/clientes/ventas (C-07): aquí sólo se les monta la autorización.
- Revocar o renovar tokens; listar/buscar usuarios; activar/desactivar usuarios (no los pide el PDF).
- Filtros en `GET /eventos` (el PDF sólo pide `page`, `size`).

## Decisions

### D1 — `get_usuario_actual` carga también los roles vigentes
Se amplía la dependencia de C-05 (no se crea otra): dentro del mismo `async with UnitOfWork(session)` lee el usuario y, si existe y está activo, `roles_vigentes(usuario.id)`. `SesionActual` pasa a ser `(usuario, roles_vigentes: list[Rol], roles_token: list[str])`. `GET /auth/yo` usa `sesion.roles_vigentes` en lugar de repetir la consulta (el servicio `yo` deja de abrir el UoW; el contrato `YoOut` no cambia).
- Por qué: RN-04 pide los roles de la base en cada petición; leerlos una vez en la dependencia (cacheada por petición) sirve a `requiere_rol`, a `/auth/yo` y, en C-07, al servicio de `GET /ventas/{id}` (personal o dueño) sin consultas repetidas. El bloque de lectura confirma al salir y devuelve la conexión al pool antes del handler (D8 de C-05).
- Alternativa descartada: que `requiere_rol` consulte por su cuenta — dos lugares que leen roles, y una segunda consulta en las rutas que además necesitan saber los roles.
- Costo: rutas abiertas que piden sesión (`/auth/yo`, `cambiar-password`) hacen la consulta de roles aunque `cambiar-password` no la use; es una consulta indexada (`ix_asignacion_rol_usuario_id`).

### D2 — `requiere_rol(*roles)` → 403
Fábrica en `app/core/dependencies.py` que devuelve una dependencia `async def` que recibe `UsuarioActualDep` y lanza `HTTPException(403, "No tenés permiso para esta operación")` si `set(sesion.roles_vigentes)` no corta a `roles`; si alcanza, devuelve la `SesionActual`. Se instancian una vez a nivel de módulo (`solo_admin = requiere_rol(Rol.ADMIN)`, `personal = requiere_rol(Rol.VENDEDOR, Rol.ADMIN)`) para que FastAPI cachee cada una por petición. Como depende de `get_usuario_actual`, el 401 siempre sale antes que el 403.
- Se monta como `dependencies=[Depends(...)]` **del `APIRouter` protegido de cada módulo** cuando todas sus rutas comparten roles (`/usuarios`, `/eventos`, `/clientes`, `/ventas`, escrituras del catálogo); los handlers que necesitan al actor lo reciben con `UsuarioActualDep` (misma instancia cacheada, sin consulta extra).
- Los 403 se lanzan como `HTTPException` en la dependencia (capa HTTP, igual que los 401 de C-05).

### D3 — Control del cambio obligatorio montado una vez
`exigir_password_al_dia` en `app/core/dependencies.py`: recibe `UsuarioActualDep`; si `sesion.usuario.debe_cambiar_password` → `HTTPException(403, "Tenés que cambiar la contraseña antes de seguir")`. Como el usuario se relee de la base en cada petición, tras `POST /auth/cambiar-password` la misma cookie pasa (C-09 del PDF). Mensaje distinto del 403 de rol para que se distingan en los casos.

### D4 — Dos grupos de rutas en `main.py`
```python
abierto = APIRouter()
protegido = APIRouter(dependencies=[Depends(exigir_password_al_dia)])
abierto.include_router(health_router); abierto.include_router(auth_router)
abierto.include_router(editoriales.router_publico); ...         # GET del catálogo
protegido.include_router(editoriales.router_admin); ...          # POST/PATCH del catálogo
protegido.include_router(usuarios_router); protegido.include_router(eventos_router)
protegido.include_router(clientes_router); protegido.include_router(ventas_router)
app.include_router(abierto); app.include_router(protegido)
```
- Por qué así: "FastAPI suma dependencias y no las resta" (PDF, sección 5.10): si el control fuese global, `/auth/cambiar-password` no podría quitárselo. Un único `APIRouter` protegido con la dependencia en su constructor la declara una vez; al incluirse en `app`, FastAPI la antepone a cada ruta del grupo. Alternativa descartada: `app.include_router(x, dependencies=[...])` por módulo — el control quedaría repetido N veces y una ruta nueva podría quedar sin él.
- Cada `router.py` de catálogo se parte en `router_publico` (GET) y `router_admin` (POST/PATCH, con `solo_admin` a nivel de router), mismo `prefix`. Starlette recorre todas las rutas y usa la primera coincidencia **completa** (ruta + método), así que `GET /editoriales/{id}` en el abierto y `PATCH /editoriales/{id}` en el protegido conviven.
- Orden de dependencias en una ruta protegida: `get_usuario_actual` (401) → `exigir_password_al_dia` (403) → rol (403) → validación de parámetros (422) → handler. Con sesión válida, un parámetro no entero da 422 sin ejecutar el handler (C-01).

Reparto (matriz de `03`, Q-10 según lo adoptado en C-04):

| Grupo | Rutas | Rol |
|---|---|---|
| Abierto, sin sesión | `/health/*`; `POST /auth/registro`, `/auth/login`, `/auth/logout`; `GET /libros/`, `/libros/{id}`; `GET /editoriales`, `/generos`, `/autores`; `GET /{editoriales,generos,autores}/{id}` y `/{id}/libros` | — |
| Abierto, con sesión | `GET /auth/yo`, `POST /auth/cambiar-password` | Autenticado |
| Protegido | `POST /editoriales,/generos,/autores`; `PATCH /editoriales/{id},/generos/{id},/autores/{id}`; `POST /libros/`, `PATCH /libros/{id}` | ADMIN |
| Protegido | `POST /usuarios`, `GET`/`POST /usuarios/{id}/roles`, `DELETE /usuarios/{id}/roles/{rol}`, `GET /eventos` | ADMIN |
| Protegido | todo `/clientes` (incl. `GET /clientes/` del TP, Q-10) y `POST`/`GET /ventas/` | VENDEDOR, ADMIN |
| Protegido | `GET /ventas/{id}` | VENDEDOR, ADMIN **transitorio** (ver D10 y QA-07) |

### D5 — Contratos (`usuarios/schemas.py`)
- `PersonalIn {email: Email, nombre, password: PasswordBcrypt, rol: RolPersonal}` con `extra="forbid"`; `RolPersonal = Literal[Rol.VENDEDOR, Rol.ADMIN]` (CLIENTE → 422; ver QA-01, QA-02).
- `AsignarRolIn {rol: Rol, vence_en: AwareDatetime | None = None}` con `extra="forbid"` y un `AfterValidator` que exige `vence_en > datetime.now(UTC)` → `ValueError` → 422. `AwareDatetime` de Pydantic rechaza la fecha sin zona con 422 (no llega a la base: no hay 409 posible). Se guarda tal cual; `timestamptz` la normaliza a UTC.
- `AsignacionRead {id, usuario_id, rol, desde, vence_en, revocada_en, otorgada_por, vigente: bool}`; `vigente` lo calcula el servicio con el mismo `ahora` de la operación.
- `EventoRead {id, cuando, actor, accion}`; `GET /eventos` → `Pagina[EventoRead]`.
- `rol` de la ruta `DELETE /usuarios/{id}/roles/{rol}` tipado como `Rol` (fuera del enum → 422); `{id}` con `IdPath` (int4, ≥ 1).

### D6 — Alta de personal (RN-16 en un bloque)
`hash = await hashear_password(datos.password)` **antes** del UoW; luego `async with uow:` `usuarios.add(Usuario(..., debe_cambiar_password=True))` (flush → id), `asignaciones.add(AsignacionRol(usuario_id, rol, desde=ahora, otorgada_por=actor.id))`, `eventos.add(EventoSeguridad(actor=actor.email, accion=f"Alta de personal {email} con rol {rol}"))`. Correo repetido → 23505 en el primer flush → el UoW revierte → router `traducir_errores("Ya existe un usuario con ese correo")` → 409 sin filas. No crea ficha de cliente (el personal no es cliente); un correo que sólo existe en `cliente` no choca. Respuesta 201 `UsuarioRead`.

### D7 — Asignar rol (RN-03 garantizado por la base)
En un bloque, con un único `ahora = datetime.now(UTC)`:
1. `usuarios.get_by_id(id)` → `None` → `NoEncontrado` (404: es el recurso de la ruta; si se dejara a la FK daría 23503 → 409, que el PDF no admite para este caso).
2. `abierta = asignaciones.get_abierta(usuario_id, rol)` (`revocada_en IS NULL`). Si existe **y venció** (`vence_en <= ahora`) → `asignaciones.update(abierta, {"revocada_en": ahora})` (el `update` hace su propio `flush`, así el UPDATE llega a la base **antes** del INSERT y libera el índice parcial).
3. `asignaciones.add(AsignacionRol(usuario_id, rol, desde=ahora, vence_en, otorgada_por=actor.id))`. Si quedaba una abierta **vigente**, el índice único parcial rechaza el INSERT (23505) → el UoW revierte → 409 «El usuario ya tiene ese rol vigente». No hay `if vigente: raise` previo: la unicidad la garantiza la base (`05` §Manejo de errores), y el SELECT del paso 2 sólo sirve para detectar la fila vencida.
4. `eventos.add(...)` con `accion` «Asignación de rol {rol} a {email}» (+ « hasta {vence_en ISO}» si corresponde).
- Concurrencia: dos asignaciones simultáneas del mismo rol → ambas leen "nada abierto", ambas insertan, el índice deja pasar una y la otra da 409. Dos reasignaciones de un vencido → la segunda espera el lock de fila del UPDATE, lo repite y su INSERT choca con el índice → 409.
- Cierre de la fila vencida con `revocada_en = ahora` (momento del cierre); la vigencia real queda en `vence_en` (ver QA-05).

### D8 — Revocar rol y autoprotección (RN-05)
En un bloque, con un único `ahora`:
1. Usuario inexistente → 404; `vigente = asignaciones.get_vigente(usuario_id, rol, ahora)` → `None` → 404 «El usuario no tiene ese rol vigente» (QA-04).
2. Si `rol == ADMIN`:
   - `usuario_id == actor.id` → `Conflicto("No podés revocarte tu propio rol ADMIN")` → 409.
   - `admins = asignaciones.admins_vigentes_bloqueando(ahora)`: `SELECT asignacion_rol.* FROM asignacion_rol JOIN usuario ... WHERE rol='ADMIN' AND revocada_en IS NULL AND (vence_en IS NULL OR vence_en > :ahora) AND usuario.activo FOR UPDATE OF asignacion_rol`. Si no queda ninguna fila de **otro** usuario → `Conflicto("El sistema no puede quedar sin administradores vigentes")` → 409.
3. `asignaciones.update(vigente, {"revocada_en": ahora})`; `eventos.add(...)` «Revocación de rol {rol} a {email}». Respuesta 200 `AsignacionRead`.
- **Race**: sin el lock, con dos ADMIN (A y B) revocándose mutuamente a la vez, cada transacción ve 2 vigentes, ninguna es autorrevocación, y ambas confirman → 0 admins. Con `FOR UPDATE`, la segunda espera; al confirmar la primera, PostgreSQL (READ COMMITTED) re-evalúa el `WHERE` sobre las filas bloqueadas que cambiaron, excluye la recién revocada y la segunda ve sólo la fila de su propio objetivo → 409. Además el actor siempre es ADMIN vigente (lo exige `solo_admin`), así que fuera de la concurrencia el segundo caso de RN-05 sólo se dispara con admins inactivos o vencidos.
- Alternativas: `pg_advisory_xact_lock(<constante>)` — serializa todas las revocaciones de ADMIN, igual de correcto pero opaco y fuera del patrón de repositorio; `SERIALIZABLE` — exigiría reintentar ante `40001`, que el resto del sistema no maneja. Se elige `FOR UPDATE` (`with_for_update(of=AsignacionRol)`) dentro del repositorio.
- Es "comprobación en el servicio" (RN-05 en la tabla del PDF), única excepción explícita a "unicidad sin consulta previa".

### D9 — Eventos de seguridad (RN-16) y `SISTEMA`
- `actor` = correo del usuario que hace el cambio (mismo criterio que el cambio de contraseña de C-05); `accion` = texto con operación, usuario afectado y rol. El evento se agrega con `uow.eventos.add` **dentro del mismo `async with`**: si cualquier paso falla, el rollback lo quita; si el `add` del evento falla, se revierte el cambio.
- `ACTOR_SISTEMA = "SISTEMA"` como constante en `app/modules/usuarios/models.py` (junto a `EventoSeguridad`); la usa `seed.py` (C-09) para «Carga de los datos iniciales». En C-06 la verificación inserta esa línea a mano (D11).
- `GET /eventos`: `EventoSeguridadRepository.listar_recientes(offset, limit)` (`ORDER BY cuando DESC, id DESC`) + `count()`; el servicio arma `Pagina` con `calcular_paginas`/`PaginaInexistente`, igual que los listados del catálogo. Router `/eventos` en el módulo `usuarios` (ahí vive el modelo).

### D10 — Rutas del TP (libros, clientes, ventas) hasta C-07
Sólo se parten en público/protegido y se les monta el rol; la lógica y `get_session_tp` siguen igual. `GET /ventas/{id}` queda en el protegido con VENDEDOR/ADMIN (falla cerrada): sin la comprobación de dueño (C-07) cualquier cliente vería ventas ajenas. C-07 le quita el rol y pone la decisión en el servicio.
- Consecuencia: en esas rutas la dependencia de sesión usa `get_session` y el handler `get_session_tp` (dos sesiones en la misma petición, no simultáneas: la de autorización confirma y devuelve la conexión antes de que el handler consulte). Ej. 6 pide la unificación; queda resuelta cuando C-07 borra `get_session_tp`.

### D11 — Verificación sin pytest y sin seed
`parcial/test/autorizacion.http`. Como `seed.py` llega en C-09, la cabecera documenta el arranque: (1) `POST /auth/registro` de dos admins y un cliente propios del archivo; (2) psql: `INSERT INTO asignacion_rol (usuario_id, rol, desde) SELECT id, 'ADMIN', now() FROM usuario WHERE email IN (...)` y `INSERT INTO evento_seguridad (cuando, actor, accion) VALUES (now(), 'SISTEMA', 'Carga de los datos iniciales')`; (3) el vendedor se crea con `POST /usuarios` (queda con cambio pendiente, sirve para C-09) y se le cambia la contraseña para los demás casos; (4) la fila vencida se fabrica con `UPDATE asignacion_rol SET vence_en = now() - interval '1 minute'` (la API la rechaza con 422, a propósito). Sesiones paralelas con `# @name` / `# @no-cookie-jar` / `Cookie:`. La revocación cruzada simultánea se demuestra con dos `psql` (D8) o se justifica por lectura; no es caso del PDF.

## Risks / Trade-offs

- [Race en "no quedar sin admins"] → `FOR UPDATE OF asignacion_rol` sobre los ADMIN vigentes antes de contar (D8). Un ADMIN insertado en paralelo (fantasma) no se ve: sólo puede producir un 409 de más, nunca 0 admins.
- [Vencimiento por tiempo deja 0 admins] → ninguna comprobación al escribir impide que el último ADMIN con `vence_en` caduque solo. Mitigación: el seed tiene dos ADMIN sin vencimiento; ver QA-03.
- [Zona horaria] → `AwareDatetime` rechaza fechas sin zona (422); "futuro" se compara contra `datetime.now(UTC)` del proceso, el mismo reloj que `desde`/`revocada_en` y que el filtro de `roles_vigentes` (C-05 ya usa el reloj de Python). Un `vence_en` muy próximo puede vencer entre la validación y el INSERT: no es un error, sólo una asignación que nace casi vencida.
- [Eventos en la misma transacción] → el evento se agrega dentro del mismo `async with` y antes de salir; ningún `commit` intermedio (los repositorios sólo hacen `flush`). Un fallo de cualquier escritura revierte cambio y evento.
- [401 contra 403] → el 401 sale siempre de `get_usuario_actual` (sub-dependencia de todo lo demás); el 403 sólo de `exigir_password_al_dia` y `requiere_rol`. Sin sesión, un parámetro mal formado en una ruta protegida da 401 y no 422 (C-01 del PDF pide el 422 *con* sesión).
- [Cambio obligatorio] → el flag se relee en cada petición; `cambiar-password` no emite token (C-05) y la misma cookie sirve. Un usuario con cambio pendiente que además tiene rol insuficiente ve el 403 del cambio (más útil: es lo primero que tiene que hacer).
- [Ruta protegida olvidada] → las rutas nuevas sólo heredan el control si se incluyen en `protegido`; la tabla de D4 y la tarea de revisión listan las rutas y su grupo (`/docs` + recorrido de `app.routes`).
- [Dos sesiones en rutas del TP] → transitorio (D10), lo cierra C-07.
- [Token con roles viejos] → informativos; `/auth/yo` muestra la diferencia (C-07 del PDF).

## Migration Plan

Sin migraciones ni cambios de esquema. Despliegue: reiniciar uvicorn. **BREAKING** para clientes del TP: escrituras del catálogo, clientes y ventas pasan a exigir sesión y rol. Rollback: revertir el commit (las rutas vuelven a quedar abiertas; las filas nuevas en `asignacion_rol`/`evento_seguridad` quedan como historial).

## Open Questions

**RESUELTAS (2026-11-05)**: el usuario aceptó la recomendación de QA-01..QA-08; las specs ya reflejan esas decisiones y no requieren ajuste. Falta el visto bueno explícito para el apply (governance CRÍTICO).

- **QA-01 (Q-05, parte "contraseña provisoria")** — ¿Quién define la contraseña provisoria de `POST /usuarios`? El PDF sólo dice "con contraseña provisoria". **Recomendación**: la envía el ADMIN en el cuerpo (`password`, ≤ 72 bytes), y el servidor la hashea antes del UoW. Alternativa: generarla en el servidor y devolverla una vez en la respuesta (pone un secreto en un cuerpo HTTP y complica los `.http`). Las contraseñas del seed siguen diferidas a C-09.
- **QA-02** — ¿`rol` es obligatorio en `POST /usuarios` y sólo `VENDEDOR`/`ADMIN`? **Recomendación**: sí ("alta de personal"; un CLIENTE nace por `/auth/registro` con su ficha, RN-02). Alternativa: opcional con default `VENDEDOR`.
- **QA-03 (RN-05 y vencimientos)** — ¿Se impide que el sistema quede sin ADMIN por vencimiento (p. ej., rechazar `vence_en` en una asignación ADMIN si sería el último sin vencimiento)? **Recomendación**: no; RN-05 se comprueba en la revocación con los vigentes "ahora" e incluyendo sólo usuarios activos. El PDF garantiza RN-05 "en el servicio" al revocar y no menciona el vencimiento.
- **QA-04** — `DELETE /usuarios/{id}/roles/{rol}` sobre una asignación abierta pero ya vencida: **Recomendación**: 404 («no tiene ese rol vigente»); la fila se cierra en la próxima reasignación. Alternativa: cerrarla y responder 200.
- **QA-05** — Al reasignar un rol vencido, ¿qué valor se escribe en `revocada_en` de la fila anterior? **Recomendación**: el momento del cierre (`ahora`); `vence_en` ya registra hasta cuándo valió. Alternativa: copiar `vence_en`.
- **QA-06** — `GET /usuarios/{id}/roles`: ¿historial completo o sólo vigentes? **Recomendación**: historial completo con `vigente` por fila (muestra por API que "la fila revocada sigue", caso C-07). Sin paginar (la tabla del PDF no le pone `page`/`size`).
- **QA-07** — `GET /ventas/{id}` hasta C-07: **Recomendación**: VENDEDOR/ADMIN (falla cerrada, D10). Alternativa: sólo sesión, dejando ver ventas ajenas hasta C-07.
- **QA-08** — Formato de `actor`/`accion`: **Recomendación**: `actor` = correo (como C-05), `accion` en texto libre con operación + afectado + rol. El PDF sólo fija «Carga de los datos iniciales» y `SISTEMA`.

Al cerrar: registrar QA-01..QA-08 resueltas en `knowledge-base/10_preguntas_abiertas.md` (QA-01 como avance de Q-05) y ajustar la línea de C-06 en `CHANGES.md` (`get_usuario_actual` ya existía, D1 de C-05).
