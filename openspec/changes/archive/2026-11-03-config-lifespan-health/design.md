# Design

## Context

`parcial/` es la copia del TP Cap 1-4. Ya tiene parte del Ej. 1: `create_engine()`/`create_session_factory()` en `app/core/database.py` llamadas desde el lifespan, `expire_on_commit=False` y `dispose()`. Lo que falta o está mal:

- `config.py` usa `dotenv` + `os.getenv("DATABASE_URL")` y falla **al importar**; no hay pool, clave de firma ni demás valores.
- `/health/ready` delega en `health/service.py` y no captura la excepción → 500 con la base caída (IN-07).
- `main.py` está en `app/main.py`; DD-08 lo lleva a `parcial/main.py`.
- `migrations/env.py` importa `DATABASE_URL` y lo inyecta con `config.set_main_option`.
- `get_session` hace `commit()`/`rollback()`, y los servicios de autores, clientes, editoriales, géneros y libros sólo hacen `flush()`: dependen de ese commit.

## Goals / Non-Goals

**Goals:** cumplir el Ej. 1 del PDF con el menor cambio sobre el código existente; dejar en `Settings` todos los valores que C-05 va a necesitar (clave, duración, costo bcrypt, cookie `Secure`).

**Non-Goals:** `security.py`, JWT, cookie y semáforo de bcrypt (C-05); UoW y repositorios (C-04); tocar `despliegue/`; pytest o scripts de verificación.

## Decisions

### D-01 — Nombres de variables (Q-04) ⚠️ A CONFIRMAR POR EL GRUPO

Los campos de `Settings` se llaman igual que la variable de entorno (mayúsculas), así el código, `env.example` y la KB usan un solo nombre.

| Variable | Tipo | Default | Uso |
|---|---|---|---|
| `POSTGRES_USER` | str | **sin default** | fijado por el PDF |
| `POSTGRES_PASSWORD` | str | **sin default** (secreto) | fijado por el PDF |
| `POSTGRES_DB` | str | **sin default** | fijado por el PDF |
| `POSTGRES_HOST` | str | `localhost` | fijado por el PDF |
| `POSTGRES_PORT` | int | `5432` | fijado por el PDF |
| `SQL_ECHO` | bool | `false` | fijado por el PDF |
| `DB_POOL_SIZE` | int | `5` | **propuesto** — tamaño del pool |
| `JWT_SECRET_KEY` | str | **sin default** (secreto) | **propuesto** — clave de firma |
| `ACCESS_TOKEN_EXPIRE_SECONDS` | int | `1800` | **propuesto** — duración del token; en segundos porque el login devuelve `expira_en_segundos` y la cookie usa `Max-Age` (segundos) |
| `BCRYPT_ROUNDS` | int | `12` | **propuesto** — costo de bcrypt (nombre del parámetro `rounds` de `bcrypt.gensalt`) |
| `COOKIE_SECURE` | bool | `false` | **propuesto** — `false` en local (HTTP); `true` detrás de HTTPS |

`POSTGRES_USER` y `POSTGRES_DB` quedan sin default porque no hay un valor razonable universal (no son secretos). No se agregan `JWT_ALGORITHM` (HS256 fijo en código, C-05), `max_overflow` ni la cantidad del semáforo de bcrypt: el PDF no los pide en la config; si C-05 los necesita, los suma.

*Alternativas*: `SECRET_KEY` (más genérico, ambiguo junto a la contraseña), `ACCESS_TOKEN_EXPIRE_MINUTES` (convención de los tutoriales de FastAPI, pero obliga a convertir a segundos para `Max-Age` y la respuesta).

### D-02 — `Settings` cargado en el lifespan, no al importar

`config.py` define `Settings(BaseSettings)` con `model_config = SettingsConfigDict(env_file=".env", extra="ignore")` y una función `get_settings()` con `@lru_cache`. El lifespan llama `get_settings()` primero: si falta un secreto, pydantic lanza `ValidationError` nombrando el campo y uvicorn aborta el arranque ("Application startup failed"). `extra="ignore"` evita que un `.env` viejo con `DATABASE_URL` rompa el arranque (pydantic-settings rechaza claves extra del `.env` por defecto).

*Alternativa*: instancia global `settings = Settings()` al importar → falla al importar, antes del lifespan, con traza más confusa y contra el espíritu de la sección 1.9.

### D-03 — URL con `@computed_field` usando `sqlalchemy.URL.create`

`DATABASE_URL` es un `@computed_field` que arma `URL.create("postgresql+asyncpg", username, password, host, port, database)` y lo devuelve como texto con `render_as_string(hide_password=False)`. Así una contraseña con `@`, `:` o `/` queda bien escapada. *Alternativa*: f-string → se rompe con caracteres especiales.

### D-04 — Motor con pool de la config, funciones que reciben `Settings`

`create_engine(settings)` → `create_async_engine(settings.DATABASE_URL, echo=settings.SQL_ECHO, pool_size=settings.DB_POOL_SIZE)`. `create_session_factory(engine)` no cambia. Ningún módulo importa valores de config a nivel módulo; el lifespan guarda en `app.state`: `settings`, `engine`, `session_factory` y `hash_ficticio`.

### D-05 — `get_session` conserva el commit hasta C-04 ⚠️ A CONFIRMAR

El PDF pide que `get_session` entregue una sesión por petición y la cierre; el commit lo hace el UoW (C-04). Pero hoy cinco servicios sólo hacen `flush()`: quitar el commit ahora dejaría las altas y modificaciones sin guardar hasta C-04. Se conserva el commit/rollback como **puente temporal** con un comentario `# TODO C-04: el UoW confirma; quitar commit/rollback`. C-04 lo quita al migrar los servicios.

*Alternativa*: quitarlo ya (más fiel al PDF) aceptando que las escrituras queden rotas entre C-02 y C-04.

### D-06 — Hash ficticio en el lifespan con bcrypt directo

El lifespan calcula `await asyncio.to_thread(bcrypt.hashpw, <bytes fijos>, bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS))` y lo guarda en `app.state.hash_ficticio`. C-05 lo reemplaza por la función de `security.py` (con semáforo) sin cambiar dónde vive. Así el Ej. 1 queda completo en este change y el costo del hash ficticio coincide con el real.

### D-07 — `health` sólo `router.py`, 503 con cuerpo propio

Se borra `health/service.py` y `run_select_one` de `database.py`. `ready` hace `async with request.app.state.engine.connect()` + `SELECT 1` dentro de `asyncio.timeout(3)` y un `try/except Exception`; si falla, devuelve `JSONResponse(status_code=503, content={"estado": "no listo"})`. Se captura `Exception` porque con la base caída pueden salir `OSError`, `SQLAlchemyError`, errores de asyncpg o `TimeoutError`. El timeout evita que la ruta quede colgada si el host no contesta. `live` no cambia (`{"estado": "vivo"}`).

### D-08 — `main.py` a la raíz de `parcial/`

`git mv parcial/app/main.py parcial/main.py` (conserva historial); el logging del logger `app` se mueve tal cual. Se arranca desde `parcial/` con `uvicorn main:app`. Los imports `from app.modules...` siguen funcionando porque `parcial/` es el directorio de trabajo. Ojo: dentro de `main.py` la variable `app = FastAPI()` tapa al paquete `app`; todos los imports van arriba, antes de crearla.

### D-09 — Alembic sin `set_main_option`

`env.py` usa `get_settings().DATABASE_URL` y crea el motor con `create_async_engine(url, poolclass=NullPool)` en lugar de `async_engine_from_config` + `set_main_option` (configparser interpreta `%`, que aparece en contraseñas escapadas). El modo offline usa la misma URL. `alembic.ini` mantiene `sqlalchemy.url =` vacío.

### D-10 — Dependencias

`requirements.txt`: agrega `pydantic-settings>=2.0`, `bcrypt>=4.0`, `PyJWT>=2.8`; cambia `fastapi>=0.111` + `uvicorn` por `fastapi[standard]>=0.111` (lo que dice la tabla del PDF); quita `python-dotenv` (pydantic-settings lee `.env` solo).

## Risks / Trade-offs

- [El `.env` local de cada integrante deja de servir] → `env.example` y README actualizados; `extra="ignore"` evita el error por la clave vieja, y la falta de las nuevas sale con el nombre de la variable.
- [Commit transitorio en `get_session` (D-05) no cumple todavía la letra del PDF] → queda marcado con TODO y es tarea explícita de C-04.
- [Cambian los nombres si el grupo no acepta D-01] → cambiar antes de apply; después de apply implica tocar `config.py`, `env.example` y README.
- [`uvicorn app.main:app` deja de funcionar] → README actualizado; `despliegue/` no se ve afectado (es otra copia).

## Migration Plan

1. Copiar `env.example` a `.env` y completar (generar la clave con `python -c "import secrets; print(secrets.token_urlsafe(32))"`).
2. `pip install -r requirements.txt` en el venv de `parcial/`.
3. Arrancar con `uvicorn main:app --reload` desde `parcial/`. Rollback: `git revert` del commit del change.
