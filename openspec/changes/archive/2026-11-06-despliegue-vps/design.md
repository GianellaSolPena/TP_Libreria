# Design

## Context

Motivación y alcance: ver `proposal.md`. Requisitos: ver `specs/despliegue-vps/spec.md`.

Estado relevado con SSH **de sólo lectura** al proponer (2026-11-06):

| Aspecto | Hallazgo |
|---|---|
| Servidor | `srv1915306`, Ubuntu 24.04.4, Docker 29.7.1, **swarm activo** (manager), 1 CPU, 3,9 GB RAM (~2,9 GB disponibles, sin swap), disco 48 GB con 41 GB libres; `git` instalado; `/root` vacío |
| Easypanel | servicios `easypanel`, `easypanel-traefik` (publica 80/443), panel en `:3000`; proyectos `grupo1-chicas` (calculadoras en 0/0 réplicas + `db`), `grupo2-elias`, `grupo3-mateo` |
| Base del grupo | servicio swarm `grupo1-chicas_db`, imagen `postgres:17` (PG 17.11), **sin puertos publicados en el host**; datos en bind `/etc/easypanel/projects/grupo1-chicas/db/data` |
| Red de la base | overlay `easypanel-grupo1-chicas` (10.0.1.0/24), **`Attachable=true`**; la base tiene los alias `grupo1-chicas-db` y `db` en esa red (y `grupo1-chicas-db` en la overlay `easypanel`, también attachable) |
| Rol y bases | `POSTGRES_USER=calculadora`, `POSTGRES_DB=calculadora`; `calculadora` es **superusuario con CREATEDB**; bases existentes: `postgres`, `calculadora`, `template0/1`; **no existe `libreria`**; `calculadora` tiene 1 tabla en `public` y ninguna `alembic_version`. El socket local del contenedor de la base es `trust` (desde `docker exec` no pide contraseña); por red, `scram-sha-256` |
| Puertos | en escucha: 22, 80, 443, 3000, 2377, 7946 (+ locales 53, 65529); **8101 libre** |
| Firewall | `ufw` activo: deny entrante por defecto, permite sólo 22, 80, 443 (v4 y v6). `iptables`: `FORWARD` pasa primero por `DOCKER-USER` (vacía) y `DOCKER-FORWARD`, **antes** de las cadenas de `ufw`; el panel `:3000` responde 200 desde afuera sin regla de `ufw` → los puertos publicados por Docker no los filtra `ufw` |
| Nombres | no hay contenedor ni imagen `libreria`; no está `python:3.12-alpine` (el build la descarga: "servidor limpio") |
| Repo | `origin` en GitHub; `despliegue/Dockerfile`, `.dockerignore`, `DEPLOY.md`, `evidencia/` y los cambios IN-06/IN-07 están **sin commitear** |
| TP | `migrations/env.py` hace `config.set_main_option("sqlalchemy.url", DATABASE_URL)` (ConfigParser: un `%` en la URL rompe Alembic); `app/core/config.py` exige `DATABASE_URL` |

## Goals / Non-Goals

**Goals:**
- TP Cap 1-4 accesible en `http://187.127.58.90:8101`, con la imagen construida en el servidor y su base propia.
- Cada paso que modifica el servidor, explícito, reversible y aprobado por el usuario antes de ejecutarse.
- Evidencia D-01..D-08 desde el VPS y `DEPLOY.md` sin pendientes.

**Non-Goals:**
- Registrar el TP como servicio/proyecto de Easypanel, dominio, HTTPS o traefik (la consigna pide `docker run`).
- Cambiar código de `despliegue/` o de `parcial/` (si algo falla por un defecto del TP, se para y se consulta).
- Copias de seguridad, monitoreo o rotación de logs del servidor.
- Tocar la base `calculadora`, el servicio `db` o cualquier recurso ajeno.

## Decisions

### D1 — Construir la imagen en el servidor, llevando los archivos con `tar` sobre SSH
`tar -C despliegue --exclude=.env --exclude='.env.*' --exclude=.venv --exclude=evidencia --exclude=__pycache__ --exclude='*.pyc' -cf - . | ssh … 'mkdir -p /root/libreria/despliegue && tar -C /root/libreria/despliegue -xf -'` y luego `docker build -t libreria .` en `/root/libreria/despliegue`.
- **Por qué**: la consigna admite ambas opciones pero D-02 dice "Servidor limpio: `docker build` y `docker run`", y D-01 pide `docker images` con la base y la del proyecto en el servidor; construir allí cumple ambos literalmente. Las dependencias bajan como wheels (sin compilar), 1 CPU alcanza.
- **Alternativas**: `git clone` en el servidor → descartado: los archivos de C-10 no están commiteados y la regla 11 prohíbe commit/push sin pedido; además exige credenciales de GitHub en el VPS si el repo es privado. `docker save | ssh docker load` → válido, pero la imagen local es `linux/amd64` construida en Windows/Docker Desktop y no deja `python:3.12-alpine` en el servidor para D-01; queda como plan B si el build en el servidor falla por red.
- `tar` respeta los finales de línea tal como están en disco (`.gitattributes -text` en `despliegue/`), igual que el build local de C-10.

### D2 — Base nueva `libreria` en el PostgreSQL del grupo
`docker exec "$(docker ps -q -f name=grupo1-chicas_db.1)" psql -U calculadora -d postgres` con `CREATE ROLE libreria LOGIN PASSWORD <aleatoria generada en el servidor>` y `CREATE DATABASE libreria OWNER libreria` (decisión del usuario, por prolijidad: rol propio en vez de reutilizar `calculadora`; la contraseña se genera del lado del servidor y nunca se muestra).
- **Por qué**: aísla las tablas y `alembic_version` del TP de la base `calculadora` (que ya tiene su tabla); `test/seed.sql` hace `TRUNCATE … CASCADE` y sólo debe tocar tablas del TP. Se comprobó (lectura) que `calculadora` tiene CREATEDB y es superusuario, así que **no hace falta pedir nada a los docentes**. Por `docker exec` se usa el socket local `trust`: no se necesita ni se muestra la contraseña de `calculadora`. El rol `libreria` es dueño sólo de la base `libreria`.
- **Alternativas / fallback**: usar la base `calculadora` con un esquema propio → requiere `search_path` en la URL o cambios en `env.py` (toca el TP): descartado. Usar `calculadora` tal cual → choque potencial de nombres y `alembic_version` compartida: descartado. Si `CREATE DATABASE` fallara (p. ej. Easypanel cambió el rol), parar y consultar a la cátedra.

### D3 — Alcanzar la base por la red overlay del grupo, host `grupo1-chicas-db`
`docker run … --network easypanel-grupo1-chicas …` y `DATABASE_URL=postgresql+asyncpg://libreria:<password>@grupo1-chicas-db:5432/libreria`.
- **Por qué**: la base no publica 5432 en el host, así que `host.docker.internal` + `--add-host=…:host-gateway` no llega a nada (habría que publicar el puerto modificando el servicio de Easypanel, y exponerlo). La red es `attachable`, por lo que un contenedor común (fuera de swarm) puede unirse con `--network`. La consigna lo cubre: "Si la cátedra entrega otra dirección, se usa esa". El alias `grupo1-chicas-db` es un nombre de host válido (sin `_`) y propio del grupo; `db` es ambiguo y se evita; `grupo1-chicas_db` (nombre del servicio) también resuelve pero lleva `_`.
- **Puerto publicado**: con un contenedor sobre una overlay attachable, `-p 8101:8000` sale por `docker_gwbridge`; se verifica en D-03.
- **Alternativas**: red `easypanel` (compartida por todos los grupos y traefik) → mayor exposición: descartado. `docker network connect` después del `run` → el comando de `DEPLOY.md` dejaría de ser un solo `docker run` reproducible: descartado. Servicio swarm (`docker service create`) → no es el `docker run` que pide la consigna: descartado.

### D4 — Comando final
```
docker run -d --name libreria -p 8101:8000 --restart unless-stopped \
  --network easypanel-grupo1-chicas --env-file /root/libreria/libreria.env libreria
```
Es la forma de la consigna con un único agregado (`--network`, análogo al `--add-host` que la consigna prevé). El mismo comando se usa en D-02, D-04 y "cómo se actualiza".

### D5 — Archivo de variables (actualizado: generado en el servidor con rol propio `libreria`)
> Nota: en la ejecución, el archivo lo generó el orquestador del lado del servidor con una contraseña aleatoria para el rol `libreria` (a pedido del usuario); el script de abajo queda como forma original/alternativa. Usuario de la URL: `libreria`.

#### Forma original (creado por el usuario, sin eco)
Ubicación `/root/libreria/libreria.env` (fuera de `/root/libreria/despliegue/`, el contexto de build), `umask 077` / `chmod 600`. El usuario lo crea en **su** sesión SSH interactiva (Claude no ve la contraseña):
```
umask 077
read -rsp 'Contraseña de la base: ' PW; echo
case "$PW" in
  ''|*[!A-Za-z0-9._~-]*) echo 'Vacía o con caracteres especiales: NO se escribió el archivo; avisar.' ;;
  *) printf 'DATABASE_URL=postgresql+asyncpg://libreria:%s@grupo1-chicas-db:5432/libreria\nSQL_ECHO=false\n' "$PW" > /root/libreria/libreria.env && echo 'Archivo escrito.' ;;
esac
unset PW
```
- `read -s` no hace eco ni deja la contraseña en el historial; `printf` es interno de bash (no aparece en `ps`).
- La validación de caracteres evita dos fallas: caracteres reservados de URL (`@ : / ? #`) y `%`, que además rompe la interpolación de ConfigParser en `migrations/env.py` (no se puede tocar el TP).
- La contraseña la conoce el usuario desde el panel de Easypanel (servicio `db` → credenciales). Alternativa B, también ejecutada por el usuario: `PW=$(docker exec "$(docker ps -q -f name=grupo1-chicas_db.1)" printenv POSTGRES_PASSWORD)` en lugar del `read` (el secreto nunca sale del servidor).
- Comprobación que sí puede correr Claude: `stat -c '%a %U %n' /root/libreria/libreria.env` y `sed -E 's#(://[^:]+:)[^@]+@#\1****@#' /root/libreria/libreria.env` (contraseña enmascarada).
- Prueba de conexión previa al `run` (no deja nada corriendo): `docker run --rm --network easypanel-grupo1-chicas --env-file /root/libreria/libreria.env --entrypoint sh libreria -c 'psql "$(echo "$DATABASE_URL" | sed "s/+asyncpg//")" -Atc "select current_database()"'` → `libreria`.

### D6 — Firewall: regla `ufw` sólo si hace falta
Los puertos publicados por Docker se enrutan por `FORWARD` → `DOCKER-FORWARD` antes de `ufw` (comprobado con `:3000`), así que `ufw allow 8101/tcp` no es necesario para que D-03 funcione. Se agrega **sólo si** D-03 falla desde afuera con el contenedor `healthy` (con aprobación), y se documenta en `DEPLOY.md`. No se toca `DOCKER-USER` ni la configuración de `ufw`/Docker.

### D7 — Evidencia: texto de consola, D-01..D-08 del VPS en `evidencia/`, lo de C-10 en `evidencia/local/`
Q-14 se asume "salida de consola" (`.txt` con el comando y su salida). Los archivos de C-10 `D-01_imagenes.txt`, `D-02_arranque.txt`, `D-04_recrear.txt`, `D-05_sin_database_url.txt`, `D-06_contenido_imagen.txt`, `D-07_usuario.txt` se mueven a `evidencia/local/` (el corrector debe ver los del VPS); `IN-06_seed.txt` e `IN-07_health_ready.txt` quedan donde están (los citan `DEPLOY.md` y la KB). Nuevos: `D-01_imagenes.txt` … `D-08_aviso_comprobante.txt` del VPS, cada uno encabezado con fecha/hora, host (`srv1915306` o "fuera del VPS") y el comando. La salida de D-03 se toma con `curl -sS -i` desde la máquina de un integrante (sin registrar su IP). Se revisa con `grep` que nada muestre la contraseña ni la cadena de conexión real.

### D8 — Fecha y hora
Se registran en `DEPLOY.md` la hora del servidor en UTC (`date -u`) y en Argentina (`TZ=America/Argentina/Mendoza date`) al momento del `docker run` de D-02.

### D9 — Checkpoints de governance ALTO
Antes de cada acción que modifica el servidor se muestra el comando exacto y se espera un "sí" explícito: (1) copia de archivos, (2) `CREATE DATABASE`, (3) creación del env-file (la hace el usuario), (4) `docker build`, (5) cada `docker run` (prueba de conexión, D-02, D-05, D-04), (6) `docker exec` de datos iniciales, (7) `docker rm -f`, (8) regla `ufw`, (9) cualquier limpieza o rollback. Antes y después se guarda (fuera del repo) `docker service ls` y la lista de bases para comprobar que nada ajeno cambió. Sin commits ni push (regla 11).

## Risks / Trade-offs

- **[Reinicio del VPS con red overlay]** Un contenedor común unido a una overlay attachable puede no volver a arrancar tras reiniciar `dockerd` si la red de swarm aún no está lista ("network not found"). → No se fuerza un reinicio para probarlo (servidor compartido); `DEPLOY.md` documenta el arreglo (`docker start libreria`) y se revisa `docker ps` cuando se sepa de un reinicio. `--restart unless-stopped` cubre el caso habitual (base no lista).
- **[Swarm reprograma la base]** El nombre del contenedor de la base cambia (`grupo1-chicas_db.1.<id>`). → El host de la URL es el alias de red (estable); los `docker exec` sobre la base usan `docker ps -q -f name=grupo1-chicas_db.1`.
- **[Contraseña con caracteres especiales]** Rompería la URL o Alembic (`%`). → El script de D5 no escribe el archivo y avisa; en ese caso se para y se consulta (no se toca el TP ni la contraseña de la base sin pedido).
- **[Servidor compartido y chico]** 1 CPU / sin swap: el build y la app compiten con otros grupos. → Build único sin caché de pip; la app es liviana; `SQL_ECHO=false`.
- **[Exposición]** `:8101` queda público (es el objetivo); la base sigue sin puertos publicados.
- **[Limpieza de Easypanel]** Una poda de imágenes desde el panel podría borrar `python:3.12-alpine` si no se usa. → No afecta al contenedor en marcha; D-01 ya queda en evidencia.
- **[PostgreSQL 17 vs 16 del stack]** Las migraciones del TP son DDL estándar (C-10 probó con 16). → Si `alembic upgrade head` fallara, el contenedor termina con error (comportamiento D-05/D-02) y se para a consultar.
- **[Evidencia mueve archivos de C-10]** → Se mueven, no se borran; `DEPLOY.md` enlaza ambas carpetas.

## Migration Plan

1. Foto previa (lectura): servicios, contenedores, bases, puertos.
2. Copia de `despliegue/` (D1) → `CREATE DATABASE libreria` (D2) → env-file por el usuario (D5).
3. `docker build` (D-01) → prueba de conexión → `docker run` (D-02) → datos iniciales.
4. D-03 desde afuera (si falla con contenedor sano: regla `ufw`, D6) → D-08 → D-04 → D-05/D-06/D-07.
5. `DEPLOY.md`, evidencia, KB/CHANGES; foto posterior y comparación.

**Rollback** (cada paso con aprobación): `docker rm -f libreria`; `docker rmi libreria`; `ufw delete allow 8101/tcp` si se agregó; `DROP DATABASE libreria` vía el mismo `docker exec` (sólo esa base); `rm -rf /root/libreria`. Ninguno toca recursos ajenos.

## Open Questions

- Q-14 (formato de la evidencia): se asume salida de consola en `.txt`; si la cátedra pide capturas, se agregan sin cambiar el plan.
- Si el corrector necesita algo más que `DEPLOY.md` para entrar al servidor (no: la URL es pública y los casos D quedan en `evidencia/`).
