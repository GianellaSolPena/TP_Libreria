# Proposal

## Why

El Ej. 9 del parcial pide empaquetar el TP Cap 1-4 (la copia congelada `despliegue/`) en una imagen Docker que se pueda correr en un servidor limpio, y verificarla con los casos D-01, D-02 y D-04..D-07. Hoy `despliegue/` no tiene `Dockerfile` ni `.dockerignore`, y además arrastra dos defectos propios del TP que impiden que la imagen funcione como pide la consigna: `GET /health/ready` responde 500 (no 503) con la base caída (IN-07), así que el `HEALTHCHECK` no distingue bien; y los datos iniciales se cargan con `psql`, que la imagen Alpine no trae (IN-06), así que ningún `docker exec libreria ...` del Ej. 10 puede cargarlos. Es la rama de despliegue, paralela al parcial, y sólo depende de C-01.

## What Changes

- Agregar `despliegue/Dockerfile` de una sola etapa: `FROM python:3.12-alpine`; `requirements.txt` copiado e instalado **antes** del código con `pip install --no-cache-dir`; usuario sin privilegios + `USER`; `HEALTHCHECK` con `wget` a `http://127.0.0.1:8000/health/ready`; `CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]` (si Alembic falla, el contenedor termina con error). Sin URL ni contraseñas de base en el Dockerfile; sin Docker Compose.
- Agregar `despliegue/.dockerignore` que excluye `.env` (y variantes), `.venv`, `.git`, `__pycache__`, `*.pyc` y `evidencia/`.
- Ajustar `despliegue/env.example`: misma forma de `DATABASE_URL` (`postgresql+asyncpg://usuario:password@<host>:5432/<base>`), sin valores reales, con nota de que dentro del contenedor el host nunca es `localhost` (p. ej. `host.docker.internal`), y `SQL_ECHO=false`.
- Corregir IN-07 (defecto propio del TP): `GET /health/ready` responde **503** con cuerpo propio cuando la base no contesta (error de conexión o demora mayor a unos segundos), nunca 500 ni texto del driver.
- Corregir IN-06 (defecto propio del TP): instalar el cliente de PostgreSQL en la imagen (`apk add --no-cache postgresql-client`) y cargar `test/seed.sql` con `psql` dentro del contenedor, sin agregar código al TP congelado. `psql` acepta una URI `postgresql://`, así que al `DATABASE_URL` se le quita `+asyncpg` en el propio comando: `docker exec libreria sh -c 'psql -v ON_ERROR_STOP=1 "$(echo "$DATABASE_URL" | sed "s/+asyncpg//")" -f test/seed.sql'`.
- Actualizar `despliegue/README.md` (paso de datos iniciales y una sección breve de Docker) y abrir `despliegue/DEPLOY.md` con los comandos `docker build`/`docker run` completos y la lista de cambios hechos al TP (IN-06, IN-07, Dockerfile, .dockerignore); C-11 completa URL pública, fecha y hora.
- Guardar en `despliegue/evidencia/` la salida de los casos D-01, D-02, D-04, D-05, D-06 y D-07 ejecutados en local.
- Ninguna otra lógica de `despliegue/` cambia; `parcial/` no se toca; `app.main:app` se conserva.

## Capabilities

### New Capabilities
- `imagen-despliegue`: imagen Docker del TP Cap 1-4 (`despliegue/`): construcción desde `python:3.12-alpine`, arranque con migraciones encadenadas, healthcheck, ausencia de secretos, usuario sin privilegios, fallo sin `DATABASE_URL`, carga de datos iniciales dentro del contenedor y salud 503 del TP corregida.

### Modified Capabilities
- `tp-snapshots`: la fidelidad de `despliegue/` a `e337710` pasa de "idéntica" a "idéntica salvo los cambios de despliegue enumerados" (Dockerfile, .dockerignore, DEPLOY.md, evidencia/, y los ajustes IN-06/IN-07 en `health`, `README.md` y `env.example`); `parcial/` ya evoluciona por sus propios changes desde C-02.

## Impact

- **Archivos** (sólo `despliegue/`): nuevos `Dockerfile`, `.dockerignore`, `DEPLOY.md`, `evidencia/*`; modificados `app/modules/health/router.py`, `app/modules/health/service.py`, `env.example`, `README.md`.
- **Dependencias**: ninguna de Python nueva; un paquete `apk` en la imagen: `postgresql-client` (~10 MB extra; el límite de 100 MB de D-01 aplica sólo a la imagen base `python:3.12-alpine`, no a la imagen final).
- **Sistemas**: requiere Docker Engine para verificar; en esta máquina el cliente Docker 29.8 está instalado pero el daemon (Docker Desktop) no estaba corriendo al proponer. Las pruebas locales necesitan una base PostgreSQL **separada** de la de `parcial/` (esquemas y `alembic_version` distintos).
- **Governance**: ALTO (secretos en la imagen): proponer y revisar antes de escribir; checkpoint con el usuario antes de construir/publicar.
- **Desbloquea**: C-11 `despliegue-vps` (bloqueado además por Q-02) y C-12.
