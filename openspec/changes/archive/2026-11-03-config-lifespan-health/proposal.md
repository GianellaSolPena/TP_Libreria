# Proposal

## Why

El Ejercicio 1 del parcial (6 pts) exige configuración con `Settings` de pydantic-settings sin secretos por defecto, motor y fábrica de sesiones creados en el lifespan, hash ficticio calculado una vez y salud con `/health/ready` que responde 503. Hoy `parcial/` (copia del TP) lee sólo `DATABASE_URL` con `dotenv` al importar, `/health/ready` termina en 500 con la base caída (IN-07) y `main.py` vive en `app/` en lugar de la raíz (DD-08). Es la base de todos los changes siguientes.

## What Changes

- `app/core/config.py` pasa a una clase `Settings` (pydantic-settings) con `POSTGRES_*`, URL `postgresql+asyncpg` armada con `@computed_field`, `SQL_ECHO`, pool, clave de firma, duración del token, costo bcrypt y `Secure` de la cookie. Clave de firma y `POSTGRES_PASSWORD` **sin default**: si faltan, la app no arranca. **BREAKING**: deja de leerse `DATABASE_URL`.
- `app/core/database.py`: el motor usa `SQL_ECHO` y el pool de `Settings`; nada se crea al importar. `get_session` sigue tomando la fábrica de `app.state` (ver design D-05 sobre el commit).
- `app/main.py` se **mueve** a `parcial/main.py` (**BREAKING**: se arranca con `uvicorn main:app`); el lifespan carga `Settings`, crea motor y fábrica en `app.state`, calcula una vez el hash ficticio y hace `dispose()` al apagar.
- `health`: `/health/ready` responde 503 si `SELECT 1` falla; se elimina `health/service.py` (el módulo queda sólo con `router.py`).
- `migrations/env.py` toma la URL de `Settings` (sin credenciales en `alembic.ini`).
- `env.example` con todas las variables y ningún secreto; `requirements.txt` agrega pydantic-settings, bcrypt y PyJWT y quita python-dotenv.
- README de `parcial/`: comando de arranque y variables actualizados.

## Capabilities

### New Capabilities

- `configuracion-ciclo-vida`: lectura de la configuración desde el entorno sin secretos por defecto y ciclo de vida de los recursos (motor, fábrica de sesiones, hash ficticio) en el arranque y apagado.
- `salud`: rutas `GET /health/live` y `GET /health/ready` para distinguir proceso vivo de proceso listo.

### Modified Capabilities

(ninguna — `tp-snapshots` no cambia)

## Impact

- Código: `parcial/app/core/config.py`, `parcial/app/core/database.py`, `parcial/app/main.py` → `parcial/main.py`, `parcial/app/modules/health/{router.py,service.py}`, `parcial/migrations/env.py`, `parcial/env.example`, `parcial/requirements.txt`, `parcial/README.md`.
- Los routers de los módulos no cambian (siguen usando `get_session`).
- Cada integrante debe rehacer su `.env` local a partir de `env.example`.
- Fuera de alcance: `security.py`, JWT, cookie y semáforo bcrypt (C-05); UoW/repositorios (C-04); `despliegue/` no se toca.
