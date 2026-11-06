# Spec Delta

## MODIFIED Requirements

### Requirement: Conjunto exacto de archivos del snapshot
Cada snapshot (`parcial/` y `despliegue/`) SHALL haberse creado con exactamente los archivos versionados en `e337710` bajo `app/`, `migrations/`, `test/` más `alembic.ini`, `requirements.txt`, `env.example` y `README.md`, con sus rutas relativas preservadas, y ningún otro archivo de ese commit. Después de creado, `parcial/` evoluciona por los changes del parcial (C-02 en adelante); `despliegue/` SHALL conservar ese conjunto y sólo MAY sumar los archivos de despliegue: `Dockerfile`, `.dockerignore`, `DEPLOY.md` y `evidencia/`.

#### Scenario: Snapshot recién creado contiene la lista esperada
- **WHEN** se compara la lista de archivos de un snapshot recién creado con la lista de esos paths en `e337710`
- **THEN** ambas listas son iguales (62 archivos, incluidas las capturas PNG de `test/C-07_CapturasPantalla/`)

#### Scenario: Archivos del commit fuera del alcance quedan excluidos
- **WHEN** se inspecciona `despliegue/`
- **THEN** no existen `PLAN.md`, `TP_Cap1a4_Consigna.pdf` ni `.gitignore`

#### Scenario: Faltante o sobrante se detecta
- **WHEN** a una copia le falta un archivo esperado o (en `despliegue/`) tiene un archivo adicional fuera de los archivos de despliegue permitidos
- **THEN** la verificación falla e informa la ruta faltante o sobrante

#### Scenario: Despliegue sólo suma archivos de despliegue
- **WHEN** se compara la lista de archivos de `despliegue/` con la de `e337710`
- **THEN** no falta ninguno y los únicos sobrantes son `Dockerfile`, `.dockerignore`, `DEPLOY.md` y lo que haya bajo `evidencia/`

### Requirement: Contenido idéntico al commit entregado
El contenido de cada archivo de un snapshot recién creado SHALL ser idéntico al blob de `e337710` en la misma ruta, comparado como lo almacenaría git (independiente de la conversión de fin de línea del checkout). En `despliegue/` los únicos archivos del TP que MAY diferir son los de la corrección de defectos propios anotados en `DEPLOY.md`: `app/modules/health/router.py` y `app/modules/health/service.py` (IN-07), `README.md` (IN-06) y `env.example` (forma de `DATABASE_URL` para el contenedor).

#### Scenario: Copia fiel verifica sin diferencias
- **WHEN** se verifica `parcial/` o `despliegue/` contra `e337710` inmediatamente después de crearlas
- **THEN** la verificación no reporta diferencias de contenido

#### Scenario: Despliegue difiere sólo en los defectos anotados
- **WHEN** se compara el contenido de `despliegue/` con `e337710` después de C-10
- **THEN** sólo difieren `app/modules/health/router.py`, `app/modules/health/service.py`, `README.md` y `env.example`

#### Scenario: Archivo modificado se detecta
- **WHEN** se altera el contenido de otro archivo de `despliegue/` (por ejemplo `app/main.py`)
- **THEN** la comparación con `e337710` informa esa ruta como contenido distinto
