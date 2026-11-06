# empaquetado-entrega Specification

## Purpose

Producir el único archivo `.zip` de entrega del parcial (Cap 1-6) con el nombre y el contenido que pide la consigna, sin credenciales reales ni archivos generados, y comprobado de modo que el proyecto levante desde cero a partir del zip extraído.

## Requirements

### Requirement: Nombre del archivo de entrega
El archivo de entrega SHALL llamarse exactamente `Parcial_Cap1a6_Las_chicas.zip` (grupo "Las chicas" de Q-01, con guion bajo en lugar de espacio) y SHALL ser un único archivo ZIP que se pueda abrir con las herramientas estándar de Windows y de Linux.

#### Scenario: Nombre correcto
- **WHEN** se inspecciona el archivo producido
- **THEN** su nombre es `Parcial_Cap1a6_Las_chicas.zip` y se abre sin errores con el explorador de Windows y con un lector ZIP estándar

### Requirement: Sólo las dos carpetas del proyecto en la raíz del zip
El zip SHALL contener en su raíz únicamente las carpetas `parcial/` y `despliegue/`. Ningún archivo ni carpeta de la raíz del repositorio de planificación (`knowledge-base/`, `openspec/`, `.claude/`, `.atl/`, `CHANGES.md`, `CLAUDE.md`, `AGENTS.md`, `README.md` de la raíz, la consigna en PDF, `.gitignore`, `.gitattributes`) MUST aparecer en el zip. Las rutas de las entradas SHALL usar `/` como separador y empezar por `parcial/` o `despliegue/`.

#### Scenario: Raíz del zip
- **WHEN** se listan las entradas del zip
- **THEN** toda entrada empieza por `parcial/` o `despliegue/` y ninguna contiene `\`

#### Scenario: Sin planificación
- **WHEN** se buscan en el listado `knowledge-base`, `openspec`, `.claude`, `.atl`, `CHANGES.md` o `Consigna`
- **THEN** no aparece ninguna entrada

### Requirement: Contenido de parcial/
`parcial/` en el zip SHALL contener el código fuente completo (`main.py`, `seed.py`, `app/`), `requirements.txt`, `env.example`, `alembic.ini`, `migrations/` con las revisiones 0001 a 0004, `test/` con los `.http` de los casos C y `solo_agregado.sql`, `README.md` con los nombres y apellidos de las integrantes (Agustina Fontagnol, Martina Suarez y Gianella Peña) y los pasos desde cero, y `evidencia/` con la evidencia de C-14 (texto de consola y captura de psql) y C-15. El `README.md` SHALL mencionar tanto `C-14_solo_agregado.txt` como `C-14_captura_psql.png`. Cada archivo SHALL ser byte a byte igual al versionado en el commit desde el que se arma el zip.

#### Scenario: Archivos obligatorios de parcial
- **WHEN** se lista `parcial/` en el zip
- **THEN** están `main.py`, `seed.py`, `app/`, `requirements.txt`, `env.example`, `alembic.ini`, `migrations/versions/0001_*` a `0004_*`, `test/*.http`, `test/solo_agregado.sql`, `README.md`, `evidencia/C-14_solo_agregado.txt`, `evidencia/C-14_captura_psql.png` y `evidencia/C-15_consultas_detalle_venta.txt`

#### Scenario: Integrantes en el README
- **WHEN** se lee `parcial/README.md` del zip
- **THEN** lista a Agustina Fontagnol, Martina Suarez, Gianella Peña y Yoselie Aquino

#### Scenario: Captura de C-14 y README coherentes
- **WHEN** se inspecciona `parcial/` en el zip extraído
- **THEN** existe `evidencia/C-14_captura_psql.png` y `README.md` la menciona junto a `C-14_solo_agregado.txt`

#### Scenario: Fidelidad al commit
- **WHEN** se compara cada archivo extraído con el blob de `parcial/` del commit de origen
- **THEN** coinciden todos, incluidos sus finales de línea

### Requirement: Contenido de despliegue/
`despliegue/` en el zip SHALL contener el TP Cap 1-4 tal como está versionado (código, `migrations/`, `test/`, `requirements.txt`, `alembic.ini`, `README.md`) más `Dockerfile`, `.dockerignore`, `env.example` (forma de `DATABASE_URL`, sin valores reales), `DEPLOY.md` y `evidencia/` con la salida de cada caso D-01 a D-08. `evidencia/local/` SHALL incluirse porque `DEPLOY.md` la enlaza. Cada archivo SHALL ser byte a byte igual al versionado en el commit de origen.

#### Scenario: Archivos de despliegue
- **WHEN** se lista `despliegue/` en el zip
- **THEN** están `Dockerfile`, `.dockerignore`, `env.example`, `DEPLOY.md` y `evidencia/D-01_*` a `evidencia/D-08_*`

#### Scenario: Enlaces de DEPLOY.md resueltos
- **WHEN** se sigue cada enlace relativo de `despliegue/DEPLOY.md` dentro del zip extraído
- **THEN** cada archivo enlazado existe, incluidos los de `evidencia/local/`

### Requirement: Exclusiones
El zip MUST NOT contener, en ningún nivel de ninguna de las dos carpetas, `.git`, `.venv`, `__pycache__`, archivos `*.pyc`, `.env` ni otros `.env.*` distintos de `env.example`, ni `.pytest_cache`.

#### Scenario: Sin archivos generados ni secretos locales
- **WHEN** se buscan en el listado entradas con `.git/`, `.venv/`, `__pycache__/`, `.pyc`, `/.env` o `.pytest_cache`
- **THEN** no aparece ninguna

### Requirement: Sin credenciales reales
El contenido del zip MUST NOT incluir credenciales reales: ni la contraseña de ninguna base real (local o del VPS), ni el valor de ninguna clave de firma JWT real, ni una `DATABASE_URL` con usuario y contraseña reales, ni material de clave privada, ni la ruta o el nombre de la clave SSH del VPS. Sólo MAY aparecer: las contraseñas de mentira del seed documentadas (Q-05), los marcadores de `env.example` (`usuario:password@<host>`, valores vacíos) y la URL pública declarada del despliegue.

#### Scenario: Búsqueda de secretos limpia
- **WHEN** se busca en el contenido extraído por asignaciones no vacías de `POSTGRES_PASSWORD`, `JWT_SECRET_KEY` o `DATABASE_URL` con credenciales, por `PRIVATE KEY`, por la ruta o el nombre de la clave SSH y por los valores reales de los `.env` locales
- **THEN** no hay coincidencias fuera de las permitidas

#### Scenario: Direcciones IP revisadas
- **WHEN** se listan las direcciones IPv4 que aparecen en el contenido extraído
- **THEN** sólo aparecen la del VPS de la URL pública declarada, direcciones de loopback, `0.0.0.0` y direcciones internas de Docker, y ninguna IP pública propia de una integrante

### Requirement: El parcial levanta desde el zip
`parcial/` extraído del zip, en un directorio nuevo y sin nada del repositorio, SHALL poder instalarse y levantarse siguiendo su `README.md`: entorno virtual, `pip install -r requirements.txt`, `.env` creado a partir de `env.example`, `alembic upgrade head` sobre una base PostgreSQL 16 vacía, `python seed.py` y arranque del servidor.

#### Scenario: Esquema desde base vacía
- **WHEN** con un `.env` de prueba se ejecuta `alembic upgrade head` desde `parcial/` extraído contra una base PostgreSQL 16 vacía
- **THEN** termina sin error en la revisión 0004

#### Scenario: Datos iniciales y salud
- **WHEN** después se ejecuta `python seed.py` y se arranca el servidor
- **THEN** el seed termina sin error y `GET /health/ready` responde 200

### Requirement: El despliegue construye desde el zip
`despliegue/` extraído del zip SHALL construir su imagen con `docker build` sin archivos externos al zip, y el contenedor SHALL aplicar sus migraciones y quedar sano contra una base vacía.

#### Scenario: Imagen desde el zip
- **WHEN** se ejecuta `docker build` sobre `despliegue/` extraído
- **THEN** la imagen se construye sin error

#### Scenario: Contenedor sano
- **WHEN** se ejecuta el contenedor con `DATABASE_URL` apuntando a una base PostgreSQL 16 vacía de prueba
- **THEN** `alembic upgrade head` termina sin error y `GET /health/ready` responde 200

### Requirement: Aprobación del contenido antes de entregar
El zip final MUST NOT considerarse listo para subir al campus hasta que el usuario haya revisado el listado completo de entradas y el resultado de la búsqueda de secretos y lo haya aprobado de forma explícita. El zip SHALL armarse fuera del repositorio y MUST NOT versionarse.

#### Scenario: Listado aprobado
- **WHEN** se termina de armar y verificar el zip
- **THEN** se presenta al usuario el listado de entradas y el resumen de verificación y se espera su aprobación explícita

#### Scenario: Zip fuera del repo
- **WHEN** se revisa `git status` después de armar el zip
- **THEN** no aparece el zip ni ningún archivo nuevo en `parcial/` o `despliegue/`
