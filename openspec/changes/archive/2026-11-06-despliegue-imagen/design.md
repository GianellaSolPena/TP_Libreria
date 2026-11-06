# Design

## Context

- Ver `proposal.md` (Why). Estado observado en `despliegue/` (copia de `e337710`, sin cambios desde C-01):
  - `app/main.py`: `app.main:app`, lifespan crea motor y fábrica de sesiones en `app.state`. Routers con barra final (`/libros/`, `/ventas/`, IN-05: no se toca).
  - `app/core/config.py`: `load_dotenv()` + `get_database_url()` que lanza `RuntimeError("Falta la variable de entorno DATABASE_URL...")` **al importar**; `SQL_ECHO` por defecto `false`. `migrations/env.py` importa `DATABASE_URL` de ahí, así que `alembic upgrade head` sin la variable ya termina con error (D-05 se cumple sin tocar código).
  - `app/modules/health/router.py` + `service.py`: `/health/ready` llama `check_database(request)` → `run_select_one(engine)` sin capturar nada: con la base caída la excepción sube y FastAPI responde **500** (IN-07). Además asyncpg tiene un timeout de conexión por defecto de 60 s, más largo que cualquier timeout razonable del `HEALTHCHECK`.
  - Datos iniciales: `test/seed.sql` (68 líneas: `BEGIN; TRUNCATE ... RESTART IDENTITY CASCADE; INSERT ...; SELECT setval(...); COMMIT;`), y el README indica `psql -U <usuario> -d libreria -f test/seed.sql` (IN-06: Alpine no trae `psql`). El archivo sólo tiene sentencias planas (sin variables de psql ni metacomandos) y es re-ejecutable (`TRUNCATE ... RESTART IDENTITY` dentro de `BEGIN/COMMIT`).
  - `requirements.txt`: `fastapi`, `sqlmodel`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `python-dotenv`, `uvicorn` (sin extras). Todas tienen wheels `musllinux` para CPython 3.12 x86_64, así que en Alpine se instalan sin compilador.
  - `env.example`: `DATABASE_URL=postgresql+asyncpg://usuario:password@localhost:5432/libreria`, `SQL_ECHO=false`.
- Restricciones: regla dura 9 (sólo Docker/VPS en `despliegue/`, la lógica no se toca salvo defectos propios anotados), sin Compose, sin pytest (DD-01), governance ALTO.
- Entorno: cliente Docker 29.8.0 instalado (contexto `desktop-linux`), pero el daemon de Docker Desktop **no estaba corriendo** al proponer; hay que iniciarlo antes de la verificación.

## Goals / Non-Goals

**Goals:**
- Una imagen reproducible, chica y sin secretos que pasa D-01, D-02, D-04..D-07 en local.
- Corregir IN-07 e IN-06 con el mínimo cambio posible y sin dependencias nuevas.
- Dejar `DEPLOY.md` listo para que C-11 sólo agregue URL pública, fecha/hora y la evidencia del VPS.

**Non-Goals:**
- No se cambia `app.main:app` por `main:app`, ni la barra final de las rutas (IN-05), ni `config.py` a pydantic-settings.
- No se agregan Compose, multi-stage ni compilador. El único paquete del sistema es `postgresql-client` (IN-06, D5).
- No se ejecutan los casos D-03 y D-08 (requieren el VPS: C-11, bloqueado por Q-02).
- No se toca `parcial/`.

## Decisions

### D1 — Dockerfile de una sola etapa sobre `python:3.12-alpine`
Orden de capas: `FROM python:3.12-alpine` → `ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1` → `WORKDIR /app` → `RUN apk add --no-cache postgresql-client` → `COPY requirements.txt .` → `RUN pip install --no-cache-dir -r requirements.txt` → `RUN addgroup -S app && adduser -S -G app app` → `COPY . .` → `USER app` → `EXPOSE 8000` → `HEALTHCHECK` → `CMD`.
- `apk add --no-cache postgresql-client` va como root (antes de `USER app`) y antes de `COPY requirements.txt`: cambia rara vez, así que su capa se reutiliza y no invalida la de `pip install`.
- El código queda propiedad de root y de sólo lectura para `app`: el proceso no necesita escribir en `/app` (sin `.pyc` por `PYTHONDONTWRITEBYTECODE`), así que no se usa `--chown` y un proceso comprometido no puede reescribir el código.
- Ninguna `ENV`/`ARG` con `DATABASE_URL` ni contraseñas (D-06: `env` no la muestra).
- *Alternativa*: multi-stage (skill `multi-stage-dockerfile`) con un builder que compile wheels. Se descarta: no hay nada que compilar; agregaría complejidad sin reducir tamaño.
- *Alternativa*: `python:3.12-slim`. Se descarta: base de ~180 MB, no cumple < 100 MB (D-01).

### D2 — Arranque con `sh -c "alembic upgrade head && exec uvicorn ..."`
`CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]`. `&&` hace que un fallo de Alembic (incluida la falta de `DATABASE_URL`, que revienta al importar `config.py`) termine el contenedor con su código de salida; `exec` reemplaza al shell para que uvicorn sea PID 1 y reciba `SIGTERM` de `docker stop`/`rm -f`. Alembic es idempotente: en D-04 no aplica nada nuevo.
- *Alternativa*: script `entrypoint.sh`. Se descarta: un archivo más sin ganancia; la consigna sugiere esta forma literal.

### D3 — `HEALTHCHECK` con `wget` de BusyBox a `127.0.0.1`
`HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8000/health/ready || exit 1`. BusyBox `wget` ya está en Alpine y devuelve distinto de cero ante 503. `127.0.0.1` y no `localhost` (en Alpine `localhost` puede resolver a `::1` y uvicorn escucha sólo IPv4). `start-period` cubre el tiempo de las migraciones.

### D4 — IN-07: el router traduce el error de la base a 503; el servicio acota la espera
- `service.check_database` envuelve `run_select_one` en `asyncio.wait_for(..., timeout=3)` (constante del módulo) para que una base que no contesta falle antes que el `--timeout=5s` del HEALTHCHECK.
- `router.ready` captura `(SQLAlchemyError, OSError, TimeoutError)` y responde `503` con cuerpo propio `{"estado": "no disponible"}` (`JSONResponse` o `HTTPException(503, detail=...)`), sin texto del driver; registra el detalle con el logger `app` (sólo servidor). La traducción de errores queda en el router, como en el resto del TP.
- Cubre: conexión rechazada (`OSError`/`ConnectionRefusedError`, que asyncpg puede propagar sin envolver), host inexistente (`socket.gaierror` ⊂ `OSError`), errores envueltos por SQLAlchemy (`DBAPIError`/`OperationalError`) y demora (`TimeoutError`, alias de `asyncio.TimeoutError` en 3.11+).
- *Alternativa*: un exception handler global para `SQLAlchemyError` → 503. Se descarta: cambiaría el comportamiento de todas las rutas del TP (regla 9).

### D5 — IN-06: instalar `postgresql-client` y cargar `test/seed.sql` con `psql` en el contenedor
Decisión del usuario: la imagen instala el cliente (`RUN apk add --no-cache postgresql-client`, como root, antes de `USER app`) y los datos iniciales se cargan con `psql` dentro del contenedor, sin tocar el TP congelado.
- `psql` acepta una URI `postgresql://...`, pero `DATABASE_URL` trae el esquema de SQLAlchemy `postgresql+asyncpg://`; basta quitar `+asyncpg` en el comando, sin variables `PG*` ni reescribir la URL a mano:
  `docker exec libreria sh -c 'psql -v ON_ERROR_STOP=1 "$(echo "$DATABASE_URL" | sed "s/+asyncpg//")" -f test/seed.sql'`
  Las comillas simples externas hacen que `$DATABASE_URL` se expanda dentro del contenedor (no en el shell del anfitrión; en PowerShell usar el mismo texto). `test/seed.sql` se lee de `/app/test/` (WORKDIR), incluido en la imagen porque `.dockerignore` no excluye `test/`.
- `-v ON_ERROR_STOP=1` hace que `psql` termine con código distinto de cero ante un error; sin él seguiría ejecutando y devolvería 0 aunque el `COMMIT` actúe como `ROLLBACK`. Es el único flag además de `-f`; `seed.sql` no usa variables de psql. Como el archivo corre dentro de `BEGIN ... COMMIT`, un error deja la base sin carga parcial. Es re-ejecutable (el `TRUNCATE ... RESTART IDENTITY` lo deja siempre en el mismo estado).
- Costo: ~10 MB más y un paquete de sistema. No importa: el límite de 100 MB de D-01 aplica sólo a la imagen base `python:3.12-alpine`, no a la imagen del proyecto.
- *Alternativa descartada*: `despliegue/seed.py` con asyncpg. Agrega código nuevo al TP congelado (regla 9) y una segunda vía de carga que mantener.
- *Alternativa descartada*: reescribir el seed como inserciones con SQLModel. Duplica datos y lógica.

### D6 — `.dockerignore`
Excluye `.env`, `.env.*` (pero no `env.example`), `.venv/`, `.git/`, `**/__pycache__/`, `**/*.pyc`, `evidencia/`, `Dockerfile`, `.dockerignore`. Se mantienen `test/` (contiene `seed.sql`, que `psql` lee dentro del contenedor) y `env.example` (no tiene secretos).

### D7 — `env.example` y `DEPLOY.md`
- `env.example` conserva la forma `DATABASE_URL=postgresql+asyncpg://usuario:password@<host>:5432/<base>` con un comentario: en el contenedor el host nunca es `localhost` (`host.docker.internal` + `--add-host=host.docker.internal:host-gateway` en Linux si la base está en el host, o la dirección que dé la cátedra); `SQL_ECHO=false`. `docker --env-file` ignora líneas que empiezan con `#`.
- `DEPLOY.md` nace en C-10 con: comandos `docker build -t libreria .` y `docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped --env-file <archivo> libreria` completos; comando de datos iniciales con `psql` (D5, `docker exec libreria sh -c '...'`); cómo se actualiza (rebuild, `docker rm -f`, mismo `docker run`; los datos viven en la base, no en el contenedor); "Cambios hechos al TP" (Dockerfile, .dockerignore, IN-07, IN-06, env.example, README). Secciones de URL pública, fecha/hora y dónde se construyó quedan marcadas "pendiente C-11".

### D8 — Verificación local
Manual, con la salida pegada en `despliegue/evidencia/` (un `.txt` por caso: `D-01_imagenes.txt`, `D-02_arranque.txt`, `D-04_recrear.txt`, `D-05_sin_database_url.txt`, `D-06_contenido_imagen.txt`, `D-07_usuario.txt`; formato abierto en Q-14, se elige texto de consola). La base de prueba es **una base nueva y separada** (p. ej. `libreria_despliegue`) en el PostgreSQL 16 local, accedida como `host.docker.internal` (Docker Desktop en Windows lo resuelve sin `--add-host`), o un contenedor `postgres:16-alpine` levantado con `docker run` en una red `docker network create` (sin Compose). Nunca la base de `parcial/`: tiene las migraciones 0003/0004 y otra `alembic_version`, y el seed del TP la truncaría.
IN-07 se verifica además sin Docker: `uvicorn app.main:app` con `DATABASE_URL` apuntando a un puerto cerrado → `GET /health/ready` 503 rápido; con la base arriba → 200; volver a apagar/levantar → se recupera.

## Risks / Trade-offs

- [Un paquete sin wheel `musllinux` obliga a compilar y el build falla en Alpine] → Verificar en el primer `docker build`; si pasa, fijar en `requirements.txt` la última versión con wheel (cambio anotado en DEPLOY.md) en lugar de agregar compilador.
- [Versiones sin fijar en `requirements.txt` (`>=`) hacen la imagen no reproducible] → Se acepta (el TP congelado no se toca más allá de lo necesario); `DEPLOY.md` registra `pip freeze` de la imagen construida como evidencia.
- [El quoting del `docker exec ... sh -c '...'` cambia según el shell del anfitrión (bash/PowerShell/cmd)] → README y DEPLOY.md documentan la forma con comillas simples externas y se verifica el comando tal cual en 3.2/5.2.
- [`psql` sin `ON_ERROR_STOP` devuelve 0 aunque la carga falle] → el comando lleva `-v ON_ERROR_STOP=1`.
- [`load_dotenv()` en la imagen podría leer un `.env` copiado por error] → `.dockerignore` excluye `.env*` y D-06 lo verifica.
- [La base caída al arrancar mata el contenedor (no reintenta)] → Es lo que pide la consigna (no tragar errores); `--restart unless-stopped` en el `docker run` del VPS lo reintenta.
- [Docker daemon no disponible en la máquina de desarrollo] → Iniciar Docker Desktop antes de la sección de verificación; si no es posible, la verificación queda pendiente y se reporta (no se marca hecha).

## Migration Plan

1. Implementar IN-07 y verificarlo sin Docker contra la base separada.
2. Escribir `Dockerfile` (con `postgresql-client`), `.dockerignore`, `env.example`; checkpoint con el usuario (governance ALTO) antes de construir.
3. Construir y correr D-01, D-02, D-04..D-07; guardar evidencia.
4. Escribir `DEPLOY.md` y actualizar README.
Rollback: borrar los archivos nuevos y restaurar los 4 modificados desde `e337710` (`despliegue/` no tiene estado persistente propio; `docker rm -f libreria && docker rmi libreria`).

## Open Questions

- Q-14 (Baja): formato de `evidencia/` (capturas vs texto). Se usa texto de consola; se puede sumar capturas sin cambiar el plan.
- Q-02 (Alta, no bloquea C-10): datos del VPS y base de la cátedra; sólo afectan el `docker run` real de C-11 (puerto, `--add-host`).
