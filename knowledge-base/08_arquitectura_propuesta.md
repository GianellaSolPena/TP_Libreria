# Arquitectura Propuesta

## Patrones aplicados (exigidos por el PDF)
| Patrón | Dónde | Por qué |
|---|---|---|
| Capas Router -> Service -> UoW -> Repository -> Model | todos los módulos | cada capa sabe lo suyo y nada más |
| Repository genérico (`BaseRepository[T]`, `SoftDeleteRepository[T]`) | `app/core/repository.py` | reutilizar CRUD; el soft delete como jerarquía aparte (métodos que la base no tiene) |
| Unit of Work (gestor de contexto async) | `app/core/unit_of_work.py` + uno por módulo | una transacción por operación de negocio; el UoW **no cierra la sesión** porque no la creó |
| Dependency Injection | `get_session`, `get_usuario_actual`, `requiere_rol`, UoW por dependencia | misma sesión en UoW y dependencias de auth (una conexión por petición) |
| Lifespan | `main.py` | motor/fábrica en `app.state`, hash ficticio, `dispose()` |
| Dos grupos de rutas | `main.py` | el control de cambio obligatorio se monta una vez (FastAPI suma dependencias, no las resta) |
| Punto único de escritura de stock | `libros` (repositorio/UoW) | alta, reposición y venta lo usan; garantiza `stock == SUM(movimientos)` |
| Sesión propia para `intento_acceso` | login | única escritura fuera de la transacción de la petición |
| Traducción de errores (`IntegrityError` -> 409, errores de dominio -> 401/403/404/409/422) | **router** (p. 9: "traducen errores"), con un helper/manejador común | 409 con mensaje propio, nunca texto de la base |

## Responsabilidades por capa (p. 8-9, Ej. 6, requisitos no funcionales)
| Capa | Hace | No hace |
|---|---|---|
| `router.py` | Declara rutas `async def` y contratos; **construye el UoW con una dependencia** (`Depends`) y se lo pasa al servicio **sin abrirlo**; traduce errores a HTTP; agenda `BackgroundTasks` | No abre el UoW, no consulta la base, no tiene reglas de negocio |
| `service.py` | Reglas de negocio; **recibe el UoW** y lo abre con `async with`; hashea con bcrypt **antes** de abrir el bloque; lanza errores del dominio | **Nunca recibe ni usa la sesión**, nunca construye su UoW, nunca hace `commit()`/`rollback()` |
| `unit_of_work.py` (módulo) | Compone los repositorios que necesitan las operaciones del módulo, **todos con la misma sesión** | No cierra la sesión (no la creó) |
| `app/core/unit_of_work.py` | Gestor de contexto async: **commit al salir**, **rollback si sale con excepción** | No cierra la sesión |
| `repository.py` | Acceso a datos; métodos nombrados por lo que traen; precarga declarada **dentro del método**; `add`/`update` hacen `flush()` | **Nunca `commit()`** |
| `models.py` | Tablas, restricciones, relaciones en los dos extremos | Sin lógica |
| `get_session` (core) | Toma la fábrica de `app.state`, entrega una sesión por petición y la **cierra** | No confirma ni revierte |
| `dependencies.py` | `get_usuario_actual`, roles vigentes, control del cambio obligatorio, `requiere_rol`; usan **la misma sesión** que el UoW de la petición | No leen roles del token para decidir |

Única excepción documentada: el registro de `intento_acceso` usa una sesión y transacción propias (Ej. 7), también encapsuladas en un repositorio/UoW propio.

## Estructura de directorios obligatoria (proyecto `parcial/`)
```
main.py                      aplicación, lifespan y los DOS grupos de rutas (el PDF lo lista sin prefijo app/, junto a seed.py: raíz del proyecto; hoy vive en app/main.py: ver Q-03)
seed.py                      deja la base en el estado inicial conocido
app/
├── core/
│   ├── config.py            Settings (pydantic-settings)
│   ├── database.py          crear motor y fábrica de sesiones (las llama el lifespan) + get_session
│   ├── security.py          hash bcrypt fuera del bucle (+semáforo); emisión/verificación del token
│   ├── dependencies.py      usuario actual, roles vigentes, control de cambio obligatorio, requiere_rol
│   ├── repository.py        BaseRepository[T], SoftDeleteRepository[T]
│   ├── paginacion.py        envoltorio de listados y cálculo de páginas
│   └── unit_of_work.py      UnitOfWork base
└── modules/
    ├── health/              (sólo router.py)
    ├── usuarios/            Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad
    ├── editoriales/  generos/  autores/
    ├── libros/              Libro, LibroAutor, MovimientoStock
    ├── clientes/            Cliente, PerfilCliente
    └── ventas/              Venta, RenglonVenta
        cada módulo: models.py · schemas.py · repository.py · unit_of_work.py · service.py · router.py
migrations/                  Alembic (plantilla asincrónica) + versions/
test/                        .http (casos C) + solo_agregado.sql (C-14)
```
Proyecto `despliegue/`: TP Cap 1-4 tal como se entregó + `Dockerfile`, `.dockerignore`, `env.example`, `DEPLOY.md`, `evidencia/`.

## Seguridad
- **Autenticación**: bcrypt (costo en config) fuera del event loop (`to_thread` + semáforo); JWT (PyJWT) con `sub`, `exp`, roles; cookie `access_token` HttpOnly, SameSite=Lax, Max-Age = duración, Secure configurable.
- **Autorización**: roles vigentes leídos de `asignacion_rol` en cada petición; 401 vs 403 siempre distintos.
- **Validación de entrada**: `extra="forbid"`, límites (72 bytes en campos bcrypt, `size` 1..100), `exclude_unset` en PATCH.
- **Secretos**: sin valor por defecto para la clave de firma ni la contraseña de la base (si faltan, la app no arranca); `.env` fuera del repo/zip/imagen; `env.example` sin secretos; ni `alembic.ini` lleva credenciales (`env.py` toma la URL de Settings).
- **Errores**: nunca texto de la base ni trazas; 429 con `Retry-After`; detalle completo en `05_reglas_de_negocio.md` §Manejo de errores.
- **Anti-enumeración**: mismo mensaje y mismo tiempo exista o no el correo.
- **Contenedor**: usuario sin privilegios (`USER`), sin secretos en capas, `.dockerignore` excluye `.env`, `.venv`, `.git`, `__pycache__`.

## Variables de entorno
| Variable | Descripción | Ejemplo | Sensible |
|---|---|---|---|
| `POSTGRES_USER` | usuario de la base (proyecto `parcial/`) | `libreria` | N |
| `POSTGRES_PASSWORD` | contraseña de la base; sin default | — | **Y** |
| `POSTGRES_DB` | nombre de la base | `libreria` | N |
| `POSTGRES_HOST` | host | `localhost` | N |
| `POSTGRES_PORT` | puerto | `5432` | N |
| `JWT_SECRET_KEY` | clave de firma del JWT; secreto principal, sin default | generar con `secrets.token_urlsafe(32)` | **Y** |
| `ACCESS_TOKEN_EXPIRE_SECONDS` | duración del token en segundos (también `Max-Age` de la cookie) | `1800` | N |
| `BCRYPT_ROUNDS` | costo de bcrypt | `12` | N |
| `COOKIE_SECURE` | `true` detrás de HTTPS | `false` | N |
| `DB_POOL_SIZE` | tamaño del pool de conexiones | `5` | N |
| `SQL_ECHO` | `true` para ver las consultas (casos C-15) | `false` | N |
| `DATABASE_URL` | **sólo en `despliegue/`** (TP Cap 1-4): `postgresql+asyncpg://...` | — | **Y** |

La dirección de la base se arma en `Settings` con `@computed_field` a partir de las variables `POSTGRES_*` con driver `postgresql+asyncpg`. `env.example` incluye todas las variables y ningún secreto.

## Pruebas
Sólo las que pide el PDF: `.http` en `test/` (casos C con respuesta esperada en comentario) y `test/solo_agregado.sql`; sin pytest. Ver `09_decisiones_y_supuestos.md` DD-01.
