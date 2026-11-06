# Design

## Context

- Ver `proposal.md` (Why). Estado observado en `parcial/` tras C-08:
  - No hay `seed.py`. Hay `test/seed.sql` del TP: sólo catálogo, clientes y una venta (2 editoriales, 2 géneros, 5 autores, Marta Gómez, Ficciones a 18000, venta 1 = 18000). No carga usuarios, roles, movimientos ni eventos, y vacía con `TRUNCATE` sólo las tablas del TP.
  - `test/` mezcla los `.http` del TP (C-01..C-08 con la numeración vieja, IN-04, más `C-07_CapturasPantalla/`) con archivos por change (`auth.http`, `autorizacion.http`, `libros_clientes_ventas.http`, `C-15_detalle_consultas_fijas.http`) que crean usuarios `c0x.`, piden dar el primer ADMIN por psql y limpiar filas a mano (incluso desactivando el disparador dentro de una transacción).
  - `evidencia/C-15_consultas_detalle_venta.txt` se tomó con datos `c08.` (4 SELECT con el VENDEDOR).
  - Piezas reutilizables: `app.core.config.get_settings()` (falla nombrando la variable si falta `POSTGRES_PASSWORD`/`JWT_SECRET_KEY`), `app.core.database.create_engine`/`create_session_factory`, `app.core.security.hashear_password` (bcrypt en `asyncio.to_thread` con semáforo), los modelos SQLModel y `LibroRepository.aplicar_movimiento` (único punto de escritura del stock: `UPDATE` atómico condicional + movimiento).
  - Rutas relevantes y roles: `POST/PATCH/DELETE /libros`, `/libros/{id}/reponer` y `/libros/{id}/movimientos` son ADMIN; `POST/GET /ventas` personal (VENDEDOR, ADMIN); `GET /ventas/{id}` y `/mis-ventas` autenticado (decide el servicio); `/usuarios/*` y `/eventos` ADMIN; `/auth/yo` devuelve `usuario`, `roles_vigentes` y `roles_token`.
- Restricciones: sin pytest (DD-01); no se toca `app/`, `main.py`, migraciones ni `despliegue/`; el PDF manda sobre la KB.

## Goals / Non-Goals

**Goals:**
- Un estado inicial único, determinista y conocido (ids incluidos) sobre el que corren todos los casos C.
- Que cada archivo de casos sea autocontenido: `python seed.py` + correr el archivo en orden, sin psql previo.
- Que un corrector pueda levantar el proyecto sólo con el README.

**Non-Goals:**
- No se agregan endpoints, validaciones ni cambios de comportamiento de la API; si un caso revela un defecto, se registra y se corrige en un change aparte (o se discute antes de tocar `app/`).
- No se automatiza la corrida de los `.http` (no hay runner; se corren con REST Client).
- No se toca el seed ni los casos del TP congelado en `despliegue/` (C-10/C-11, IN-06).

## Decisions

### D1 — `seed.py` asincrónico que reutiliza la configuración y el motor de la aplicación
`asyncio.run(main())`: `get_settings()` → `create_engine(settings)` → `create_session_factory(engine)` → una sesión y **una transacción** (`async with session.begin()`) → `engine.dispose()` en `finally`. Así toma las mismas variables de `.env` (sin credenciales en el archivo), el mismo driver asyncpg y el mismo costo bcrypt.
- *Alternativa*: SQL plano por psql como el TP (`seed.sql`). Se descarta: el PDF pide `python seed.py`, los hashes bcrypt requieren Python y en Alpine no hay psql (IN-06).
- *Alternativa*: engine sincrónico (psycopg). Se descarta: agrega una dependencia sólo para el script.

### D2 — Vaciado con un único `TRUNCATE ... RESTART IDENTITY CASCADE` de todas las tablas del modelo
La lista se arma de `SQLModel.metadata.sorted_tables` (todas las tablas de la aplicación; `alembic_version` no está en el metadata, así que no se toca) y se emite en una sola sentencia con nombres citados. `TRUNCATE` no dispara los disparadores `FOR EACH ROW` de DELETE, así que el de sólo agregado no se desactiva ni se debilita (DD-10). Va dentro de la misma transacción que la carga: si la carga falla, el rollback deshace también el vaciado.
- *Alternativa*: lista fija de tablas. Se descarta: si un change futuro agrega una tabla, el seed quedaría dejando filas viejas.

### D3 — Ids deterministas por orden de inserción, no explícitos
Tras `RESTART IDENTITY` las secuencias vuelven a 1, así que se insertan las filas en el orden de los ids deseados y se hace `flush()` por grupo; después del flush el script **comprueba** que los ids obtenidos son los esperados (p. ej. Rayuela = 1, Antología = 2) y aborta si no. Evita `setval` y los ids a mano del TP, que desfasaban las secuencias.

### D4 — Datos concretos del catálogo (IN-02/IN-03)
Lo fijado por el PDF se respeta literal; lo no fijado se toma del `seed.sql` del TP y lo que falta se completa (anotado en la KB, `10` IN-02/IN-03):

| id | Editorial | Género | Autor |
|---|---|---|---|
| 1 | Sudamericana (Argentina) | Novela | Julio Cortázar |
| 2 | Alfaguara (España) | Cuento | Jorge Luis Borges |
| 3 | Emecé (Argentina) *(nueva)* | Ensayo *(nuevo)* | Adolfo Bioy Casares |
| 4 | | | Silvina Ocampo |
| 5 | | | Ricardo Piglia |
| 6 | | | Ernesto Sabato *(nuevo)* |

| id | Libro | ISBN | Precio | Stock inicial → actual | Editorial · Género | Autores (rol, orden) |
|---|---|---|---|---|---|---|
| 1 | Rayuela | 978-950-00-0001-1 | 25000.00 | 11 → 10 | 1 · 1 | Cortázar (autor, 1) |
| 2 | Antología de la literatura fantástica | 978-950-00-0002-8 | 30000.00 | 5 → 5 | 2 · 2 | Borges (autor, 1), Bioy Casares (coautor, 2), Ocampo (coautor, 3) |
| 3 | Ficciones | 978-950-00-0003-3 | 22000.00 | 10 → 8 | 1 · 2 | Borges (autor, 1) |
| 4 | Respiración artificial | 978-950-00-0004-4 | 27000.00 | 3 → 3 | 2 · 1 | Piglia (autor, 1) |
| 5 | Bestiario | 978-950-00-0005-5 | 16000.00 | 1 → 1 | 1 · 2 | Cortázar (autor, 1) |

Ids y precios de 1-3 y el ISBN de 1-2 salen del ejemplo `GET /libros?size=2` y de la venta 1 (1×25000 + 2×22000 = 69000); Respiración y Bestiario conservan el precio del TP; los ISBN 3-5 siguen el patrón del TP sin chocar con el `978-950-00-0006-6` del ejemplo de `POST /libros`. Autores 3 y 4 (Bioy Casares, Ocampo) son los coautores del ejemplo de `POST /libros`. Sólo «Ficciones» contiene «ficc» (C-16).

### D5 — Personas: usuarios, roles, clientes (Q-05, Q-09)
| id | Usuario | Nombre | Rol vigente | Cambio obligatorio | Contraseña (propuesta Q-05) |
|---|---|---|---|---|---|
| 1 | admin@example.com | Administración | ADMIN | no | `admin1234` |
| 2 | admin2@example.com | Administración 2 | ADMIN | no | `admin21234` |
| 3 | vendedor@example.com | Vendedor | VENDEDOR | no | `vendedor1234` |
| 4 | ana@example.com | Ana Paz | CLIENTE | no | `ana12345` |
| 5 | nuevo@example.com | Personal nuevo | VENDEDOR | **sí** | `nuevo1234` |

- Hashes con `hashear_password` **antes** de abrir la transacción (como hace la API), con el costo de `Settings`.
- `asignacion_rol` abiertas: `desde = ahora`, `vence_en`/`revocada_en`/`otorgada_por` nulos (otorgadas por el sistema).
- Clientes: 1 Lucía Fernández `lucia@example.com` + perfil (`11-5555-0001`, `Av. Corrientes 1234`, del TP); 2 Tomás Ríos `tomas@example.com`; 3 Ana Paz `ana@example.com` con `usuario_id = 4` (mismo correo que su usuario, QA-12 de C-07). Marta Gómez del TP no se carga (IN-02).
- *Alternativa*: crear los usuarios con los servicios (`/auth/registro`, `POST /usuarios`). Se descarta: generarían un evento por alta y el PDF pide **una** línea `SISTEMA`; además el primer ADMIN no puede crearse por la API.

### D6 — Stock y venta 1 por el punto único de escritura
Los libros se insertan con `stock = 0` y su stock se escribe sólo con `LibroRepository(session).aplicar_movimiento(...)`: «Stock inicial» por libro con `usuario_id = 1` (admin, propuesta Q-08); luego la venta 1 (cliente 1, `fecha` fija `2026-10-01T15:00:00Z`, total 69000.00) con renglones Rayuela ×1 a 25000.00 y Ficciones ×2 a 22000.00 (precio copiado del libro), y sus dos salidas «Venta» −1/−2 con `venta_id = 1` y `usuario_id = 3` (vendedor). Así el seed respeta RN «un solo punto de escritura del stock» y el invariante sale por construcción. Antes de confirmar, una consulta compara `libro.stock` con `SUM(movimiento_stock.cantidad)` por libro y aborta (rollback) si alguno difiere.
- *Alternativa*: insertar `stock` final y movimientos a mano. Se descarta: duplica la lógica del stock fuera del punto único.

### D7 — Evento `SISTEMA` y cierre
Se agrega una sola fila `EventoSeguridad(actor="SISTEMA", accion="Carga de los datos iniciales")`. `intento_acceso` queda vacía por el TRUNCATE. Al terminar se imprime un resumen breve (conteos por tabla y usuarios de prueba) para que el README pueda mostrarlo. Errores: cualquier excepción revierte y sale con código ≠ 0; la falta de variables la reporta `Settings` (mensaje que nombra la variable).

### D8 — Un `.http` por caso, con los usuarios del seed
Nombres: `C-01_parametro_no_entero.http`, `C-02_registro_correo_repetido.http`, `C-03_cookie_login.http`, `C-04_credenciales_indistinguibles.http`, `C-05_limite_intentos.http`, `C-06_401_403_lo_propio.http`, `C-07_revocar_rol_sesion_abierta.http`, `C-08_autoproteccion_admin.http`, `C-09_cambio_obligatorio.http`, `C-10_venta_valida.http`, `C-11_venta_sin_stock.http`, `C-12_venta_inexistentes_o_baja.http`, `C-13_reponer_baja_reuso_isbn.http`, `C-15_detalle_consultas_fijas.http`, `C-16_busqueda_paginacion_patch.http`. Encabezado común: `@host`, credenciales del seed como variables, bloque «Precondiciones» (`alembic upgrade head`, `python seed.py`, `uvicorn main:app`, `SQL_ECHO=true` sólo en C-15). Cada login con `# @name loginX`; las peticiones con `# @no-cookie-jar` + `Cookie: {{loginX.response.headers.Set-Cookie}}`; los ids creados en el archivo se toman con `{{nombre.response.body.$.id}}`.

Guion por caso (sobre los ids de D4/D5):
- **C-01**: login vendedor; `GET /ventas/abc` → 422 (y `GET /usuarios/abc/roles` con admin → 422).
- **C-02**: registro nuevo → 201; registro con `ana@example.com` (correo de usuario) → 409; con `tomas@example.com` (cliente sin usuario) → 409 y no se apropia de la ficha; psql comentado: ningún `usuario` con esos correos, cliente 2 sigue sin `usuario_id`.
- **C-03**: login ana → 200, `Set-Cookie` HttpOnly/SameSite=Lax/Max-Age, cuerpo `{mensaje, debe_cambiar_password, expira_en_segundos}`; `/auth/yo` con cookie 200; sin cookie 401; sólo `Authorization: Bearer` 401 (JWT pegado del `Set-Cookie`, como en `auth.http` de C-05).
- **C-04**: login `vendedor@` con contraseña mala y `noexiste@example.com` → 401 con cuerpo idéntico (comentario: tiempo parecido en la columna de REST Client).
- **C-05**: cinco fallos de `admin2@example.com` → 401; sexto → 429 con `Retry-After` y en pocos ms; psql comentado: 5 filas en `intento_acceso` para ese correo e IP.
- **C-06**: `POST /libros` sin cookie → 401; con vendedor → 403; vendedor `POST /ventas` para el cliente 3 (Ana) → 201; ana `GET /ventas/{esa}` → 200; ana `GET /ventas/1` (de Lucía) → 403.
- **C-07**: login admin y vendedor; vendedor `GET /ventas` → 200; admin `DELETE /usuarios/3/roles/VENDEDOR` → 200; vendedor, misma cookie, `GET /ventas` → 403; vendedor `/auth/yo` → `roles_token` con VENDEDOR y `roles_vigentes` vacío; admin `GET /usuarios/3/roles` → la fila revocada con `revocada_en`; admin `POST /usuarios/3/roles` con `vence_en` pasado → 422 y sin zona → 422.
- **C-08**: admin `DELETE /usuarios/1/roles/ADMIN` → 409; `GET /auth/yo` sigue ADMIN.
- **C-09**: login `nuevo@` → 200 con `debe_cambiar_password: true`; `GET /ventas` → 403; `GET /auth/yo` → 200; `POST /auth/cambiar-password` → 200; misma cookie `GET /ventas` → 200; `/auth/yo` → `debe_cambiar_password: false`.
- **C-10**: vendedor `POST /ventas` con el cuerpo de ejemplo del PDF (cliente 2, libro 1 ×2, libro 4 ×1) → 201, precios 25000.00/27000.00, total 77000.00; `GET /libros/1` stock 8, `/libros/4` stock 2; admin `GET /libros/1/movimientos` con la salida −2; comentario: aviso del comprobante en la consola de uvicorn después de la línea de la respuesta.
- **C-11**: venta Rayuela ×1 + Bestiario ×2 → 409; `GET /ventas` total 1; `GET /libros/1` stock 10; psql comentado de `stock == SUM` (7 movimientos).
- **C-12**: venta con cliente 999 → 409; con libro 999 → 409; admin `DELETE /libros/5` → 204 y venta con libro 5 → 409; `GET /ventas` total 1; psql comentado.
- **C-13**: admin `POST /libros/3/reponer {"cantidad": 5}` → 200 con movimiento «Reposición»; `DELETE /libros/3` → 204; `GET /libros?titulo=ficc` total 0; `POST /libros` con ISBN `978-950-00-0003-3` → 201 (id 6); otra vez → 409; `GET /ventas/1` → renglón «Ficciones».
- **C-15**: vendedor `POST /ventas` de 4 renglones (cliente 2; libros 1, 2, 3, 4 ×1) → 201; `GET /ventas/1` (2 renglones) y `GET /ventas/{nueva}` (4) con la misma cookie; esperado 4 SELECT en cada uno (usuario, roles, venta+cliente, renglones+libros); un tercer detalle con la dueña (ana) no aplica porque la venta 1 no es suya.
- **C-16**: `GET /libros?titulo=' OR '1'='1` (URL-codificado) → 200 `items` [] `total` 0; `titulo=ficc&size=1` → total 1, pages 1; `&page=2` → 422; `size=500` → 422; admin `PATCH /libros/1 {"precio": "26000.00"}` → 200, título y stock iguales; `PATCH /libros/1 {"stock": 99}` → 422; `PATCH /editoriales/3 {"pais": "Uruguay"}` → 200, nombre igual.

### D9 — Qué se retira de `test/` y qué se reubica
Se borran `seed.sql`, `C-01..C-08` del TP, `C-07_CapturasPantalla/`, `auth.http`, `autorizacion.http`, `libros_clientes_ventas.http`; el historial git los conserva. Las comprobaciones extra que no son casos del PDF (contraseñas de 72/73 bytes, campo extra 422, rol en el registro, logout, alta de personal 409, `Retry-After` vencido) se reubican como peticiones adicionales en el caso afín (C-02, C-03, C-05, C-09) marcadas «(extra)», para no perder cobertura. `solo_agregado.sql` no cambia (ya es autocontenido y termina en ROLLBACK).
- *Alternativa*: conservar los archivos por change. Se descarta: necesitan psql previo y prefijos `c0x.`, contradicen «antes de cada archivo se corre `python seed.py`» y confunden al corrector (ver Open Questions, QA-03).

### D10 — Evidencia en texto plano
- **C-14**: `python seed.py` y luego `psql -v ON_ERROR_STOP=0 -f test/solo_agregado.sql` (en este entorno vía `docker exec -i libreria-pg psql -U libreria -d libreria ... < test/solo_agregado.sql`), salida completa (stdout+stderr) a `evidencia/C-14_solo_agregado.txt` con un encabezado de comando y fecha. Texto en lugar de captura de imagen: es legible, versionable y el PDF dice «captura de psql» sin exigir formato.
- **C-15**: `python seed.py`, uvicorn con `SQL_ECHO=true` y su salida redirigida a un archivo temporal; se corre `C-15_detalle_consultas_fijas.http`; se extrae el bloque de cada detalle (con el mismo formato que el archivo actual: encabezado por petición, SELECT contados) a `evidencia/C-15_consultas_detalle_venta.txt`.

### D11 — README
Se reescribe sobre la estructura del actual: integrantes (Q-06), requisitos, puesta en marcha 1-6 (venv, deps, `.env` + tabla de variables + `python -c "import secrets; print(secrets.token_urlsafe(32))"`, `alembic upgrade head`, `python seed.py`, `uvicorn main:app`), usuarios del seed, estructura del proyecto (cap. 1-6), tabla de endpoints actual (sin barra final, `page`/`size`), casos C-01..C-16 con archivo y evidencia, decisiones de diseño breves. Se verifica siguiéndolo sobre una base vacía (`downgrade base` → `upgrade head` → `seed` → servidor → `/health/ready` y `GET /libros`).

## Risks / Trade-offs

- [El TRUNCATE requiere permisos de dueño de las tablas] → el usuario de `.env` es el mismo que corre las migraciones; se documenta en el README.
- [bcrypt de 5 contraseñas con costo 12 tarda ~1-2 s] → aceptable; se hashea antes de abrir la transacción para no tenerla abierta.
- [Ids deterministas dependen del orden de inserción] → comprobación explícita de ids tras cada `flush` (D3); si falla, rollback con mensaje.
- [C-05 deja `admin2` bloqueado 60 s] → sólo afecta al resto de ese archivo; el siguiente `python seed.py` vacía `intento_acceso`.
- [C-03 necesita pegar el JWT a mano para el caso Bearer] → es un paso del cliente HTTP, no de la base; queda indicado en el comentario.
- [Las contraseñas de mentira aparecen en `seed.py`, los `.http` y el README] → son de mentira por definición del PDF; nunca se usan fuera de los datos iniciales y no hay secretos reales.
- [Un caso puede revelar un defecto de la API] → se registra; no se corrige dentro de este change sin acordarlo (Non-Goals).
- [Borrar los archivos por change pierde la documentación de esos changes] → quedan en git y en los archivos de `openspec/changes/archive/`; lo extra se reubica (D9).

## Migration Plan

1. `seed.py` y verificación del estado (spec `datos-iniciales`).
2. Casos `.http` nuevos, uno por uno contra uvicorn tras `python seed.py`; recién cuando todos pasan se retiran los viejos.
3. Evidencia C-14 y C-15.
4. README y prueba desde cero.
Rollback: revertir los commits del change (no hay migraciones ni cambios en `app/`).

## Open Questions

Decisiones que el grupo puede confirmar o cambiar sin alterar specs ni tareas (se aplica la recomendación si no hay respuesta):
- **QA-01 (Q-06)**: integrantes del README. Recomendación: los del TP (Agustina Fontagnol, Martina Suarez y Gianella Peña) hasta que el grupo confirme.
- **QA-02 (Q-05)**: contraseñas de mentira del seed. Recomendación: las de la tabla D5 (≥ 8 caracteres, ASCII, sin relación con contraseñas reales).
- **QA-03**: retirar `auth.http`, `autorizacion.http` y `libros_clientes_ventas.http` reubicando sus comprobaciones extra en los casos (D9). Alternativa: conservarlos en una subcarpeta `test/extra/`.
- **QA-04 (Q-08)**: los «Stock inicial» los registra `admin@example.com`. Recomendación: sí (propuesta original de la KB).
- **QA-05**: completar la 3.ª editorial (Emecé), el 3.º género (Ensayo) y el 6.º autor (Ernesto Sabato), y los ISBN 3-5 según D4. Cualquier valor sirve mientras no se use «ficc» en otro título.
