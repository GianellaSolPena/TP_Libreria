# Tasks

> Antes de aplicar: el grupo confirma los nombres de D-01 (Q-04) y la decisión D-05 del design.

## 1. Dependencias y configuración

- [x] 1.1 `parcial/requirements.txt`: agregar `pydantic-settings>=2.0`, `bcrypt>=4.0`, `PyJWT>=2.8`; `fastapi>=0.111` → `fastapi[standard]>=0.111`; quitar `uvicorn` y `python-dotenv` (D-10). Verificar: `pip install -r requirements.txt` termina sin errores en el venv de `parcial/`.
- [x] 1.2 Reescribir `parcial/app/core/config.py`: `Settings(BaseSettings)` con los campos de D-01, `SettingsConfigDict(env_file=".env", extra="ignore")`, `DATABASE_URL` como `@computed_field` con `URL.create(...).render_as_string(hide_password=False)` (D-03) y `get_settings()` con `@lru_cache` (D-02); sin `dotenv` ni lecturas al importar. Verificar: `python -c "from app.core.config import get_settings; print(get_settings().DATABASE_URL)"` con el `.env` completo imprime la URL `postgresql+asyncpg://...`.
- [x] 1.3 Reescribir `parcial/env.example` con todas las variables de D-01, `POSTGRES_PASSWORD=` y `JWT_SECRET_KEY=` vacías y un comentario de cómo generar la clave. Verificar: cada campo de `Settings` aparece en `env.example` y no hay secretos.

## 2. Motor, sesión y arranque

- [x] 2.1 `parcial/app/core/database.py`: `create_engine(settings)` con `echo=SQL_ECHO` y `pool_size=DB_POOL_SIZE` (D-04); quitar el import de `DATABASE_URL`/`SQL_ECHO` y `run_select_one`; `get_session` conserva commit/rollback con el comentario `TODO C-04` (D-05). Verificar: `python -c "import app.core.database"` no crea motor ni lee `.env`.
- [x] 2.2 `git mv parcial/app/main.py parcial/main.py`; el lifespan llama `get_settings()`, crea motor y fábrica, calcula `hash_ficticio` con `asyncio.to_thread` + `bcrypt.gensalt(rounds=BCRYPT_ROUNDS)` (D-06), guarda todo en `app.state` y hace `dispose()` al salir (D-08). Verificar: `uvicorn main:app` desde `parcial/` arranca y `GET /editoriales/` responde 200.
- [x] 2.3 `parcial/migrations/env.py`: URL desde `get_settings().DATABASE_URL`, `create_async_engine(url, poolclass=NullPool)` sin `set_main_option` (D-09); `alembic.ini` sin credenciales. Verificar: `alembic current` desde `parcial/` muestra la revisión `0002` sin error.

## 3. Salud

- [x] 3.1 Borrar `parcial/app/modules/health/service.py`; `router.py` hace `SELECT 1` con `asyncio.timeout(3)` y devuelve 503 `{"estado": "no listo"}` ante cualquier excepción (D-07). Verificar: el módulo `health` sólo tiene `__init__.py` y `router.py`.

## 4. Documentación

- [x] 4.1 `parcial/README.md`: arranque con `uvicorn main:app --reload`, `main.py` en la raíz, variables nuevas y cómo generar la clave. Verificar: los comandos del README corren tal cual.
- [x] 4.2 Registrar los nombres confirmados en `knowledge-base/08_arquitectura_propuesta.md` (§Variables de entorno) y marcar Q-04 como resuelta en `knowledge-base/10_preguntas_abiertas.md`. Verificar: ambos archivos usan los mismos nombres que `env.example`.

## 5. Verificación manual (CHANGES.md C-02)

- [x] 5.1 Con `.env` completo y la base levantada: `uvicorn main:app` arranca; `GET /health/live` → 200 y `GET /health/ready` → 200; `alembic upgrade head` funciona; `POST /editoriales/` crea y el `GET` posterior lo devuelve.
- [x] 5.2 Sin `JWT_SECRET_KEY` en el entorno/`.env`: el servidor no arranca y el error nombra `JWT_SECRET_KEY`.
- [x] 5.3 Sin `POSTGRES_PASSWORD`: el servidor no arranca y el error nombra `POSTGRES_PASSWORD`.
- [x] 5.4 Con la app arriba, detener PostgreSQL: `GET /health/live` → 200 y `GET /health/ready` → 503 (nunca 500, sin texto de la base); al levantar PostgreSQL de nuevo, `/health/ready` vuelve a 200 sin reiniciar.
- [x] 5.5 Con `SQL_ECHO=true` se ven las consultas en la consola; al detener el servidor (Ctrl+C) termina sin errores.

## Workflow follow-up

- Revisión del grupo antes de `/opsx:apply` (governance ALTO).
- Archivar con `/opsx:archive config-lifespan-health` y marcar C-02 `[x]` en `CHANGES.md`.
- C-04: quitar commit/rollback de `get_session` (D-05).
