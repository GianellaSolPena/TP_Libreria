# Preguntas Abiertas

Nada de lo siguiente se inventó: son huecos o inconsistencias del PDF (`Parcial_Cap1a6_Consigna.pdf`) o de su cruce con el código del TP.

## Inconsistencias detectadas

### IN-01 — "Una migración nueva" vs "dos migraciones nuevas" y numeración
**PDF dice**: "A las migraciones del TP se suman dos nuevas. La tercera ... --autogenerate ... La cuarta se escribe a mano" y el criterio "dos migraciones nuevas (una a mano)". **TP actual**: 0001 y 0002. **Impacto**: ninguno si se numera 0003/0004; ids de revisión del TP son `"0001"`, `"0002"` (no hash). **Resolución propuesta**: 0003 y 0004 con esa convención.

### IN-02 — Seed del TP vs seed pedido ("Los del TP") — RESUELTA (2026-11-06, C-09)
**PDF dice**: editoriales/géneros/autores "los del TP: 3 editoriales, 3 géneros y 6 autores"; clientes Lucía Fernández, Tomás Ríos y Ana Paz. **`test/seed.sql` del TP**: 2 editoriales, 2 géneros, 5 autores; clientes Lucía, Tomás y Marta Gómez. **Impacto**: `seed.py` no puede "cargar los del TP" literalmente. **Resolución propuesta**: seed.py carga lo que dice el PDF (completando la 3.ª editorial, el 3.º género y el 6.º autor; Marta Gómez no figura en el PDF).
**Resuelta (2026-11-06, C-09 `seed-casos-readme`)**: `seed.py` carga 3 editoriales (Sudamericana, Alfaguara, Emecé), 3 géneros (Novela, Cuento, Ensayo) y 6 autores (Cortázar, Borges, Bioy Casares, Ocampo, Piglia, Sabato); clientes Lucía Fernández (con perfil), Tomás Ríos y Ana Paz (vinculada a `ana@example.com`); Marta Gómez no se carga. Completados por decisión del grupo: Emecé, Ensayo y Ernesto Sabato.

### IN-03 — Precios y stocks del seed — RESUELTA (2026-11-06, C-09)
**PDF**: stock actual Rayuela 10, Antología 5, Ficciones 8, Respiración artificial 3, Bestiario 1; venta 1 = 1 Rayuela + 2 Ficciones = 69000.00 (implica Rayuela 25000 y Ficciones 22000, o combinaciones equivalentes); ejemplo de listado muestra Antología a 30000.00. **TP**: Rayuela 25000/10, Ficciones 18000/15, Antología 22000/8, Respiración 27000/6, Bestiario 16000/12; su venta 1 es 1 Ficciones = 18000. **Impacto**: precios de Antología/Ficciones/Respiración/Bestiario no están todos fijados por el PDF (sólo se deduce Rayuela x1 + Ficciones x2 = 69000). También los ISBN del ejemplo (`978-950-00-0002-8` para Antología) difieren del seed (`...-0002-2` es Ficciones). **Resolución propuesta**: fijar Rayuela 25000 y Ficciones 22000; el resto: confirmar con la cátedra o elegir y documentar. El PDF sugiere además el **orden de ids** (lista del seed y ejemplo de `GET /libros?size=2`): 1 Rayuela (`978-950-00-0001-1`, 25000.00), 2 Antología de la literatura fantástica (`978-950-00-0002-8`, 30000.00), 3 Ficciones, 4 Respiración artificial, 5 Bestiario; el cuerpo de ejemplo de `POST /ventas` (cliente 2, libros 1 y 4) y C-11 (Rayuela + Bestiario) funcionan con ese orden. `total: 5`/`pages: 3` del ejemplo confirman 5 libros vigentes.
**Resuelta (2026-11-06, C-09 `seed-casos-readme`)**: 1 Rayuela 25000.00 (`978-950-00-0001-1`, stock 10), 2 Antología de la literatura fantástica 30000.00 (`978-950-00-0002-8`, 5), 3 Ficciones 22000.00 (`978-950-00-0003-3`, 8), 4 Respiración artificial 27000.00 (`978-950-00-0004-4`, 3), 5 Bestiario 16000.00 (`978-950-00-0005-5`, 1); venta 1 de Lucía = 1 Rayuela + 2 Ficciones = 69000.00. Los precios de 4-5 conservan los del TP; los ISBN 3-5 siguen el patrón del TP.

### IN-04 — Texto "caso C-07" de consultas fijas vs numeración del parcial
En el TP, C-07 era "consultas fijas" y C-08 "búsqueda segura"; en el parcial C-07 pasa a "revocar rol con sesión abierta" y las consultas fijas son C-15, la búsqueda segura C-16. **Impacto**: los `.http` del TP se renombran/reordenan (C-01..C-16 nuevos; los del TP se reaprovechan parcialmente).

### IN-05 — Rutas con y sin barra final
PDF: `/libros`, `/clientes`, `/ventas`... (sin barra). TP: routers con `"/"` (`/libros/`). Con la barra final de FastAPI hay un redirect 307 al pedir sin ella. **Impacto**: el despliegue D-03 usa `GET /libros/` y `POST /ventas/` (con barra) en el PDF. **Resolución propuesta**: en `parcial/` declarar las rutas sin barra (o aceptar ambas); en `despliegue/` no tocar la lógica.

### IN-06 — Datos iniciales del despliegue: `seed.sql` requiere psql
**PDF** (Ej. 10): "la base se carga ejecutando dentro del contenedor el comando de datos iniciales que indica el README del TP (docker exec libreria ...)". **TP**: el README indica `psql -U <usuario> -d libreria -f test/seed.sql`, y la imagen Alpine **no trae `psql`** ni se agrega ningún paquete ("no hace falta instalar ningún compilador"). **Impacto**: el comando del README no corre dentro del contenedor tal cual. **Resolución propuesta**: decidir (cambio permitido y anotado en DEPLOY.md) cómo cargar el seed en el contenedor (p. ej. un `seed.py` Python para el TP congelado, o instalar `postgresql-client`), y actualizar el README del TP.

### IN-07 — `/health/ready` del TP no responde 503
**PDF** (Ej. 1 y 9): `GET /health/ready` responde 503 si la base no contesta; el HEALTHCHECK de la imagen depende de ello y el PDF menciona "una ruta de salud que no responde como pedía su consigna" como defecto a corregir en el TP. **TP**: `check_database` no captura excepciones (daría 500). **Resolución propuesta**: corregir en `despliegue/` y anotarlo en DEPLOY.md; en `parcial/` implementarlo desde el principio.

## Preguntas abiertas (priorizadas)
| ID | Prioridad | Pregunta | Bloquea | Decisor |
|---|---|---|---|---|
| Q-01 | Alta | **Nombre del grupo** (el zip es `Parcial_Cap1a6_<NombreDelGrupo>.zip`) | Entrega | Grupo |
| Q-02 | Alta | **Datos de acceso al VPS** (host/IP, usuario, método de acceso), **puerto asignado** (`-p <puerto>:8000`), **URL pública**, y **base de datos que provee la cátedra** (host, usuario, contraseña, nombre; si es `host.docker.internal` u otra dirección) | Ej. 9-10 | Cátedra |
| Q-03 | Alta | Ubicación de `main.py`: el PDF lista `main.py` y `seed.py` en la raíz de la estructura y `app/core/*` y `app/modules/*` con prefijo `app/`; el TP tiene `app/main.py` y el Dockerfile usa `app.main:app`. **RESUELTA (2026-11-03, el usuario): `parcial/main.py` en la raíz (DD-08)** | Ej. 1, 6 | Grupo (y confirmar con cátedra) |
| Q-04 | — | ~~Nombres exactos de las variables de `Settings`~~ **Resuelto en C-02**: `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_SECONDS` (1800), `BCRYPT_ROUNDS` (12), `COOKIE_SECURE` (false), `DB_POOL_SIZE` (5) | — | — |
| Q-05 | Media | Contraseñas de los usuarios del seed (el PDF dice que son "de mentira") y contraseña provisoria del alta de personal | Casos C (diferida a C-09, decisión 2026-11-04). **Avance (C-06, QA-01)**: la contraseña provisoria del alta de personal la envía el ADMIN en el cuerpo de `POST /usuarios` (≤ 72 bytes, se hashea antes del UoW); **Resuelta (2026-11-06, C-09 `seed-casos-readme`)**: contraseñas de mentira del seed `admin1234` (admin), `admin21234` (admin2), `vendedor1234` (vendedor), `ana12345` (ana) y `nuevo1234` (nuevo, con cambio obligatorio); sólo en `seed.py`, los `.http` y el README, hasheadas con bcrypt en la base | — |
| Q-06 | Media | Integrantes (nombres y apellidos) para el `README.md`. El README del TP lista: Agustina Fontagnol, Martina Suarez y Gianella Peña; **Resuelta (2026-11-06, el usuario; C-09)**: se mantienen esos tres integrantes | Entrega | — |
| Q-07 | — | ~~Contenido del `motivo` de `movimiento_stock`~~ **Resuelta (2026-11-05, el usuario; C-07 QA-02)**: textos fijos «Stock inicial», «Reposición» y «Venta»; el vínculo con la venta queda en `venta_id` | Ej. 6 | — |
| Q-08 | Media | ~~¿`movimiento_stock.usuario_id` obligatorio?~~ **Resuelto por el PDF**: no lleva "(nulo)" y la Fig. 1 dibuja `MovimientoStock 0..* -> 1 Usuario` ("actor"): NOT NULL. **Resuelto (2026-11-06, C-09 `seed-casos-readme`)**: los "Stock inicial" del seed los registra `admin@example.com` y las salidas de la venta 1, `vendedor@example.com`, todo por `LibroRepository.aplicar_movimiento`. Antes abierto: qué usuario va en los "Stock inicial" del seed (propuesta: `admin@example.com`; las salidas de la venta 1, `vendedor@example.com`) y si hace falta backfill sobre bases ya pobladas (no: ver propuesta C-03). **Propuesta C-03 (design D-08)**: la 0003 no backfillea, porque `usuario_id` es NOT NULL y al migrar no existe ningún usuario; el PDF parte de base vacía + `seed.py` | seed | — |
| Q-09 | — | ~~Dónde se persiste `Cliente.usuario_id`... y si el registro crea `nombre` desde el cuerpo~~ **Resuelta (2026-11-04, el usuario; C-05 design D9/D12)**: el registro crea usuario + rol CLIENTE + ficha de cliente (`nombre` del cuerpo del registro, `usuario_id` del nuevo usuario) en una sola transacción; correo repetido (de usuario o de cliente) → 409 por UNIQUE, sin filas sueltas y sin apropiarse de la ficha existente. Ana Paz ↔ `ana@example.com` lo arma el seed (C-09) | — | — |
| Q-10 | Media | Rutas del TP que la tabla del PDF **no lista**: `GET /autores`, `GET /editoriales/{id}`, `GET /generos/{id}`, `GET /autores/{id}`, `PATCH /generos/{id}`, `GET /clientes`. ¿Se conservan? Propuesta: conservarlas (no se pueden quitar columnas, pero sí sumar rutas), las GET públicas en el grupo abierto con envoltorio de paginación en los listados, `PATCH /generos/{id}` y `GET /clientes` en el protegido con el mismo rol que sus hermanas | Ej. 3 | Grupo |
| Q-11 | — | ~~Logout y cambiar-password~~ **Resuelto por el PDF** (tabla p. 16): `POST /auth/logout` (POST, no GET), grupo abierto, "Cualquiera", 200 (borra la cookie aunque no haya sesión); `POST /auth/cambiar-password`, grupo abierto, "Autenticado", 200/401/422. **Resuelta (2026-11-04, el usuario; C-05 design D9/D12)**: contraseña *actual* incorrecta → **401** con mensaje propio («La contraseña actual no es correcta»), porque la tabla sólo admite 200/401/422 | — | — |
| Q-12 | — | ~~Rol de `GET /ventas`~~ **Resuelto por el PDF** (tabla p. 18): `GET /ventas (page, size)` = VENDEDOR, ADMIN; 200, 422 | — | — |
| Q-13 | Baja | Fecha límite de entrega: "se publica en el campus" | Entrega | Cátedra |
| Q-14 | Baja | `evidencia/` del despliegue: formato (capturas vs salida de consola) de cada caso D | Ej. 10 | Grupo |
| Q-15 | Baja | Si se incluye `.git` en el zip se revisa el historial; confirmar que ningún commit del TP contiene credenciales reales (el repo ya tiene 8 commits) | Entrega | Grupo |
| Q-17 | Baja | `asignacion_rol.otorgada_por` (nulo): la tabla la lista pero la Fig. 1 no dibuja su relación. ¿FK a `usuario` (con índice y `foreign_keys` explícito) o sólo un entero? Propuesta: FK a `usuario.id` + índice (cada FK nueva lleva índice) | Ej. 2 | Grupo |
| Q-18 | — | ~~Listados sin `page`/`size` en la tabla~~ **Resuelta (2026-11-05, el usuario; C-07 QA-06)**: `/{editoriales,generos,autores}/{id}/libros`, `/libros/{id}/movimientos` y `/clientes/{id}/ventas` devuelven el envoltorio con `page`/`size` opcionales (422 si se envían mal) | Ej. 3 | — |
| Q-19 | — | ~~`GET`/`PATCH`/`DELETE` de un libro dado de baja~~ **Resuelta (2026-11-05, el usuario; C-07 QA-07)**: 404 en las tres; `GET /libros/{id}/movimientos` de un dado de baja → 200 (historial de auditoría); reponer un dado de baja → 409 | Ej. 3, 6 | — |
| Q-20 | — | ~~¿El rechazo 429 se anota en `intento_acceso`?~~ **Resuelta (2026-11-04, el usuario; C-05 design D7/D12)**: **no** se anota; el 429 no extiende el bloqueo y C-05 encuentra exactamente los cinco fallos | — | — |
| Q-16 | Baja | [DISCOVERY] `problem`, `system_type`, `domain`, `scale`, `stack`, `needs_infra`: se infirieron con alta confianza (documento muy explícito); `scale` = `public_multi_user` (clientes se auto-registran) | — | — |

## Decisiones de C-06 (autorizacion-roles-eventos) — resueltas 2026-11-05 (el usuario aceptó las recomendaciones)
- **QA-01** (avance de Q-05): contraseña provisoria enviada por el ADMIN en el cuerpo (`password`, ≤ 72 bytes).
- **QA-02**: `rol` obligatorio en `POST /usuarios`, sólo `VENDEDOR` o `ADMIN` (un CLIENTE nace por `/auth/registro`).
- **QA-03**: no se impide que el sistema quede sin ADMIN por vencimiento; RN-05 se comprueba al revocar (vigentes ahora, usuarios activos).
- **QA-04**: revocar una asignación abierta pero vencida → 404 «no tiene ese rol vigente».
- **QA-05**: al reasignar un rol vencido, la fila anterior se cierra con `revocada_en = ahora`.
- **QA-06**: `GET /usuarios/{id}/roles` devuelve el historial completo con `vigente` por fila, sin paginar.
- **QA-07**: `GET /ventas/{id}` queda VENDEDOR/ADMIN hasta C-07 (falla cerrada).
- **QA-08**: `actor` = correo del usuario; `accion` en texto libre (operación + afectado + rol); `SISTEMA` para la carga inicial.

## Decisiones de C-07 (libros-clientes-ventas) — resueltas 2026-11-05 (el usuario aceptó las recomendaciones)
- **QA-01**: el stock se escribe con un `UPDATE` atómico condicional (`stock + n >= 0`, libro vigente) en un único punto (`LibroRepository.aplicar_movimiento`); evita la actualización perdida sin `FOR UPDATE` ni reintentos; los movimientos de una venta se aplican ordenados por `libro_id`.
- **QA-02**: motivos fijos «Stock inicial», «Reposición», «Venta» (Q-07).
- **QA-03**: `stock_inicial` 0 se admite y no crea movimiento (CHECK `cantidad <> 0`).
- **QA-04**: `autores` con al menos uno (422 si viene vacío).
- **QA-05**: `PATCH /libros/{id}` sólo `titulo` y `precio`; cualquier otro campo (incluido `stock`) → 422.
- **QA-06**: envoltorio con `page`/`size` opcionales en los listados que la tabla del PDF no detallaba (Q-18).
- **QA-07**: libro dado de baja → 404 en `GET`/`PATCH`/`DELETE`; movimientos → 200; reponer → 409 (Q-19).
- **QA-08**: `GET /ventas/{id}` inexistente → 404 para todos.
- **QA-09**: `/mis-ventas` sin ficha de cliente → 200 con página vacía.
- **QA-10**: `POST /libros/{id}/reponer` recibe `{"cantidad": n}` y responde `{libro, movimiento}`.
- **QA-11**: `/autores/{id}/libros` devuelve `Pagina[LibroRead]` como los otros dos listados.
- **QA-12** (revisada): `PATCH /clientes/{id}` con `email` sobre un cliente con usuario responde 409; el correo es la credencial de login y no diverge.
