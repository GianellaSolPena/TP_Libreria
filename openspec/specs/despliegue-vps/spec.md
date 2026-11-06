# despliegue-vps Specification

## Purpose
Dejar el TP Cap 1-4 (`despliegue/`) en línea en el VPS compartido de la cátedra, accesible desde afuera en la URL declarada, con su propia base dentro del PostgreSQL del grupo, sin secretos fuera del servidor, sin afectar servicios ajenos y con los casos D-01..D-08 demostrados y documentados (Ej. 10 del parcial).

## Requirements

### Requirement: Aplicación accesible en la URL pública declarada
El contenedor `libreria` SHALL correr en el VPS publicando sólo el puerto 8000 de la aplicación en el puerto `8101` del servidor, con `--restart unless-stopped`, de modo que `http://187.127.58.90:8101` responda desde fuera del VPS. La aplicación SHALL seguir en línea hasta que se publiquen las notas.

#### Scenario: D-03 salud desde afuera
- **WHEN** desde una máquina fuera del VPS se pide `GET http://187.127.58.90:8101/health/ready`
- **THEN** responde 200

#### Scenario: D-03 catálogo con datos iniciales
- **WHEN** con los datos iniciales cargados se pide desde afuera `GET http://187.127.58.90:8101/libros/`
- **THEN** responde 200 con la lista de los libros de `test/seed.sql`

#### Scenario: D-03 venta de ejemplo del TP
- **WHEN** desde afuera se hace `POST http://187.127.58.90:8101/ventas/` con el cuerpo de ejemplo del TP (`cliente_id` 2; libro 1 x2 y libro 4 x1)
- **THEN** responde 201 con el precio de cada renglón copiado del libro y el total calculado por el servidor

#### Scenario: Reinicio automático
- **WHEN** el contenedor termina (por ejemplo, la base no respondía al arrancar o el servidor se reinició)
- **THEN** Docker lo vuelve a levantar sin intervención y regresa a `healthy` cuando la base contesta

### Requirement: Base propia dentro del PostgreSQL del grupo
La aplicación SHALL usar una base dedicada (`libreria`) dentro del servicio PostgreSQL del grupo (`grupo1-chicas_db`), alcanzada por la red interna del grupo y nunca por `localhost`. Las migraciones y los datos iniciales del TP MUST NOT crear, modificar ni vaciar tablas de otras bases del mismo servidor (en particular la base `calculadora`). La base `libreria` pertenece a un rol propio `libreria`.

#### Scenario: Esquema del TP aislado
- **WHEN** el contenedor arranca por primera vez contra la base `libreria` vacía
- **THEN** `alembic upgrade head` crea las tablas del TP y su `alembic_version` sólo en `libreria`, y la base `calculadora` conserva exactamente sus tablas previas

#### Scenario: Datos iniciales sólo en la base del TP
- **WHEN** se ejecuta el comando de datos iniciales dentro del contenedor
- **THEN** las tablas del TP en `libreria` quedan con los datos de `test/seed.sql` y ninguna otra base cambia

#### Scenario: DATABASE_URL sin localhost
- **WHEN** se revisa la forma de `DATABASE_URL` documentada en `DEPLOY.md`
- **THEN** usa el driver `postgresql+asyncpg`, el nombre interno de la base del grupo como host y la base `libreria`, y nunca `localhost` ni `127.0.0.1`

### Requirement: Configuración fuera del repositorio y de la imagen
La configuración del contenedor SHALL entrar sólo por un archivo de variables que vive en el servidor, fuera del repositorio, del contexto de construcción y de la imagen, legible sólo por su dueño, con `DATABASE_URL` y `SQL_ECHO=false`. La contraseña de la base MUST NOT aparecer en el repositorio, en la imagen, en `DEPLOY.md`, en `evidencia/`, en el historial de comandos mostrado ni en el chat.

#### Scenario: Archivo de variables protegido
- **WHEN** se inspeccionan en el servidor los permisos y la ubicación del archivo de variables
- **THEN** tiene permisos `600`, está fuera del directorio desde el que se construye la imagen, y `DEPLOY.md` sólo nombra el archivo sin mostrar su contenido

#### Scenario: Sin consultas en el registro
- **WHEN** el contenedor atiende peticiones
- **THEN** `docker logs libreria` no muestra las consultas SQL (`SQL_ECHO=false`)

#### Scenario: Evidencia y documentación sin secretos
- **WHEN** se buscan la contraseña de la base y cadenas `postgresql://usuario:clave@` con valores reales en `despliegue/` (incluidos `DEPLOY.md` y `evidencia/`)
- **THEN** no se encuentra ninguna credencial real

### Requirement: Casos D demostrados en el VPS con evidencia
Los casos D-01..D-08 SHALL ejecutarse sobre el servidor (D-03 desde afuera, sobre la URL pública) y su comando y salida de consola SHALL guardarse en `despliegue/evidencia/`, un archivo por caso. La evidencia local previa de C-10 SHALL conservarse separada (`evidencia/local/`).

#### Scenario: D-01 y D-02 en el servidor
- **WHEN** se construye la imagen en el VPS y se corre el contenedor contra la base `libreria` vacía
- **THEN** `docker images` muestra `python:3.12-alpine` menor a 100 MB y `libreria`, `docker logs libreria` muestra las migraciones del TP aplicadas antes del arranque de uvicorn y `docker ps` muestra `libreria` como `healthy`

#### Scenario: D-04 recrear sin perder datos
- **WHEN** en el VPS se ejecuta `docker rm -f libreria` y el mismo `docker run`
- **THEN** vuelve a `healthy`, los libros y la venta de D-03 siguen y los logs no aplican migraciones nuevas

#### Scenario: D-05, D-06 y D-07 en el servidor
- **WHEN** en el VPS se corre la imagen sin `DATABASE_URL`, se lista `/app` y el entorno de la imagen, y se ejecuta `docker exec libreria id`
- **THEN** el contenedor sin `DATABASE_URL` termina con error, no hay `.env` en `/app` ni `DATABASE_URL`/contraseñas en el entorno de la imagen, y el usuario del proceso no es root

#### Scenario: D-08 aviso del comprobante
- **WHEN** después de la venta de D-03 se mira `docker logs libreria`
- **THEN** la línea "Comprobante de la venta N enviado" de esa venta aparece después de la línea de acceso de la respuesta del `POST /ventas/`

### Requirement: DEPLOY.md completo
`despliegue/DEPLOY.md` SHALL incluir la URL pública, el día y la hora del despliegue, que la imagen se construyó en el servidor y cómo se llevaron los archivos, los comandos `docker build` y `docker run` completos tal como se ejecutaron (con el nombre del archivo de variables y sin su contenido), la base y la red usadas, el comando de datos iniciales, los cambios hechos al TP para que corra en el contenedor, y cómo se actualiza (reconstruir, `docker rm -f libreria`, mismo `docker run`; los datos viven en la base). Los comandos que no entran cómodos en una línea (más de ~100 caracteres) SHALL partirse en varias líneas con `\` al final, sin cambiar ningún argumento, de modo que el bloque se pueda copiar y pegar tal cual en un shell POSIX.

#### Scenario: Comandos reproducibles
- **WHEN** se ejecutan en el servidor, en orden, los comandos de actualización de `DEPLOY.md`
- **THEN** el contenedor vuelve a `healthy` en la misma URL con los mismos datos

#### Scenario: Sin pendientes
- **WHEN** se lee `DEPLOY.md` al cerrar el change
- **THEN** no quedan marcas de "pendiente" en URL, fecha y hora, lugar de construcción ni casos D-03/D-08

#### Scenario: Comandos largos partidos
- **WHEN** se buscan en los bloques de código de `DEPLOY.md` líneas de comando de más de ~100 caracteres
- **THEN** no hay ninguna, y al unir las líneas terminadas en `\` se obtienen exactamente los mismos argumentos que antes del cambio

### Requirement: Sin impacto sobre servicios ajenos
El despliegue MUST NOT detener, reconfigurar, reiniciar ni borrar servicios, contenedores, imágenes, volúmenes, redes ni bases de Easypanel, traefik u otros grupos, ni recursos existentes de grupo1 (aplicaciones calculadora, base `calculadora`, servicio `db`). Sólo SHALL agregar: el directorio `/root/libreria/`, las imágenes `python:3.12-alpine` y `libreria`, el contenedor `libreria`, la base `libreria` y, si hace falta, una regla de firewall para el puerto 8101.

#### Scenario: Servicios previos intactos
- **WHEN** se compara `docker service ls` y la lista de bases del PostgreSQL del grupo antes y después del despliegue
- **THEN** todos los servicios previos conservan sus réplicas e imagen, y la única base nueva es `libreria`

#### Scenario: Puerto libre y sin colisión de nombres
- **WHEN** antes de `docker run` se revisan los puertos en escucha y los contenedores e imágenes existentes
- **THEN** `8101` no está en uso y no existe contenedor ni imagen `libreria` ajenos que se pisen
