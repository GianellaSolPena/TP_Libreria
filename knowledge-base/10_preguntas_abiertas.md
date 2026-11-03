# Preguntas Abiertas

Nada de lo siguiente se inventó: son huecos o inconsistencias del PDF (`Parcial_Cap1a6_Consigna.pdf`) o de su cruce con el código del TP.

## Inconsistencias detectadas

### IN-01 — "Una migración nueva" vs "dos migraciones nuevas" y numeración
**PDF dice**: "A las migraciones del TP se suman dos nuevas. La tercera ... --autogenerate ... La cuarta se escribe a mano" y el criterio "dos migraciones nuevas (una a mano)". **TP actual**: 0001 y 0002. **Impacto**: ninguno si se numera 0003/0004; ids de revisión del TP son `"0001"`, `"0002"` (no hash). **Resolución propuesta**: 0003 y 0004 con esa convención.

### IN-02 — Seed del TP vs seed pedido ("Los del TP")
**PDF dice**: editoriales/géneros/autores "los del TP: 3 editoriales, 3 géneros y 6 autores"; clientes Lucía Fernández, Tomás Ríos y Ana Paz. **`test/seed.sql` del TP**: 2 editoriales, 2 géneros, 5 autores; clientes Lucía, Tomás y Marta Gómez. **Impacto**: `seed.py` no puede "cargar los del TP" literalmente. **Resolución propuesta**: seed.py carga lo que dice el PDF (completando la 3.ª editorial, el 3.º género y el 6.º autor; Marta Gómez no figura en el PDF).

### IN-03 — Precios y stocks del seed
**PDF**: stock actual Rayuela 10, Antología 5, Ficciones 8, Respiración artificial 3, Bestiario 1; venta 1 = 1 Rayuela + 2 Ficciones = 69000.00 (implica Rayuela 25000 y Ficciones 22000, o combinaciones equivalentes); ejemplo de listado muestra Antología a 30000.00. **TP**: Rayuela 25000/10, Ficciones 18000/15, Antología 22000/8, Respiración 27000/6, Bestiario 16000/12; su venta 1 es 1 Ficciones = 18000. **Impacto**: precios de Antología/Ficciones/Respiración/Bestiario no están todos fijados por el PDF (sólo se deduce Rayuela x1 + Ficciones x2 = 69000). También los ISBN del ejemplo (`978-950-00-0002-8` para Antología) difieren del seed (`...-0002-2` es Ficciones). **Resolución propuesta**: fijar Rayuela 25000 y Ficciones 22000; el resto: confirmar con la cátedra o elegir y documentar. El PDF sugiere además el **orden de ids** (lista del seed y ejemplo de `GET /libros?size=2`): 1 Rayuela (`978-950-00-0001-1`, 25000.00), 2 Antología de la literatura fantástica (`978-950-00-0002-8`, 30000.00), 3 Ficciones, 4 Respiración artificial, 5 Bestiario; el cuerpo de ejemplo de `POST /ventas` (cliente 2, libros 1 y 4) y C-11 (Rayuela + Bestiario) funcionan con ese orden. `total: 5`/`pages: 3` del ejemplo confirman 5 libros vigentes.

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
| Q-05 | Media | Contraseñas de los usuarios del seed (el PDF dice que son "de mentira") y contraseña provisoria del alta de personal | Casos C | Grupo |
| Q-06 | Media | Integrantes (nombres y apellidos) para el `README.md`. El README del TP lista: Agustina Fontagnol, Martina Suarez y Gianella Peña; confirmar que sigue igual | Entrega | Grupo |
| Q-07 | Media | Contenido del `motivo` de `movimiento_stock` (texto libre vs valores fijos): el PDF cita "Stock inicial"; hay que inventar "Reposición" y "Venta" | Ej. 6 | Grupo |
| Q-08 | Media | ~~¿`movimiento_stock.usuario_id` obligatorio?~~ **Resuelto por el PDF**: no lleva "(nulo)" y la Fig. 1 dibuja `MovimientoStock 0..* -> 1 Usuario` ("actor"): NOT NULL. **Sigue abierto**: qué usuario va en los "Stock inicial" del seed (propuesta: `admin@example.com`; las salidas de la venta 1, `vendedor@example.com`) y si hace falta backfill sobre bases ya pobladas | seed | Grupo |
| Q-09 | Media | Dónde se persiste `Cliente.usuario_id` en `ana@example.com` y ficha `Ana Paz`; y si el registro sin ficha previa crea `nombre` desde el cuerpo del registro | Ej. 4 | Grupo |
| Q-10 | Media | Rutas del TP que la tabla del PDF **no lista**: `GET /autores`, `GET /editoriales/{id}`, `GET /generos/{id}`, `GET /autores/{id}`, `PATCH /generos/{id}`, `GET /clientes`. ¿Se conservan? Propuesta: conservarlas (no se pueden quitar columnas, pero sí sumar rutas), las GET públicas en el grupo abierto con envoltorio de paginación en los listados, `PATCH /generos/{id}` y `GET /clientes` en el protegido con el mismo rol que sus hermanas | Ej. 3 | Grupo |
| Q-11 | — | ~~Logout y cambiar-password~~ **Resuelto por el PDF** (tabla p. 16): `POST /auth/logout` (POST, no GET), grupo abierto, "Cualquiera", 200 (borra la cookie aunque no haya sesión); `POST /auth/cambiar-password`, grupo abierto, "Autenticado", 200/401/422. **Sigue abierto**: qué código da una contraseña *actual* incorrecta en el cambio (la tabla sólo admite 200, 401, 422; propuesta 401 con mensaje propio, o 422) | Ej. 4 | Grupo |
| Q-12 | — | ~~Rol de `GET /ventas`~~ **Resuelto por el PDF** (tabla p. 18): `GET /ventas (page, size)` = VENDEDOR, ADMIN; 200, 422 | — | — |
| Q-13 | Baja | Fecha límite de entrega: "se publica en el campus" | Entrega | Cátedra |
| Q-14 | Baja | `evidencia/` del despliegue: formato (capturas vs salida de consola) de cada caso D | Ej. 10 | Grupo |
| Q-15 | Baja | Si se incluye `.git` en el zip se revisa el historial; confirmar que ningún commit del TP contiene credenciales reales (el repo ya tiene 8 commits) | Entrega | Grupo |
| Q-17 | Baja | `asignacion_rol.otorgada_por` (nulo): la tabla la lista pero la Fig. 1 no dibuja su relación. ¿FK a `usuario` (con índice y `foreign_keys` explícito) o sólo un entero? Propuesta: FK a `usuario.id` + índice (cada FK nueva lleva índice) | Ej. 2 | Grupo |
| Q-18 | Baja | `GET /editoriales/{id}/libros`, `/generos/{id}/libros`, `/autores/{id}/libros` y `GET /libros/{id}/movimientos` no muestran `(page, size)` ni 422 en la tabla, pero Ej. 3 dice "los listados devuelven el envoltorio". Propuesta: devolver el envoltorio con `page`/`size` por defecto (422 sólo si se envían mal) | Ej. 3 | Grupo |
| Q-19 | Baja | `GET /libros/{id}` / `PATCH /libros/{id}` / `DELETE /libros/{id}` sobre un libro ya dado de baja: el PDF sólo dice que deja de aparecer en el catálogo. Propuesta: 404 en las tres | Ej. 3, 6 | Grupo |
| Q-20 | Baja | ¿El rechazo 429 se anota en `intento_acceso`? Ej. 7: "cada intento de login, correcto o fallido"; C-05 sólo exige que estén los cinco fallos. Si se anota como fallido, extiende el bloqueo mientras sigan intentando | Ej. 4, 7 | Grupo |
| Q-16 | Baja | [DISCOVERY] `problem`, `system_type`, `domain`, `scale`, `stack`, `needs_infra`: se infirieron con alta confianza (documento muy explícito); `scale` = `public_multi_user` (clientes se auto-registran) | — | — |
