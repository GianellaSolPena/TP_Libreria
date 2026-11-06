# imagen-despliegue Specification

## Purpose
Empaquetar el TP Cap 1-4 (`despliegue/`) en una imagen Docker que arranca sola en un servidor limpio: aplica las migraciones, se declara sana sólo si la base contesta, no lleva secretos, no corre como root y permite cargar los datos iniciales desde dentro del contenedor (Ej. 9 del parcial, casos D).

## Requirements

### Requirement: Imagen basada en python:3.12-alpine
La imagen del proyecto SHALL construirse a partir de `python:3.12-alpine` (imagen base menor a 100 MB), con una sola instrucción de construcción (`docker build`) desde `despliegue/` y sin Docker Compose. Las dependencias de `requirements.txt` MUST instalarse antes de copiar el código y sin guardar la caché de pip, y MUST NOT requerir compilador. El único paquete del sistema adicional permitido es `postgresql-client` (instalado con `apk add --no-cache`, como root y antes de `USER`), necesario para la carga de datos iniciales.

#### Scenario: D-01 imagen base menor a 100 MB
- **WHEN** se lista `docker images` después de construir
- **THEN** aparece `python:3.12-alpine` con menos de 100 MB y la imagen del proyecto, y el Dockerfile parte de esa base

#### Scenario: Cliente psql disponible en la imagen
- **WHEN** se ejecuta `docker run --rm --entrypoint psql <imagen> --version`
- **THEN** informa la versión del cliente y la imagen base sigue siendo `python:3.12-alpine`

#### Scenario: Cambio sólo de código reutiliza la capa de dependencias
- **WHEN** se modifica un archivo de `app/` sin tocar `requirements.txt` y se vuelve a construir
- **THEN** la capa de instalación de dependencias se toma de la caché de construcción

### Requirement: Arranque con migraciones encadenadas
Al iniciar, el contenedor SHALL aplicar `alembic upgrade head` y sólo si termina bien SHALL iniciar el servidor de `app.main:app` en `0.0.0.0:8000` como proceso principal. Si las migraciones fallan, el contenedor MUST terminar con código distinto de cero, sin levantar el servidor.

#### Scenario: D-02 arranque en servidor limpio
- **WHEN** se construye la imagen y se corre con `docker run -d --name libreria -p <puerto>:8000 --env-file <archivo> libreria` contra una base vacía accesible
- **THEN** `docker logs libreria` muestra las migraciones aplicadas antes del arranque de uvicorn y `docker ps` muestra el contenedor `healthy`

#### Scenario: D-04 recrear el contenedor conserva los datos
- **WHEN** se ejecuta `docker rm -f libreria` y el mismo `docker run` otra vez
- **THEN** el contenedor vuelve a `healthy`, los datos cargados siguen en la base y `docker logs` no muestra migraciones nuevas aplicadas

#### Scenario: Migración fallida detiene el contenedor
- **WHEN** la base indicada en `DATABASE_URL` no es accesible al arrancar
- **THEN** el contenedor termina con código distinto de cero y no queda un servidor escuchando

### Requirement: Sin configuración por defecto de la base
La imagen MUST NOT contener la dirección ni la contraseña de la base ni ningún archivo `.env`; la configuración SHALL entrar sólo por variables de entorno en `docker run`. Sin `DATABASE_URL` el contenedor MUST terminar con error.

#### Scenario: D-05 sin DATABASE_URL
- **WHEN** se corre la imagen sin definir `DATABASE_URL`
- **THEN** el contenedor termina con código distinto de cero y el log indica que falta `DATABASE_URL`

#### Scenario: D-06 la imagen no lleva secretos
- **WHEN** se ejecuta `docker run --rm --entrypoint ls <imagen> -a /app` y `docker run --rm --entrypoint env <imagen>`
- **THEN** no aparece `.env`, `.venv`, `.git` ni `__pycache__` en `/app`, y el entorno no muestra `DATABASE_URL` ni contraseñas

### Requirement: Proceso sin privilegios
El proceso del contenedor SHALL correr con un usuario distinto de root.

#### Scenario: D-07 usuario del proceso
- **WHEN** se ejecuta `docker exec libreria id` con el contenedor corriendo
- **THEN** el uid informado no es 0 ni el usuario es `root`

### Requirement: Healthcheck sobre la salud lista
La imagen SHALL declarar un `HEALTHCHECK` que consulta `GET http://127.0.0.1:8000/health/ready` con `wget` y marca el contenedor `unhealthy` cuando esa ruta no responde 200.

#### Scenario: Sano con la base disponible
- **WHEN** el contenedor está corriendo y la base contesta
- **THEN** `docker inspect --format '{{.State.Health.Status}}' libreria` informa `healthy`

#### Scenario: No sano con la base caída
- **WHEN** la base deja de contestar con el contenedor corriendo
- **THEN** tras los reintentos configurados el estado pasa a `unhealthy`

### Requirement: Salud lista del TP responde 503 con la base caída
En `despliegue/`, `GET /health/ready` SHALL responder 200 cuando la base contesta a `SELECT 1` y 503 con un cuerpo propio de la aplicación cuando no contesta (conexión rechazada, host inexistente o demora mayor a unos pocos segundos), MUST NOT responder 500 ni exponer texto del driver o de PostgreSQL. `GET /health/live` no cambia (200 sin tocar la base).

#### Scenario: Listo con la base disponible
- **WHEN** se pide `GET /health/ready` con la base disponible
- **THEN** responde 200

#### Scenario: No listo con la base caída
- **WHEN** la base no contesta y se pide `GET /health/ready`
- **THEN** responde 503 con un cuerpo propio, sin texto interno de la base, y nunca 500

#### Scenario: Se recupera sin reiniciar
- **WHEN** la base vuelve a contestar después de un 503
- **THEN** la siguiente petición a `GET /health/ready` responde 200 sin reiniciar el proceso

### Requirement: Datos iniciales cargables dentro del contenedor
`despliegue/` SHALL ofrecer un comando de datos iniciales que corre dentro de la imagen con `psql` (cliente `postgresql-client` instalado en la imagen), usando `DATABASE_URL` sin su sufijo `+asyncpg`, y que carga exactamente `test/seed.sql` sin agregar código al TP. El comando SHALL ser re-ejecutable (deja la base siempre en el mismo estado) y el README del TP SHALL indicarlo.

#### Scenario: Carga dentro del contenedor
- **WHEN** con el contenedor `healthy` se ejecuta `docker exec libreria sh -c 'psql -v ON_ERROR_STOP=1 "$(echo "$DATABASE_URL" | sed "s/+asyncpg//")" -f test/seed.sql'`
- **THEN** termina con código 0 y `GET /libros/` devuelve los cinco libros del seed

#### Scenario: Re-ejecución deja el mismo estado
- **WHEN** se ejecuta el comando de datos iniciales dos veces seguidas
- **THEN** la base queda con los mismos datos e ids que después de la primera ejecución

#### Scenario: Error de la base no queda a medias
- **WHEN** la carga falla (por ejemplo, tablas sin migrar)
- **THEN** el comando (con `-v ON_ERROR_STOP=1`) termina con código distinto de cero y la base no queda con una carga parcial

### Requirement: Cambios al TP acotados y documentados
Sobre `despliegue/` sólo SHALL agregarse los archivos de despliegue (`Dockerfile`, `.dockerignore`, `DEPLOY.md`, `evidencia/`) y corregirse los defectos propios IN-06 e IN-07 (con su ajuste en `README.md` y `env.example`); el resto de la lógica del TP MUST NOT cambiar. `DEPLOY.md` SHALL listar cada cambio hecho al TP y los comandos `docker build` y `docker run` completos (nombre del archivo de variables, nunca su contenido). `env.example` SHALL mostrar la forma de `DATABASE_URL` sin valores reales.

#### Scenario: Diff acotado contra el TP entregado
- **WHEN** al cerrar el change se listan los archivos de `despliegue/` agregados o modificados respecto de su estado anterior a este change (`git status`/`git diff --stat HEAD -- despliegue/`)
- **THEN** sólo aparecen los archivos enumerados en este requisito (más `app/modules/health/`, que es la corrección de IN-07)

#### Scenario: DEPLOY.md documenta los cambios
- **WHEN** se lee `despliegue/DEPLOY.md`
- **THEN** figuran IN-06 e IN-07 como cambios hechos al TP y los comandos `docker build` y `docker run` completos, sin credenciales
