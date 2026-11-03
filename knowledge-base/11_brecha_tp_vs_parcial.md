# Brecha: TP Cap 1-4 (código actual) vs Parcial Cap 1-6 (requerido)

El parcial se resuelve **agregando modificaciones sobre el TP existente**. Estado leído del repo (rama `main`, commit `e337710`): `app/{core,main.py,modules/*}`, `migrations/{env.py,versions/0001,0002}`, `test/*.http` + `seed.sql`, `README.md`, `PLAN.md`, `requirements.txt`, `env.example`.

> **Antes de tocar nada**: preservar el TP Cap 1-4 tal cual está (tag/branch o copia) para armar `despliegue/` (DD-03).

## Resumen por área
| Área | Estado actual (TP) | Requerido (parcial) | Acción |
|---|---|---|---|
| Config | `app/core/config.py` con `dotenv`; sólo `DATABASE_URL` (falla al importar si falta) y `SQL_ECHO` | `Settings` pydantic-settings; `POSTGRES_*` + `@computed_field`; clave de firma sin default; costo bcrypt, pool, cookie `Secure` en config | Reescribir `config.py`; actualizar `env.py` de Alembic y `env.example`; agregar deps |
| Motor / sesiones | `create_engine()`/`create_session_factory()` en `database.py`, ya llamadas desde el lifespan, `expire_on_commit=False`; `get_session` **hace commit/rollback** | `get_session` entrega y **cierra** la sesión (no commitea; confirma el UoW); pool declarado en config; hash ficticio calculado en el lifespan | Quitar commit de `get_session`; agregar pool y hash ficticio |
| Estructura | `app/modules/<m>/{models,schemas,service,router}.py` | agrega `repository.py` y `unit_of_work.py` por módulo; `core/{security,dependencies,repository,paginacion,unit_of_work}.py`; módulo `usuarios`; `health` sólo `router.py` (hoy tiene `service.py`) | Crear capas; mover lógica de `service.py` a repos/UoW |
| Servicios | Reciben `AsyncSession`; **hacen `rollback()`/`commit()`** (ej. `ventas.crear` commitea) y consultan con `select` directo | Reciben el UoW y lo abren con `async with`; nunca construyen UoW; ningún repo/servicio commitea | Refactor de **todos** los módulos |
| Health | `/health/live` ok; `/ready` ejecuta `SELECT 1` pero **no devuelve 503** | `/ready` -> 503 si la base no contesta | Capturar excepción -> 503 |
| Usuarios/auth | No existe | Tablas `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`; bcrypt+semáforo+`to_thread`; JWT en cookie; registro/login/logout/yo/cambiar-password; hash ficticio; límite 429; 72 bytes | Módulo nuevo completo |
| Autorización | No existe (todo público) | `get_usuario_actual` (401), `requiere_rol` (403, roles en BD por petición), dos grupos de rutas en `main.py`, cambio obligatorio, dueño en `/ventas/{id}`, `/mis-ventas` | Nuevo `dependencies.py` + `main.py` |
| `cliente` | `id, nombre, email UNIQUE`; `perfil` 1-1 | + `usuario_id` (nulo, UNIQUE) y `Cliente.usuario` (objeto) | Modelo + migración 0003 |
| `libro` | `isbn UNIQUE`; `stock` editable por `PATCH` y en el alta (`stock`); sin borrado lógico | `borrado_en`; **índice único parcial** de `isbn`; `stock` sólo por movimientos; alta con `stock_inicial`; `PATCH` sólo título/precio y rechaza `stock` (422) | Modelo, esquemas (`extra=forbid`), repo `SoftDeleteRepository`, migración 0003 (hay que **eliminar el UNIQUE común** de `isbn`: ojo, el autogenerate puede no hacerlo con un índice parcial: leer y corregir a mano, con comentario) |
| Endpoints de libros | `POST /libros/`, `GET /libros/`, `GET /libros/{id}`, `PATCH /libros/{id}` (con `stock`) | + `DELETE /libros/{id}` (204), `POST /libros/{id}/reponer`, `GET /libros/{id}/movimientos`, todos ADMIN salvo los GET de catálogo | Nuevos en C-07 |
| Endpoints que el PDF no lista | `GET /autores/`, `GET /{editoriales,generos,autores}/{id}`, `PATCH /generos/{id}`, `GET /clientes/` | No figuran en la tabla de referencia | Q-10 |
| `requirements.txt` | `python-dotenv`, sin pydantic-settings/bcrypt/PyJWT | `pydantic-settings>=2.0`, `bcrypt>=4.0`, `PyJWT>=2.8`, `fastapi[standard]` (trae uvicorn) | C-02 / C-05 |
| `alembic.ini` | `sqlalchemy.url =` vacío; `env.py` toma `DATABASE_URL` | `env.py` toma la URL de `Settings` (computada) | C-02 |
| `movimiento_stock` | No existe | Tabla nueva + CHECK `cantidad <> 0` + índices en FKs (`libro_id`, `venta_id`, `usuario_id` NOT NULL) | Migración 0003 |
| Sólo-agregado | No existe | Función + disparador (UPDATE/DELETE rechazados) | Migración 0004 **a mano**; `test/solo_agregado.sql` |
| Ventas | `ventas.crear`: lee libros, crea renglones y total, **commit dentro del servicio**; sin descuento de stock ni movimientos; sin validar libro dado de baja | En un solo UoW: venta+renglones+descuento+movimiento por renglón; 409 si no alcanza o libro/cliente inexistente o dado de baja; aviso `BackgroundTasks` **sólo si confirmó**; `/mis-ventas`; detalle con acceso por dueño | Reescribir; punto único de escritura de stock |
| Listados | `limit`/`offset` y `list[...]` | `{items,total,page,size,pages}`, `page>=1`, `size` 1..100, página inexistente -> 422, `total` con los mismos filtros, 1 página vacía si hay 0 | `core/paginacion.py` y adaptar todos los listados |
| Contratos | `SQLModel` en esquemas, sin `extra="forbid"` (ver `LibroCreate`/`LibroUpdate`) | `extra="forbid"` en entradas; sin `password_hash` en respuestas; `exclude_unset` en PATCH | Revisar todos los `schemas.py` |
| Lecturas | `joinedload`/`selectinload` dentro de los servicios | Precarga **dentro del método del repositorio**; detalle de venta incluye libro dado de baja | Mover a repos (`get_by_id_including_deleted`) |
| Errores | `_conflicto(IntegrityError)` por servicio con SQLSTATE 23505/23503, que lanza `HTTPException` **desde el servicio** | El servicio lanza errores del dominio; el **router traduce** (p. 9); nunca texto de la base ni 500 (incluido overflow de `int4` en ids) | Unificar (C-04) y aplicar en cada módulo |
| Logging aviso | Logger `app` configurado en `main.py` con handler propio (visible con uvicorn) | Mensaje visible con el arranque normal de uvicorn, después de la respuesta | Conservar el enfoque; verificar |
| Rutas | Routers con `"/"` final (`/libros/`) | Rutas del PDF sin barra | Normalizar (IN-05) |
| Seed | `test/seed.sql` (psql) | `seed.py` en raíz: vacía tablas y carga datos del PDF; actor `SISTEMA` en `evento_seguridad` | Crear `seed.py`; mantener o retirar `seed.sql` |
| Tests `.http` | `C-01..C-08` | `C-01..C-16` (+ `solo_agregado.sql` para C-14), con respuesta esperada en comentario | Rehacer/renumerar (IN-04) |
| Tests pytest | No existen | No se piden: sólo los `.http` y `solo_agregado.sql` del PDF (DD-01) | Nada |
| README | Puesta en marcha sin bcrypt/clave/seed.py | README con integrantes y pasos desde cero: venv, deps, `.env` + cómo generar la clave de firma, `alembic upgrade head`, `python seed.py`, arranque | Reescribir |
| Despliegue | No existe | `despliegue/` con Dockerfile, .dockerignore, env.example, DEPLOY.md, evidencia/ | Ver `12_entregables_del_parcial.md` |

## Detalle de riesgos de la migración sobre el esquema existente
- La base del TP ya tiene `libro.isbn UNIQUE`, **nombrada `uq_libro_isbn`** en la 0001 (verificado): la 0003 debe `op.drop_constraint("uq_libro_isbn", "libro", type_="unique")` y crear `ix_libro_isbn_vigente` (nombre libre) con `postgresql_where=sa.text("borrado_en IS NULL")`; el downgrade hace lo inverso.
- **Desfasaje modelo ↔ migración del TP**: los modelos declaran `Field(unique=True)` sin nombre (`isbn`, `email`, `nombre`), mientras la 0001/0002 crearon `uq_*` con nombre. El autogenerate de la 0003 puede proponer drops/creates espurios de esas UNIQUE: hay que leerla y quitar lo que no corresponda (y conviene declarar las restricciones con el mismo nombre en `__table_args__`). Lo mismo con índices: la 0001 crea `ix_*` explícitos.
- `cliente.usuario_id` necesita UNIQUE con nombre (p. ej. `uq_cliente_usuario_id`) + FK a `usuario.id`; ninguna fila existente se ve afectada (nulo).
- `movimiento_stock` vs libros existentes: en una base ya poblada habría que **backfillear** un movimiento "Stock inicial" por libro para respetar `stock == SUM`. El PDF parte de base vacía + `seed.py`, así que no es obligatorio, pero conviene decidirlo (Q nueva si se quiere soportar datos previos).
- `env.py` de Alembic importa `DATABASE_URL` de `config.py`: hay que migrar a `Settings` sin dejar credenciales en `alembic.ini`.
- `app/modules/models.py` agrega los metadatos a Alembic: sumar `usuarios` (y `MovimientoStock`) para el autogenerate.
- El autogenerate **no ve** funciones/disparadores: por eso la 0004 es a mano.

## Orden de cambios sugerido (dependencias)
1. Snapshot del TP para `parcial/` y `despliegue/` (hecho en C-01).
2. Config/lifespan/get_session/health (Ej. 1).
3. Capas core: `repository.py`, `unit_of_work.py`, `paginacion.py`; migrar módulos de referencia (editoriales, géneros, autores) como patrón.
4. Modelos nuevos + migraciones 0003/0004 (Ej. 2, 7).
5. `usuarios`: seguridad, auth, dependencias, grupos de rutas (Ej. 4, 5).
6. `libros` con stock/borrado lógico, `clientes`, `ventas` con UoW (Ej. 6, 8).
7. `seed.py`, `.http` C-01..C-16, evidencia C-14/C-15, README.
8. En paralelo e independiente: `despliegue/` (Ej. 9-10), sobre el snapshot del TP.
