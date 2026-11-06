# Design

## Context

F-02 no escribe código de la aplicación: produce evidencia en `parcial/evidencia/` corriendo de verdad las migraciones y los `.http` sobre el código ya corregido por F-01. Hoy hay tres archivos de evidencia (`C-14_solo_agregado.txt` tomado sobre **PostgreSQL 17**, `C-14_captura_psql.png` que no coincide con él, y `C-15_consultas_detalle_venta.txt` recortado a mano).

Relevamiento del entorno (solo lectura, 2026-11-06):

| Elemento | Observado | Consecuencia |
|---|---|---|
| `python` / `python3` | alias de Microsoft Store (`WindowsApps\python.exe`), no es un intérprete | **nunca** usar `python` a secas; usar la ruta del venv |
| `py -0` | sólo Python 3.13 (64-bit); no hay 3.12 instalado | — |
| `parcial/.venv` | existe; `pyvenv.cfg` → Python **3.13.15**; tiene fastapi 0.162.0, SQLAlchemy 2.1.6, asyncpg 0.32.0, alembic 1.20.1, httpx; `alembic.exe` en `Scripts/` | intérprete de la corrida: `parcial/.venv/Scripts/python.exe` (cumple «3.12 o superior» del README) |
| Docker | 29.9.2, demonio arriba; imagen `postgres:16-alpine` ya descargada | contenedor descartable sin descarga |
| Contenedores existentes | `libreria-pg` (postgres:16, 5434, detenido) — base del usuario; `turnos-odontologia-*` arriba ocupando **127.0.0.1:5432** y **0.0.0.0:8000** | no tocar `libreria-pg`; no usar los puertos 5432 ni 8000 |
| `psql` en el host | no está | psql vía `docker exec -i <contenedor> psql` |
| `curl` | `/mingw64/bin/curl` (Git Bash) | disponible para comprobaciones sueltas |
| `parcial/.env` | existe (ignorado por git) con los datos de la base local del usuario; `Settings` lo lee con `env_file=".env"` | ver D2: riesgo de que `seed.py` (TRUNCATE) apunte a la base del usuario |
| `.http` | `@host = http://localhost:8000` fijo; sesiones con `{{loginX.response.headers.Set-Cookie}}`, ids con `{{ventaX.response.body.$.id}}`; psql comentado con `docker exec -i libreria-pg ...` | el ejecutor debe resolver esas referencias y sustituir `host` sin editar los archivos |
| Aviso del comprobante | `logger.info` en `app.modules.ventas.service` con 0,5 s de espera; `main.py` agrega un `StreamHandler` al logger `app` | aparece en la consola de uvicorn (stderr) después de la línea de acceso |

## Goals / Non-Goals

**Goals:**
- Evidencia reproducible y cruda del ciclo de migraciones y de los casos que escriben datos, con el comando exacto en cada encabezado.
- Cero riesgo para la base local del usuario y para los contenedores de otros proyectos.
- Detectar (no corregir) cualquier diferencia entre los `.http` y la realidad.

**Non-Goals:**
- Cambiar código, `.http`, `seed.py`, migraciones, `.env` o el README (F-03).
- Correr los casos de sólo lectura (C-01, C-03, C-04, C-06, C-09, RN-15) — se pueden sumar si el usuario lo pide; el ejecutor ya los soporta.
- Tocar `despliegue/`, el VPS o el zip (F-04).

## Decisions

### D1. Base: contenedor descartable `postgres:16-alpine`
`docker run -d --rm --name libreria-f02 -e POSTGRES_USER=libreria -e POSTGRES_DB=libreria -e POSTGRES_PASSWORD=<aleatoria> -p 127.0.0.1:55432:5432 postgres:16-alpine`. La contraseña se genera con `secrets.token_urlsafe(24)` y vive sólo en el scratchpad de la sesión (nunca en el repo ni en la evidencia). Nombre distinto de `libreria-pg` y puerto 55432 para no chocar con nada. `--rm` + `docker stop` al final lo descarta. PostgreSQL 16 = versión del stack (corrige que C-14 se tomó sobre 17).
*Alternativa descartada*: la base local / `libreria-pg` — `seed.py` hace `TRUNCATE` y el plan lo prohíbe.

### D2. Configuración por variables de proceso, sin tocar `.env`
pydantic-settings da prioridad a las variables de entorno del proceso sobre `.env`. Para cada comando (alembic, seed, uvicorn) se exportan **todas** las variables que `.env` podría aportar: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST=127.0.0.1`, `POSTGRES_PORT=55432`, `JWT_SECRET_KEY` (aleatoria de la sesión), `SQL_ECHO`, `DB_POOL_SIZE`, `ACCESS_TOKEN_EXPIRE_SECONDS`, `BCRYPT_ROUNDS`, `COOKIE_SECURE=false`. Antes del primer `seed.py`, un **CHECKPOINT** imprime `host`, `port` y `database` de `get_settings()` (sin la contraseña) y, vía la app, `SELECT inet_server_port(), version()` debe decir PostgreSQL 16 dentro del contenedor. Si no apunta a `127.0.0.1:55432`, se aborta.
*Alternativa*: copiar `parcial/` a una carpeta temporal sin `.env` — más seguro pero la evidencia diría otra ruta; se usa sólo si el CHECKPOINT falla.

### D3. Puertos: uvicorn en 8001
El 8000 lo usa otro proyecto. `uvicorn main:app --port 8001`; el ejecutor sustituye `@host` por `http://localhost:8001` al leer cada `.http` (sin modificar el archivo). La evidencia lo aclara en el encabezado.

### D4. Ejecutor de los `.http`: script Python fuera del repo
Un script en el scratchpad de la sesión, corrido con el intérprete del venv y `httpx` (ya instalado), que:
- parsea el `.http` tal cual (bloques `###`, variables `@x = ...`, `# @name`, `# @no-cookie-jar`, encabezados, cuerpo);
- resuelve `{{var}}`, `{{nombre.response.headers.Set-Cookie}}` (sólo la parte `access_token=...`) y `{{nombre.response.body.$.campo}}` (en F-01 el ejecutor no resolvía este último: C-06d y C-10f quedaron sin verificar; aquí es obligatorio);
- no guarda cookies entre peticiones (todas las peticiones de los `.http` llevan `# @no-cookie-jar` o `Cookie:` explícita);
- escribe por petición: título, `# Esperado:`, la petición enviada, la respuesta real (código, `Set-Cookie`/`Retry-After`/`Content-Type` y cuerpo) y deja la marca de coincidencia para revisarla contra el comentario.

El veredicto «coincide / no coincide» lo pone el agente leyendo comentario y respuesta (los comentarios son prosa, no aserciones automatizables); el script no lo inventa.
El script no se versiona (DD-01: sin andamiaje de pruebas; F-02 es «sin código»). La reproducibilidad para un lector humano sigue siendo REST Client en VS Code, como dice el README; la evidencia documenta la sustitución de `host`.
*Alternativas*: `httpyac` por `npx` (compatible con la sintaxis de REST Client, pero descarga paquetes de la red y su resolución de `@host` frente a `--var` no está verificada); REST Client a mano con copiar/pegar (no reproducible por el agente). Ver Open Questions.

### D5. Tokens en la evidencia
Las respuestas crudas incluyen `Set-Cookie: access_token=<JWT>`. Se reemplaza el valor del JWT por `<jwt>` (los atributos `HttpOnly; Max-Age=1800; Path=/; SameSite=lax` quedan), indicándolo en el encabezado. La clave de firma y la contraseña del contenedor no aparecen nunca; un `grep` final lo verifica.

### D6. Formato de los archivos
- Encabezado común: caso y título, «Cómo se obtuvo (fecha): …» con imagen (`postgres:16-alpine`, `SELECT version()`), Python del venv, comandos, `host` sustituido y nota de D5.
- `migraciones_ida_y_vuelta.txt`: para cada paso, `$ alembic <cmd>` + su stdout/stderr + código de salida + estado (`\dt`, `SELECT version_num FROM alembic_version`, `SELECT count(*) FROM pg_proc WHERE proname = 'movimiento_stock_solo_agregado'`). Se corre **antes** del seed sobre la base recién creada (vacía).
- `C-NN_corrida.txt` (C-02, C-05, C-07, C-08, C-10, C-11, C-12, C-13, C-16): bloques por petición + sección final «Comprobaciones en la base» con cada consulta psql comentada del `.http` ejecutada vía `docker exec -i libreria-f02 psql -U libreria -d libreria -c "..."` y su salida.
- C-10: sección «Consola de uvicorn» con el fragmento desde `POST /ventas HTTP/1.1" 201` hasta la línea del comprobante (uvicorn corre con stdout/stderr redirigidos a un log en el scratchpad).
- `C-15_consultas_detalle_venta.txt`: se reemplaza. Encabezado + captura cruda del log de uvicorn con `SQL_ECHO=true` desde el login hasta el segundo `GET /ventas/... 200`, sin cortes + anotación final con el conteo de SELECT por petición (esperado 4 y 4).
- Codificación UTF-8, finales de línea LF (como los existentes; `.gitattributes` deja `parcial/**` sin conversión).

### D7. C-14
Con el contenedor sembrado, se regenera `C-14_solo_agregado.txt` copiando el script al contenedor (`docker exec libreria-f02 mkdir -p /test` + `docker cp test/solo_agregado.sql libreria-f02:/test/`) y corriendo `docker exec -w / libreria-f02 psql -U libreria -d libreria -v ON_ERROR_STOP=0 -a -f test/solo_agregado.sql 2>&1` (con `-f` y esa ruta relativa los errores salen como `psql:test/solo_agregado.sql:NN:`, igual que en el archivo actual; con `<` saldrían como `psql:<stdin>:NN:`), conservando el formato del archivo actual y declarando PostgreSQL 16. La imagen la rehace el usuario (paso opcional): el agente deja el contenedor sembrado y le pasa el comando; si el usuario no la rehace, se deja constancia y el png queda como está.

### D8. Diferencias encontradas
Si una respuesta no coincide con su comentario: no se arregla código ni `.http` en F-02. Se anota en la evidencia como «NO coincide», se detiene la tarea y se reporta al usuario para decidir (otro change F-xx o corregir el comentario en F-03).

## Risks / Trade-offs

- **`seed.py` contra la base equivocada** → D2 (todas las variables exportadas + CHECKPOINT de destino antes del primer seed).
- **C-05 depende del tiempo** (5 fallos en 60 s, 429 con `Retry-After`) → el ejecutor corre el archivo sin pausas; si el reloj interfiere se repite tras `seed.py`.
- **C-10 aviso a 0,5 s** → esperar ≥ 1 s antes de cortar el log.
- **C-07 usa vencimientos con fecha** → usa fechas fijas (2020 pasada, 2099 futura): no depende del día de la corrida.
- **Ejecutor propio con bugs de parseo** → antes de los casos se prueba sobre `C-01` (sólo lectura) y se compara con REST Client/curl; cualquier petición mal parseada invalida la corrida de ese archivo.
- **Contenedor olvidado** → `--rm` y tarea final `docker ps -a --filter name=libreria-f02` vacío.
- **Trade-off**: el ejecutor no queda en el repo; un tercero reproduce con REST Client (manual) en vez de con un comando.

## Migration Plan

No aplica (sin cambios de esquema ni de código). Rollback: `git checkout -- parcial/evidencia/` y borrar los archivos nuevos.

## Open Questions

- **Q-A (ejecutor)**: ¿script Python en el scratchpad (D4, recomendado) o `httpyac` vía `npx`? Si el usuario quiere que cualquiera pueda reproducir con un comando, habría que versionar el ejecutor, lo que choca con DD-01 / «sin código»: se registraría en `knowledge-base/10_preguntas_abiertas.md`.
- **Q-B (C-14)**: ¿se regenera `C-14_solo_agregado.txt` sobre PostgreSQL 16 (D7) y el usuario rehace el png, o se deja el txt de PostgreSQL 17 y sólo se rehace el png?
- **Q-C (alcance)**: ¿se suman las corridas de los casos de sólo lectura (C-01, C-03, C-04, C-06, C-09, RN-15)? Costo marginal bajo; no lo pide el plan.
- **Q-D (puertos)**: alternativa a D3: que el usuario detenga temporalmente `turnos-odontologia` para correr en 8000 sin sustituir `host`.
