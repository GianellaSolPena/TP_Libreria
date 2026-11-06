# Librería · Parcial Programación III (Capítulos 1-6)

Integrantes: Agustina Fontagnol, Martina Suarez y Gianella Peña

API REST con FastAPI, SQLModel y PostgreSQL (asyncpg). Catálogo de libros, autores, editoriales y
géneros, clientes y ventas, con autenticación por cookie (JWT), roles (ADMIN, VENDEDOR, CLIENTE),
control de stock por movimientos y un historial de seguridad.

## Requisitos

- Python 3.12 o superior
- PostgreSQL 16 con una base vacía (por ejemplo `libreria`) y un usuario que sea dueño de sus
  tablas: es el mismo que corre las migraciones y `seed.py` (que vacía las tablas con `TRUNCATE`)
- Opcional: la extensión *REST Client* de VS Code (o un IDE de JetBrains) para los archivos `.http`
  y `psql` para las comprobaciones de base

## Puesta en marcha (desde cero)

Todos los comandos se ejecutan dentro de la carpeta `parcial/`.

1. **Entorno virtual y dependencias**

   ```bash
   python -m venv .venv
   ```

   | Sistema | Activar el entorno |
   |---|---|
   | Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
   | Windows (Git Bash) | `source .venv/Scripts/activate` |
   | Linux / macOS | `source .venv/bin/activate` |

   ```bash
   pip install -r requirements.txt
   ```

2. **Variables de entorno.** Copiá `env.example` como `.env` y completá tus datos. El archivo
   `.env` no se versiona y no debe llevar secretos de verdad en ningún archivo del repositorio.

   | Sistema | Copiar |
   |---|---|
   | Windows (PowerShell) | `Copy-Item env.example .env` |
   | Linux / macOS / Git Bash | `cp env.example .env` |

   | Variable | Descripción |
   |---|---|
   | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Credenciales y base de PostgreSQL (sin valor por defecto) |
   | `POSTGRES_HOST`, `POSTGRES_PORT` | Dirección de la base. Por defecto `localhost` y `5432` |
   | `SQL_ECHO` | `true` para ver en la consola las consultas SQL (necesario para el caso C-15). Por defecto `false` |
   | `DB_POOL_SIZE` | Tamaño del pool de conexiones. Por defecto `5` |
   | `JWT_SECRET_KEY` | Clave de firma del token (sin valor por defecto). Generala con el comando de abajo |
   | `ACCESS_TOKEN_EXPIRE_SECONDS` | Duración del token y de la cookie en segundos. Por defecto `1800` |
   | `BCRYPT_ROUNDS` | Costo de bcrypt. Por defecto `12` |
   | `COOKIE_SECURE` | `true` cuando se sirve por HTTPS. Por defecto `false` |

   Para generar la clave de firma y pegarla en `JWT_SECRET_KEY`:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   Si falta `POSTGRES_PASSWORD` o `JWT_SECRET_KEY`, tanto el servidor como `seed.py` terminan con un
   error que nombra la variable.

3. **Crear las tablas** con Alembic (el proyecto no usa `create_all`):

   ```bash
   alembic upgrade head
   ```

   Hay cuatro migraciones: el esquema inicial, `genero`, los accesos/movimientos/borrado lógico
   (autogenerada) y el disparador de sólo agregado de `movimiento_stock` (escrita a mano).

4. **Carga inicial de datos.** Es parte de la puesta en marcha: deja la base con los datos del
   enunciado. Se puede correr las veces que haga falta: vacía todas las tablas de la aplicación
   (`TRUNCATE ... RESTART IDENTITY`, sin tocar el esquema ni el disparador) y vuelve a cargar los
   mismos datos con los mismos ids, todo en una transacción.

   ```bash
   python seed.py
   ```

5. **Levantar el servidor**

   ```bash
   uvicorn main:app
   ```

   - Documentación interactiva: <http://localhost:8000/docs>
   - Estado: `GET /health/live` (sin tocar la base) y `GET /health/ready` (ejecuta `SELECT 1`)

6. **Comprobar** que quedó andando:

   ```bash
   curl http://localhost:8000/health/ready
   curl "http://localhost:8000/libros?size=2"
   ```

   El segundo pedido devuelve `total` 5, `pages` 3 y los libros 1 (Rayuela) y 2 (Antología de la
   literatura fantástica).

## Datos iniciales (`seed.py`)

Usuarios (las contraseñas son **de mentira**, sólo para estos datos; en la base se guardan hasheadas
con bcrypt):

| Correo | Contraseña | Rol vigente | Notas |
|---|---|---|---|
| `admin@example.com` | `admin1234` | ADMIN | |
| `admin2@example.com` | `admin21234` | ADMIN | |
| `vendedor@example.com` | `vendedor1234` | VENDEDOR | |
| `ana@example.com` | `ana12345` | CLIENTE | ficha de cliente 3 (Ana Paz) |
| `nuevo@example.com` | `nuevo1234` | VENDEDOR | debe cambiar la contraseña (C-09) |

Catálogo: 3 editoriales, 3 géneros, 6 autores y 5 libros (1 Rayuela 25000.00 stock 10, 2 Antología de
la literatura fantástica 30000.00 stock 5, 3 Ficciones 22000.00 stock 8, 4 Respiración artificial
stock 3, 5 Bestiario stock 1). Clientes: 1 Lucía Fernández (con perfil), 2 Tomás Ríos, 3 Ana Paz.
Venta 1 de Lucía (1 Rayuela + 2 Ficciones = 69000.00). Hay un movimiento «Stock inicial» por libro y
dos de «Venta», de modo que `stock` coincide con la suma de movimientos. El historial de seguridad
queda con una sola línea, actor `SISTEMA`: «Carga de los datos iniciales».

## Estructura

```
main.py                  # App, lifespan (motor y fábrica de sesiones), grupos de rutas
seed.py                  # Datos iniciales (python seed.py)
app/
├── core/                # config, database, security (bcrypt/JWT/cookie), dependencies, errores,
│                        # paginacion, repository y unit_of_work base
└── modules/
    ├── health/          # sólo router.py
    ├── usuarios/        # registro, login, roles, historial de seguridad (/auth, /usuarios, /eventos)
    ├── editoriales/
    ├── generos/
    ├── autores/
    ├── libros/          # incluye LibroAutor y MovimientoStock
    ├── clientes/        # incluye PerfilCliente
    └── ventas/          # incluye RenglonVenta
        # cada módulo: models · schemas · repository · service · unit_of_work · router
migrations/              # Alembic (plantilla asincrónica) y versions/ (0001 a 0004)
test/                    # un .http por caso C-01 a C-16 (salvo C-14), los extra RN-03_rol_ya_vigente.http y
                         # RN-15_caracter_nulo.http, y solo_agregado.sql
evidencia/               # migraciones_ida_y_vuelta.txt; C-01_corrida.txt a C-13_corrida.txt, C-16_corrida.txt y
                         # RN-15_corrida.txt; C-14_solo_agregado.txt y C-14_captura_psql.png;
                         # C-15_consultas_detalle_venta.txt
```

Capas: el router arma la unidad de trabajo, el servicio aplica las reglas, el repositorio accede a
los datos y el modelo define la tabla.

## Endpoints

Sin barra final. Los listados devuelven `{items, total, page, size, pages}` y se paginan con `page`
(desde 1) y `size` (1 a 100, por defecto 20).

| Recurso | Rutas | Acceso |
|---|---|---|
| Health | `GET /health/live`, `GET /health/ready` | público |
| Auth | `POST /auth/registro`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/yo`, `POST /auth/cambiar-password` | público (`yo` y `cambiar-password` con sesión) |
| Usuarios | `POST /usuarios`, `GET /usuarios/{id}/roles`, `POST /usuarios/{id}/roles`, `DELETE /usuarios/{id}/roles/{rol}` | ADMIN |
| Eventos | `GET /eventos` | ADMIN |
| Editoriales / Géneros / Autores | `GET` lista, `GET /{id}` y `GET /{id}/libros` públicos; `POST` y `PATCH /{id}` | lectura pública, escritura ADMIN |
| Libros | `GET /libros` (`titulo`, `genero_id`, `page`, `size`), `GET /libros/{id}` | público |
| Libros (escritura) | `POST /libros`, `PATCH /libros/{id}` (`titulo`, `precio`), `DELETE /libros/{id}` (baja lógica), `POST /libros/{id}/reponer`, `GET /libros/{id}/movimientos` | ADMIN |
| Clientes | `POST /clientes`, `GET /clientes`, `GET /clientes/{id}`, `PATCH /clientes/{id}`, `POST /clientes/{id}/perfil`, `GET /clientes/{id}/ventas` | VENDEDOR o ADMIN |
| Ventas | `POST /ventas`, `GET /ventas` | VENDEDOR o ADMIN |
| Ventas (consulta) | `GET /ventas/{id}` (el cliente sólo ve las propias), `GET /mis-ventas` | con sesión |

Códigos de respuesta: 201 al crear, 204 en la baja, 401 sin sesión, 403 sin el rol (o con el cambio de
contraseña pendiente), 404 si el recurso no existe, 409 cuando se viola una regla o la base rechaza
la escritura (único, clave foránea, stock), 422 si el cuerpo o los parámetros no cumplen el contrato
y 429 tras demasiados intentos de login fallidos. Los errores llevan un mensaje propio, nunca el
texto de la base.

## Casos de prueba

Los archivos de `test/` usan el formato de la extensión *REST Client* (también funcionan en los IDE
de JetBrains). **Antes de correr cada archivo, ejecutá `python seed.py`** (con la base migrada y
`uvicorn main:app` arriba): cada archivo es autocontenido y se puede correr en cualquier orden. Cada
petición lleva su respuesta esperada en un comentario; las comprobaciones que sólo se ven en la base
quedan como consultas `psql` comentadas al final del archivo. Las peticiones marcadas «(extra)» son
comprobaciones adicionales a los casos del enunciado.

| Caso | Archivo | Condición | Qué demuestra | Evidencia |
|---|---|---|---|---|
| C-01 | `C-01_parametro_no_entero.http` | | Parámetro de ruta no entero → 422 | `evidencia/C-01_corrida.txt` |
| C-02 | `C-02_registro_correo_repetido.http` | psql (final) | Registro 201; correo repetido de usuario o de cliente → 409 sin filas sueltas | `evidencia/C-02_corrida.txt` |
| C-03 | `C-03_cookie_login.http` | | Cookie HttpOnly, SameSite=Lax y Max-Age; sin token en el cuerpo; sin cookie o sólo Bearer → 401 | `evidencia/C-03_corrida.txt` |
| C-04 | `C-04_credenciales_indistinguibles.http` | | Correo existente con contraseña mala y correo inexistente → mismo 401 | `evidencia/C-04_corrida.txt` |
| C-05 | `C-05_limite_intentos.http` | psql (final) | Sexto intento fallido → 429 con `Retry-After`; cinco filas en `intento_acceso` | `evidencia/C-05_corrida.txt` |
| C-06 | `C-06_401_403_lo_propio.http` | | 401 sin sesión, 403 sin rol; la cliente ve su venta (200) y la ajena (403) | `evidencia/C-06_corrida.txt` |
| C-07 | `C-07_revocar_rol_sesion_abierta.http` | psql (final) | Rol revocado con sesión abierta → la misma cookie recibe 403; vencimiento pasado o sin zona → 422 | `evidencia/C-07_corrida.txt` |
| C-08 | `C-08_autoproteccion_admin.http` | | El ADMIN no puede revocarse su propio ADMIN → 409 | `evidencia/C-08_corrida.txt` |
| C-09 | `C-09_cambio_obligatorio.http` | | Cambio de contraseña obligatorio: 403 salvo `/auth`; luego la misma cookie entra | `evidencia/C-09_corrida.txt` |
| C-10 | `C-10_venta_valida.http` | psql (final) | Venta de dos renglones: 201, precios copiados, total, stock y movimientos; aviso del comprobante en la consola de uvicorn | `evidencia/C-10_corrida.txt` |
| C-11 | `C-11_venta_sin_stock.http` | psql (final) | Sin stock suficiente → 409 y nada cambia | `evidencia/C-11_corrida.txt` |
| C-12 | `C-12_venta_inexistentes_o_baja.http` | psql (final) | Cliente o libro inexistente o dado de baja → 409 | `evidencia/C-12_corrida.txt` |
| C-13 | `C-13_reponer_baja_reuso_isbn.http` | | Reponer, baja lógica, reuso del ISBN y título intacto en la venta vieja | `evidencia/C-13_corrida.txt` |
| C-14 | `solo_agregado.sql` | `psql -f` | `movimiento_stock` rechaza UPDATE y DELETE | `evidencia/C-14_solo_agregado.txt` y `evidencia/C-14_captura_psql.png` |
| C-15 | `C-15_detalle_consultas_fijas.http` | `SQL_ECHO=true` | El detalle de una venta emite la misma cantidad de consultas con 2 y con 4 renglones | `evidencia/C-15_consultas_detalle_venta.txt` |
| C-16 | `C-16_busqueda_paginacion_patch.http` | | Búsqueda segura, paginación y PATCH parcial | `evidencia/C-16_corrida.txt` |
| RN-03 (extra) | `RN-03_rol_ya_vigente.http` | | Asignar un rol que el usuario ya tiene vigente → 409 «El usuario ya tiene ese rol vigente» | |
| RN-15 (extra) | `RN-15_caracter_nulo.http` | | El carácter U+0000 en cuerpos y en `?titulo=` → 422, nunca 500 | `evidencia/RN-15_corrida.txt` |

C-14 se corre con `psql -U <usuario> -d <base> -v ON_ERROR_STOP=0 -f test/solo_agregado.sql` (con
Docker: `docker exec -i <contenedor> psql -U <usuario> -d <base> < test/solo_agregado.sql`). Es
autocontenido y termina con `ROLLBACK`.

La carpeta `evidencia/` guarda la salida real de las comprobaciones, hecha contra una base
PostgreSQL 16 descartable recién migrada y sembrada: `migraciones_ida_y_vuelta.txt` (`alembic
upgrade head` → `downgrade base` → `upgrade head`) y un `*_corrida.txt` por cada archivo `.http`
indicado en la tabla, con la respuesta esperada y la respuesta real de cada petición.

## Decisiones de diseño

- **Dinero con `Decimal`** (`Numeric(10,2)` y `Numeric(12,2)`), nunca `float`; las fechas nuevas son
  `timestamptz`.
- **Unicidad y claves foráneas las garantiza la base**: no hay consultas previas de existencia; el
  `IntegrityError` se traduce a un 409 con mensaje propio.
- **Autorización contra la base**: el JWT sólo identifica; el rol se consulta en `asignacion_rol`
  (vigente) en cada petición, por eso revocar un rol surte efecto sin esperar a que venza el token.
  Se distingue siempre 401 (sin sesión) de 403 (sin permiso).
- **Contraseñas y secretos**: bcrypt fuera del bucle de eventos (`asyncio.to_thread`); la clave de
  firma y la contraseña de la base no tienen valor por defecto ni se versionan.
- **Stock**: un único punto de escritura (`LibroRepository.aplicar_movimiento`: `UPDATE` atómico
  condicional más su movimiento); `movimiento_stock` es de sólo agregado por un disparador de la
  base (migración 0004). `stock` es igual a la suma de los movimientos.
- **Sin N+1**: `joinedload` para relaciones a uno y `selectinload` para colecciones. El detalle de
  una venta emite una cantidad fija de consultas (C-15).
- **Ventas**: el cuerpo de alta lleva sólo `cliente_id` y los renglones (`libro_id`, `cantidad`). El
  precio de cada renglón se copia del libro y el total lo calcula el servidor. Las ventas no se
  modifican.
- **Asincronía**: todos los handlers son `async def`; el motor y la fábrica de sesiones viven en el
  lifespan. Al registrar una venta se agenda con `BackgroundTasks` un aviso de comprobante que corre
  después de enviar la respuesta.
