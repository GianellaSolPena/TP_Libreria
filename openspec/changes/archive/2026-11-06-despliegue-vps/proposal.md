# Proposal

## Why

El Ej. 10 del parcial (7 pts) pide que el TP Cap 1-4 (`despliegue/`) quede **en línea en el VPS de la cátedra**, accesible desde afuera en la URL declarada en `DEPLOY.md`, con los casos D demostrados sobre el servidor y su salida en `despliegue/evidencia/`. C-10 dejó la imagen `libreria` probada sólo en local; Q-02 ya tiene datos (VPS `187.127.58.90`, usuario `root` con clave SSH, puerto `8101`, base `grupo1-chicas_db` de Easypanel), así que el change deja de estar bloqueado. Si el despliegue no está accesible al corregir, los casos D no comprobables no suman: hay que dejarlo arriba hasta que se publiquen las notas.

## What Changes

- Llevar `despliegue/` al VPS (copia por `tar` sobre SSH, sin `.env`, `.venv`, `evidencia/`, `__pycache__`) a `/root/libreria/despliegue/` y **construir la imagen en el servidor** con `docker build -t libreria .` (D-01, D-02 sobre "servidor limpio").
- Crear en el PostgreSQL 17 de `grupo1-chicas_db` una base **nueva** `libreria` (dueño: un rol propio `libreria`, creado por decisión del usuario por prolijidad), separada de la base `calculadora` del otro proyecto del grupo, para que las tablas y `alembic_version` del TP no choquen.
- Archivo de variables en el servidor, **fuera del repo y de la imagen**: `/root/libreria/libreria.env` (`chmod 600`) con `DATABASE_URL=postgresql+asyncpg://libreria:<password>@grupo1-chicas-db:5432/libreria` y `SQL_ECHO=false`; lo genera el servidor con una contraseña aleatoria del rol `libreria` (la contraseña nunca pasa por el chat, el repo, la imagen ni los logs).
- Correr el contenedor con la forma de la consigna más la red de la base: `docker run -d --name libreria -p 8101:8000 --restart unless-stopped --network easypanel-grupo1-chicas --env-file /root/libreria/libreria.env libreria` (la base no publica puertos en el host, así que `host.docker.internal` no sirve; es "otra dirección que entrega la cátedra").
- Cargar los datos iniciales con el comando de C-10: `docker exec libreria sh -c 'psql -v ON_ERROR_STOP=1 "$(echo "$DATABASE_URL" | sed "s/+asyncpg//")" -f test/seed.sql'`.
- Evidencia de **D-01..D-08 ejecutados en el VPS** en `despliegue/evidencia/` (salida de consola, Q-14); D-03 desde afuera del VPS contra `http://187.127.58.90:8101`; D-08 con el aviso del comprobante en `docker logs libreria`. La evidencia local de C-10 se conserva en `despliegue/evidencia/local/`.
- Completar `despliegue/DEPLOY.md`: URL pública, día y hora, que se construyó en el servidor, cómo se llevaron los archivos, comandos `docker build`/`docker run` completos (nombre del env-file, sin contenido), red y base usadas, datos iniciales, cómo se actualiza, cambios al TP (sin cambios nuevos de lógica).
- Regla de `ufw` para 8101 **sólo si** D-03 falla desde afuera: los puertos publicados por Docker no pasan por las cadenas de `ufw` en este servidor (el panel `:3000` responde desde afuera sin regla).
- Registrar Q-02 como resuelta (sin secretos) en `knowledge-base/10_preguntas_abiertas.md` y marcar C-11 en `CHANGES.md` / `CLAUDE.md` / `AGENTS.md`.
- No se toca la lógica de `despliegue/` ni nada de `parcial/`; no se toca ningún servicio de Easypanel, de traefik ni de otros grupos, ni se borra nada de grupo1.

## Capabilities

### New Capabilities
- `despliegue-vps`: el TP Cap 1-4 en línea en el VPS compartido de la cátedra: imagen construida en el servidor, base propia `libreria` en el PostgreSQL del grupo, configuración por env-file fuera del repo, contenedor `libreria` publicado en `:8101` con reinicio automático, datos iniciales por `docker exec`, casos D-01..D-08 con evidencia y `DEPLOY.md` completo, sin afectar servicios ajenos.

### Modified Capabilities
<!-- Ninguna: `imagen-despliegue` ya cubre la imagen y sus casos en abstracto (sus escenarios admiten `<puerto>` y opciones extra de `docker run`); `tp-snapshots` ya admite `DEPLOY.md` y `evidencia/` en `despliegue/`. -->

## Impact

- **Repo** (sólo `despliegue/` y planificación): `despliegue/DEPLOY.md` (completar), `despliegue/evidencia/` (D-01..D-08 del VPS; los de C-10 a `evidencia/local/`); `knowledge-base/10_preguntas_abiertas.md`, `CHANGES.md`, `CLAUDE.md`/`AGENTS.md`. Ningún archivo de código.
- **Servidor compartido** (`srv1915306`, Ubuntu 24.04, Docker 29.7.1 en swarm, 1 CPU, 4 GB, 41 GB libres): nuevo directorio `/root/libreria/`, imagen `python:3.12-alpine` + `libreria`, contenedor `libreria` (fuera de swarm, adjunto a la red overlay `easypanel-grupo1-chicas`), base `libreria` en `grupo1-chicas_db`. Puerto `8101` publicado. Nada más cambia.
- **Secretos**: la contraseña de la base sólo vive en el env-file del servidor (y en la configuración de Easypanel que ya la tenía).
- **Governance**: ALTO. Cada acción que modifica el servidor (copia de archivos, crear base, crear env-file, `docker build`, `docker run`, `docker rm -f`, regla `ufw`) tiene checkpoint de aprobación del usuario. Sin commits ni push sin pedido explícito (regla 11).
- **Desbloquea**: C-12 `empaquetado-zip`.
