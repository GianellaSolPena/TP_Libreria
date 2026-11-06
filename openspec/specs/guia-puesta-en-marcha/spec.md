# guia-puesta-en-marcha Specification

## Purpose
Definir el contenido de `parcial/README.md`: integrantes, entorno virtual, dependencias, `.env` y clave de firma, migraciones, seed y arranque, de modo que un tercero pueda levantar el proyecto desde cero.

## Requirements

### Requirement: Integrantes del grupo
`parcial/README.md` SHALL nombrar al comienzo a los integrantes del grupo con nombre y apellido, tal como los confirma el grupo.

#### Scenario: Lectura del encabezado
- **WHEN** se abre `parcial/README.md`
- **THEN** antes de los pasos de instalación figura la lista de integrantes con nombre y apellido

### Requirement: Pasos desde cero hasta el servidor con datos
`parcial/README.md` SHALL describir, en orden y con los comandos exactos para Windows y para un shell POSIX cuando difieran: crear y activar el entorno virtual; instalar las dependencias de `requirements.txt`; crear `.env` a partir de `env.example`, con la tabla de variables y cómo generar la clave de firma `JWT_SECRET_KEY`; `alembic upgrade head`; `python seed.py`; y arrancar el servidor con `uvicorn main:app`. Todos los comandos MUST correrse desde `parcial/`. El README MUST aclarar que `.env` no se versiona, que sin `POSTGRES_PASSWORD` o sin `JWT_SECRET_KEY` la aplicación no arranca, y MUST NOT contener ningún secreto real.

#### Scenario: Puesta en marcha siguiendo el README
- **WHEN** alguien sigue el README paso a paso sobre una base PostgreSQL vacía
- **THEN** llega al servidor arriba, `GET /health/ready` responde 200 y `GET /libros` devuelve los cinco libros del seed

#### Scenario: Clave de firma
- **WHEN** se busca en el README cómo completar `JWT_SECRET_KEY`
- **THEN** hay un comando que genera una clave aleatoria y la indicación de pegarla en `.env`

### Requirement: Guía de los casos de prueba y la evidencia
`parcial/README.md` SHALL listar los usuarios del seed con su rol y su contraseña de mentira, explicar que antes de cada archivo de casos se corre `python seed.py`, indicar la extensión con la que se corren los `.http` y cómo se manejan varias sesiones, y traer una tabla con cada caso C-01..C-16, su archivo y qué demuestra. MUST indicar qué casos requieren `SQL_ECHO=true` o psql, y dónde está la evidencia de C-14 y C-15.

#### Scenario: Ubicar un caso
- **WHEN** se busca en el README el caso C-14 o C-15
- **THEN** la tabla indica el archivo que lo demuestra, la condición para correrlo y el archivo de `evidencia/` correspondiente

### Requirement: Descripción coherente con el parcial
`parcial/README.md` SHALL describir el proyecto del parcial (capítulos 1 a 6): estructura `main.py`/`seed.py` en la raíz y `app/core`, `app/modules`, rutas actuales sin barra final, paginación con `page` y `size` y el envoltorio `{items, total, page, size, pages}`. MUST NOT quedar instrucciones del TP que ya no aplican (por ejemplo `test/seed.sql`, `limit`/`offset` o la numeración vieja de los casos).

#### Scenario: Sin restos del TP
- **WHEN** se busca en el README `seed.sql`, `limit`, `offset` o rutas con barra final
- **THEN** no aparecen como instrucciones vigentes
