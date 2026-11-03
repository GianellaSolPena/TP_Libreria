## Purpose

Define cómo la aplicación del parcial lee su configuración desde el entorno sin secretos por defecto y cómo crea y libera sus recursos compartidos durante el arranque y el apagado.

## ADDED Requirements

### Requirement: Configuración leída del entorno
La aplicación SHALL leer su configuración desde variables de entorno o desde un archivo `.env` no versionado, y SHALL armar la dirección de la base con `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST` y `POSTGRES_PORT` usando el driver `postgresql+asyncpg`.

#### Scenario: Arranque con un .env completo
- **WHEN** existe un `.env` con todas las variables de `env.example` completadas y la base está disponible
- **THEN** la aplicación arranca y responde `GET /health/ready` con 200

#### Scenario: Las migraciones usan la misma configuración
- **WHEN** se ejecuta `alembic upgrade head` con el mismo `.env`
- **THEN** Alembic se conecta a la base indicada por las variables `POSTGRES_*` sin que `alembic.ini` contenga credenciales

### Requirement: Secretos sin valor por defecto
La clave de firma de los tokens y `POSTGRES_PASSWORD` MUST NOT tener valor por defecto en el código ni generarse al arrancar; si alguna falta, la aplicación MUST NOT arrancar.

#### Scenario: Falta la clave de firma
- **WHEN** se arranca la aplicación sin la variable de la clave de firma
- **THEN** el arranque falla con un error que nombra la variable faltante y el servidor no atiende peticiones

#### Scenario: Falta la contraseña de la base
- **WHEN** se arranca la aplicación sin `POSTGRES_PASSWORD`
- **THEN** el arranque falla con un error que nombra la variable faltante y el servidor no atiende peticiones

### Requirement: Plantilla de variables sin secretos
El proyecto SHALL incluir un `env.example` que liste todas las variables que lee la configuración y MUST NOT contener valores secretos reales.

#### Scenario: env.example completo
- **WHEN** se compara `env.example` con las variables declaradas en la configuración
- **THEN** están todas y la clave de firma y la contraseña aparecen vacías o con un marcador evidente

### Requirement: Recursos creados en el arranque y liberados al apagar
El motor asincrónico (con `SQL_ECHO` y el tamaño del pool de la configuración) y la fábrica de sesiones SHALL crearse al arrancar la aplicación, no al importar un módulo, y SHALL liberarse al apagarla. El hash ficticio del login SHALL calcularse una sola vez al arrancar.

#### Scenario: Consultas visibles con SQL_ECHO
- **WHEN** se arranca con `SQL_ECHO=true` y se hace una petición que consulta la base
- **THEN** la consola muestra las sentencias SQL ejecutadas

#### Scenario: Apagado ordenado
- **WHEN** se detiene el servidor
- **THEN** las conexiones del motor se cierran y el proceso termina sin errores

### Requirement: Una sesión por petición
Cada petición que use la base SHALL recibir su propia sesión, creada sin expirar los objetos al confirmar, y la sesión SHALL cerrarse al terminar la petición.

#### Scenario: Rutas existentes siguen funcionando
- **WHEN** se ejecuta una petición de lectura y una de alta de los módulos existentes (por ejemplo `GET /editoriales/` y `POST /editoriales/`)
- **THEN** responden igual que antes del cambio
