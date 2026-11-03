# Flujos Principales

## Flujo 1 — Auto-registro (RN-02, RN-16 parcial)
**Disparador**: `POST /auth/registro`. **Actor**: visitante.
1. Router valida contrato (`extra=forbid`, contraseña <= 72 bytes) y construye el UoW de `usuarios`.
2. Servicio calcula el hash bcrypt **antes** de abrir la transacción (`to_thread` + semáforo).
3. `async with uow`: inserta `usuario`, `asignacion_rol(CLIENTE)`, `cliente(usuario_id)`; los repositorios hacen `flush`, el UoW hace `commit` al salir.
4. Error: email repetido (usuario o cliente) -> `IntegrityError` traducido a **409** con mensaje propio; el rollback no deja ninguna de las tres filas.

## Flujo 2 — Login (RN-07, RN-08)
**Disparador**: `POST /auth/login`.
1. Contar en `intento_acceso` los fallos de (email, ip) en los últimos 60 s **desde el último login correcto**. Si >= 5 -> **429 + Retry-After**, sin hash.
2. Buscar usuario; verificar bcrypt contra su hash o contra el **hash ficticio** (calculado una vez en el lifespan) si no existe.
3. Registrar el intento (correcto o fallido) en `intento_acceso` con **sesión y transacción propias, siempre confirmadas** (aunque la petición termine en 401). Se abre desde la fábrica de `app.state` con un UoW/repositorio propio construido por el router, para que el servicio siga sin tocar sesiones. Comentario obligatorio en el código: qué hace distinto, por qué no puede compartir la transacción, su costo (deja filas aunque la petición falle). Si el rechazo 429 también se anota es decisión del grupo (Q-20).
4. Éxito: emitir JWT (`sub`, `exp`, roles vigentes) en cookie `access_token`; cuerpo `{mensaje, debe_cambiar_password, expira_en_segundos}`.
5. Falla: 401 con el mismo cuerpo exista o no el correo.
```
Cliente -> router -> servicio -> [intento_acceso: sesión propia] ; [usuario: UoW de la petición]
                                  <- 401/429/200 (+Set-Cookie)
```

## Flujo 3 — Petición autenticada y autorizada (RN-04, RN-06)
1. `get_usuario_actual`: lee cookie `access_token` de `request.cookies` (nunca `Authorization`) -> valida JWT -> carga usuario (existente y activo) con la **misma sesión que el UoW** -> 401 si falla algo.
2. Grupo protegido: control "cambio pendiente" montado una vez -> 403 si `debe_cambiar_password` y no es ruta `/auth`.
3. `requiere_rol(...)`: consulta `asignacion_rol` vigentes en la base -> 403 si no alcanza.
4. Handler -> servicio abre el UoW.

## Flujo 3b — Cambio de contraseña y alta de personal (RN-06, RN-16)
- `POST /auth/cambiar-password` (grupo **abierto**, pide sesión): contrato con contraseña actual y nueva (<= 72 bytes cada una -> si no, 422); verificar la actual con bcrypt fuera del bucle; calcular el hash nuevo **antes** de abrir el UoW; en **un solo bloque**: actualizar `password_hash`, poner `debe_cambiar_password=false` e insertar la línea en `evento_seguridad`. No emite token nuevo ni invalida sesiones: la misma cookie sirve después para las rutas protegidas (C-09).
- `POST /usuarios` (ADMIN): contraseña provisoria hasheada antes del UoW; en un solo bloque `usuario(debe_cambiar_password=true)` + `asignacion_rol` + `evento_seguridad`; correo repetido -> 409 por el UNIQUE (sin consulta previa).

## Flujo 4 — Asignar / revocar rol (RN-03, RN-05, RN-16)
`POST /usuarios/{id}/roles` y `DELETE /usuarios/{id}/roles/{rol}`, un solo bloque UoW cada uno:
1. Validar `vence_en` (con zona, futuro) -> 422.
2. Asignar: si hay fila abierta vigente -> 409 (índice único parcial); si hay una vencida abierta -> cerrarla y abrir una nueva.
3. Revocar: escribir `revocada_en` (no borrar). Si el actor se revoca su ADMIN o dejaría 0 admins vigentes -> **409**.
4. Insertar línea en `evento_seguridad` en la **misma transacción**.

## Flujo 5 — Registrar venta (RN-09, RN-10, RN-11)
**Disparador**: `POST /ventas`. **Actor**: VENDEDOR/ADMIN.
1. Contrato: >= 1 renglón, sin libros repetidos, sin precio/total/fecha.
2. UoW de `ventas` (con repositorios de ventas, clientes y libros). Verificar cliente y libros (no dados de baja) -> 409 si falta alguno.
3. Crear `venta` + `renglon_venta` (precio copiado del libro, total calculado por el servidor).
4. Para cada libro: descontar stock y crear `movimiento_stock(cantidad<0, venta_id, usuario_id, motivo)` **por el único punto de escritura de stock**. Si no alcanza -> **409** y rollback total.
5. Commit al salir del bloque. Recién entonces `BackgroundTasks` ejecuta el aviso (`sleep(0.5)` + log) **después de la respuesta**.
6. Invariante a verificar tras cada caso: para cada libro, `stock == SUM(movimiento_stock.cantidad)`.

## Flujo 6 — Ciclo de vida del libro (RN-11, RN-13)
- Alta: `POST /libros` con `stock_inicial` -> libro + autorías + movimiento "Stock inicial" (mismo punto de escritura de stock).
- Reposición: `POST /libros/{id}/reponer` -> movimiento positivo y stock actualizado; sobre libro dado de baja -> 409.
- Baja: `DELETE /libros/{id}` -> `borrado_en = now()` (204); desaparece del catálogo; ventas anteriores lo siguen mostrando (precarga que incluye borrados). Recargar el ISBN -> 201; segundo vigente -> 409.

## Flujo 7 — Despliegue del TP Cap 1-4 (Ej. 9-10, proyecto `despliegue/`)
1. En el servidor (o en otro lado y se lleva): `docker build -t libreria .` (base `python:3.12-alpine`).
2. `docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped --env-file <archivo-de-variables> libreria` (+ `--add-host=host.docker.internal:host-gateway` en Linux si la base está en el host). El archivo de variables vive en el servidor, fuera del repo/imagen, con `DATABASE_URL` (driver `postgresql+asyncpg`) y `SQL_ECHO=false`.
3. Arranque del contenedor: `alembic upgrade head` -> `uvicorn app.main:app --host 0.0.0.0`. Si la base no responde, Alembic falla y el contenedor termina con error (es lo deseado; `--restart unless-stopped` lo reintenta).
4. `HEALTHCHECK` sobre `GET /health/ready` con `wget` a **127.0.0.1** (no `localhost`: resuelve a ::1 y uvicorn sólo escucha IPv4).
5. Carga de datos: `docker exec libreria <comando de datos iniciales del README del TP>`.
6. Actualizar: rebuild de la imagen, `docker rm -f libreria`, mismo `docker run`; los datos viven en la base del servidor.
7. Debe seguir en línea hasta que se publiquen las notas.

## Flujo 8 — Verificación de los casos
Antes de cada `.http`: `python seed.py`. Varias sesiones simultáneas en REST Client: `# @name loginAdmin` y pedidos con `# @no-cookie-jar` + `Cookie: {{loginAdmin.response.headers.Set-Cookie}}`. Casos C-01..C-16 sobre `parcial/`; D-01..D-08 sobre el despliegue (ver `12_entregables_del_parcial.md`).
