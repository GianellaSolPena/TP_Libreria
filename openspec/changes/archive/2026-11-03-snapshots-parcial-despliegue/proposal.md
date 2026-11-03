# Proposal

## Why

El parcial (Ej. 1-8) se resuelve evolucionando el TP Cap 1-4 entregado, pero el despliegue (Ej. 9-10, 18 pts) exige el TP **tal como se entregó** (DD-03). Si se modifica el código antes de congelar una copia fiel del commit `e337710`, se pierde la base de `despliegue/` y el punto de partida verificable de `parcial/`. Este change es el GATE 0: ningún otro change puede empezar hasta que ambas copias existan y estén verificadas.

## What Changes

- Se crean `parcial/` y `despliegue/` como copias idénticas (contenido de blob git) del TP en `e337710`, extraídas desde git (no desde el working tree), con exactamente: `app/`, `migrations/`, `test/`, `alembic.ini`, `requirements.txt`, `env.example`, `README.md` (62 archivos).
- Quedan fuera: `PLAN.md`, `TP_Cap1a4_Consigna.pdf`, `.gitignore`, `.git`, `.venv`, `__pycache__`, `*.pyc`, `.env`, `.pytest_cache`.
- Se crea el tag git local `tp-cap1a4-entregado` sobre `e337710` como respaldo (no se pushea en este change).
- Se agrega una herramienta de verificación en la raíz (`tools/snapshots.py`) que lista los archivos esperados, crea una copia y verifica una copia contra `e337710` (faltantes, sobrantes, contenido distinto, artefactos prohibidos), y verifica que los archivos del TP en la raíz no cambiaron.
- Se agrega una suite pytest mínima en `tests/` (raíz) que ejercita esa verificación (unitaria sobre copias temporales + integración sobre las copias reales).
- Se documenta la regla de layout (raíz intacta; parcial sólo en `parcial/`; `despliegue/` sólo recibe Docker/VPS) — ya presente en `CLAUDE.md`/`AGENTS.md`; se verifica y se referencia la herramienta.
- **No** se mueve `main.py` (eso es C-03) ni se agrega nada de Docker (C-19..C-21).

## Capabilities

### New Capabilities
- `tp-snapshots`: copias congeladas/base del TP Cap 1-4 entregado (`parcial/`, `despliegue/`), su contenido exacto, exclusiones y la verificación de integridad contra el commit entregado y de la raíz intacta.

### Modified Capabilities
<!-- Ninguna: no hay specs previas en openspec/specs/. -->

## Impact

- Nuevos directorios: `parcial/`, `despliegue/` (copias), `tools/` y `tests/` en la raíz (herramientas del repo, no son código del TP).
- Git: tag local `tp-cap1a4-entregado`. Sin commits en la fase de propuesta.
- Dependencia de desarrollo: `pytest` instalado en un `.venv` de la raíz (ignorado por `.gitignore`); el TP no cambia sus `requirements.txt`.
- Habilita C-02 (infra de tests en `parcial/`) y C-19 (ajustes de `despliegue/`).


## Nota posterior a la implementación (2026-11-03)

Las copias `parcial/` y `despliegue/` se crearon y verificaron con `tools/snapshots.py` (resultado `OK`, 62 archivos cada una, 31 tests en verde). Después, a pedido del usuario, se eliminaron `tools/`, `tests/`, `pytest.ini`, `requirements-dev.txt` y el `.venv` de la raíz: eran andamiaje de verificación y no forman parte de la entrega. Por eso se quitó el requisito "Verificación ejecutable" de la spec. Quedan las dos copias, `.gitattributes` y el tag local `tp-cap1a4-entregado`.
