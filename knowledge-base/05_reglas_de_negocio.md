# Reglas de Negocio

Las RN01-RN16 del PDF **se numeran de nuevo y reemplazan a las del TP** en lo que se superponen. Siguen vigentes, aunque no se repitan: los CHECK de precio y stock del libro y la **búsqueda por título con parámetros ligados** (sin distinguir mayúsculas). El PDF las escribe `RN01`..`RN16` en la tabla y `RN-01`..`RN-16` en las consignas; aquí se usa `RN-NN`.

> **Verificada** (auditoría `13_auditoria_vs_pdf.md`): la tabla se re-extrajo con `pdftotext -table` (xpdf 4.06), que respeta las columnas, y cada par enunciado ↔ garante coincide textualmente con el PDF (RN-01..RN-13 en p. 7, RN-14..RN-16 en p. 8).

| Código | Enunciado | Garante esperado |
|---|---|---|
| RN-01 | El correo de un usuario, el de un cliente, el nombre de una editorial y el de un género son únicos. El ISBN de un libro es único entre los que no están dados de baja. | UNIQUE e índice único parcial en la base; 409 con mensaje propio |
| RN-02 | El auto-registro crea el usuario, su rol CLIENTE y su ficha de cliente: o quedan las tres filas, o ninguna. Si ya existe un cliente con ese correo, el registro da 409 y no se apropia de esa ficha. | Un solo Unit of Work |
| RN-03 | Un usuario tiene a lo sumo una asignación abierta por rol. | Índice único parcial; 409 |
| RN-04 | Los permisos se deciden con los roles vigentes en la base, en cada petición. Los roles que trae el token son informativos. | Dependencia que consulta `asignacion_rol` |
| RN-05 | Un administrador no puede revocarse su propio rol ADMIN, y el sistema nunca queda sin administradores vigentes. | Comprobación en el servicio; 409 |
| RN-06 | Mientras un usuario tenga el cambio de contraseña pendiente, sólo puede usar las rutas de `/auth` y las que no piden sesión. | Dos grupos de rutas; 403 |
| RN-07 | Después de 5 intentos fallidos con el mismo correo desde la misma dirección en 60 segundos, el login responde 429 sin verificar la contraseña. Un login correcto reinicia la cuenta: los fallos anteriores siguen en la tabla, pero dejan de contar. | Conteo sobre `intento_acceso`; `Retry-After` |
| RN-08 | El login responde lo mismo, y tarda lo mismo, exista o no el correo. | Mismo mensaje; verificación contra un hash ficticio |
| RN-09 | Una venta nace con sus renglones (al menos uno, sin libros repetidos), con el precio de cada renglón copiado del libro y el total calculado por el servidor. Las ventas no se modifican. | DTO; el precio y el total nunca viajan en el cuerpo; no hay PATCH |
| RN-10 | Registrar una venta descuenta el stock de cada libro y deja un movimiento por renglón. Si un libro no alcanza, no queda ninguna de esas escrituras: ni la venta, ni los renglones, ni los descuentos, ni los movimientos. | Un solo Unit of Work; 409 |
| RN-11 | El stock de un libro sólo cambia a través de movimientos: el alta con stock inicial, la reposición y la venta. No se edita por PATCH. | Punto único de escritura de stock |
| RN-12 | `movimiento_stock` es de sólo agregado: nadie puede modificar ni borrar sus filas. | Disparador en la base, instalado por migración |
| RN-13 | Un libro dado de baja deja de aparecer en el catálogo y no se puede vender ni reponer, pero sus datos se conservan y las ventas anteriores lo siguen mostrando. | Borrado lógico; 409 |
| RN-14 | Lo propio sólo pide estar autenticado: un cliente ve sus ventas y ninguna otra. | `/mis-ventas` y comprobación de dueño; 403 |
| RN-15 | Ningún error devuelve al cliente texto interno de la base (entregaría el mapa del esquema). Ninguna entrada inválida termina en un 500. | Traducción del `IntegrityError`; validación en el contrato |
| RN-16 | Cada alta de personal, cambio de rol y cambio de contraseña deja una línea en `evento_seguridad`, en la misma transacción que el cambio. | Un solo Unit of Work |

## Reglas derivadas de las consignas (no numeradas como RN en el PDF)
### Contratos y paginación (Ej. 3)
- Contratos de entrada con `extra="forbid"`: nadie se registra con un rol ni edita el stock por PATCH (RN-11). Ninguna respuesta incluye `password_hash`.
- PATCH aplica sólo campos enviados (`exclude_unset`).
- Códigos: 201 al crear, 204 al dar de baja un libro, 404 recurso de la ruta inexistente, 409 choque con lo guardado, 422 cuerpo/parámetros fuera de contrato.
- Listados: `{items, total, page, size, pages}`; `page` desde 1; `size` 1..100 (default 20); página más allá de la última -> **422** ("La página 4 no existe: hay 3"); `total` cuenta con los **mismos filtros** que la página; con cero resultados hay **una página, vacía**.

### Autenticación (Ej. 4)
- bcrypt con **costo configurable** (no fijo en código); toda llamada va en `to_thread` **bajo un semáforo** que limita cuántas corren a la vez; el hash se calcula **antes** de abrir la transacción (para no retener la conexión ~300 ms).
- Todo campo que termina en bcrypt (contraseña de registro, de login, **actual** y nueva del cambio) acepta **máximo 72 bytes** (bytes, no caracteres: "ñ" ocupa 2); sin ese límite una contraseña larga da 500 en lugar de 422 (bcrypt >= 5 lanza excepción).
- Orden del login: (1) límite de intentos (una consulta; si se superó -> 429 + `Retry-After` sin calcular hash); (2) verificación contra el hash del usuario o contra el **hash ficticio** si el correo no existe.
- JWT con `sub`, `exp` y los roles vigentes al emitirlo. Viaja sólo en cookie `access_token`: `HttpOnly`, `SameSite=Lax`, `Max-Age` = duración del token, `Secure` configurable. El cuerpo del login no trae el token (`{"mensaje":"Sesión iniciada","debe_cambiar_password":false,"expira_en_segundos":1800}` en el ejemplo). La dependencia lee `request.cookies`; **nunca** `Authorization`.
- Cambiar la contraseña **no** invalida sesiones abiertas ni emite token nuevo.
- `GET /auth/yo`: usuario, roles vigentes **y** los que dice el token.

### Autorización (Ej. 5)
- `vence_en` llega **con zona horaria y en el futuro**; sin zona o en el pasado -> **422** (no 409).
- Reasignar un rol vencido cierra la fila anterior y abre una nueva.
- Revocar no borra la fila.
- El historial de seguridad registra los datos iniciales con actor `SISTEMA` (texto, no usuario).

### Repositorios / UoW (Ej. 6)
- `BaseRepository[T]` recibe sesión **y clase del modelo** en el constructor (los genéricos se borran en runtime); ofrece al menos `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`. `SoftDeleteRepository[T]` hereda, lo usa `Libro`, filtra los dados de baja y agrega `get_by_id_including_deleted` y `soft_delete`.
- `add` y `update` hacen `flush()`, **nunca** `commit()`.
- Método de repositorio con nombre por lo que trae; la precarga se declara adentro del método que la necesita.
- UoW base: confirma al salir del bloque, revierte si sale con excepción, no cierra la sesión. Un UoW por módulo, con los repositorios que sus operaciones necesitan, todos con la misma sesión. El router lo construye con una dependencia; el servicio lo abre con `async with` y nunca lo construye.
- RN-02, RN-10 y RN-16 se escriben **cada una en un solo bloque**.

### Integridad (Ej. 7)
- `intento_acceso` se escribe con **sesión y transacción propias, que se confirman siempre** (también en login fallido); es la **única** escritura que no comparte la transacción de su petición. El código lo declara en un comentario con tres cosas: qué hace distinto, por qué no puede compartir la transacción y cuál es su costo (deja filas aunque la petición falle).

### Lecturas y asincronía (Ej. 8)
- Toda respuesta con datos de una relación los obtiene con carga anticipada declarada en el repositorio. El detalle de venta (cliente, renglones, libro de cada renglón **incluso dado de baja**) usa un número **fijo** de consultas.
- Aviso de comprobante con `BackgroundTasks`: `await asyncio.sleep(0.5)` + mensaje de log, corre **después de enviar la respuesta y sólo si la operación se confirmó**. El mensaje debe verse en consola con el comando normal de uvicorn (un logger propio sin configurar no aparece con el registro por defecto).

### Baja lógica en lecturas (RN-13, derivado)
- `GET /libros`, `GET /libros/{id}` y los listados `/editoriales/{id}/libros`, `/generos/{id}/libros`, `/autores/{id}/libros` excluyen los dados de baja (el repositorio `SoftDeleteRepository` filtra por defecto). `GET /libros/{id}` de un libro dado de baja -> 404 (deja de aparecer en el catálogo; ver Q-19).
- Vender o reponer un libro dado de baja -> **409** (RN-13). El detalle de una venta vieja sí lo muestra (`get_by_id_including_deleted` / precarga sin filtro).

## Manejo de errores (RN-15 + tabla de requisitos no funcionales, p. 20)
- **Quién traduce**: el router "traduce errores" (p. 9). El servicio lanza errores del dominio (no conoce HTTP); el router (o un manejador común registrado en `main.py`) los convierte en 401/403/404/409/422/429 con **mensajes propios**.
- **Unicidad**: "garantizada por la base; no se verifica con una consulta previa". El 409 de RN-01/RN-02/RN-03 sale de traducir el `IntegrityError` (SQLSTATE 23505; FK inexistente 23503 -> 409 en `POST /ventas` y `POST /libros`), nunca de un `SELECT` previo. Excepción explícita: RN-05 es "comprobación en el servicio".
- **Nunca texto de la base ni traza**: ni el `detail` del `IntegrityError`, ni nombres de restricciones o tablas.
- **Ninguna entrada inválida termina en 500** (validación en el contrato): `extra="forbid"`; parámetros de ruta no enteros -> 422 sin ejecutar el handler (C-01); ids y `cantidad` fuera del rango de `int4` (p. ej. `/libros/99999999999`) acotados en el contrato (`le=2**31-1`) para que asyncpg no lance un `DataError` -> 500; contraseñas > 72 bytes -> 422; `vence_en` sin zona o pasado -> 422; `page` fuera de rango -> 422; `size` fuera de 1..100 -> 422; renglones vacíos o con libro repetido -> 422.
- **401 vs 403**: 401 = no se sabe quién es (sin cookie, token inválido/vencido, usuario inexistente o inactivo, `Authorization: Bearer` ignorado); 403 = se sabe quién es pero no puede (rol vigente insuficiente, cambio de contraseña pendiente, venta ajena).
- **429** con `Retry-After` (RN-07), sin calcular hash. **503** en `/health/ready` si `SELECT 1` falla.
- **404** sólo para el recurso de la ruta (`/{id}`); una FK del cuerpo que no existe es **409** (choca con lo guardado), no 404.

## Excepciones globales
- Ninguna entrada inválida termina en 500; ningún error filtra texto de la base.
- Falta la clave de firma o la contraseña de la base -> la aplicación **no arranca** (sin valores por defecto; tampoco una clave inventada al arrancar).
