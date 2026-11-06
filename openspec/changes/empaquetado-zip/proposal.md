# Proposal

## Why

El parcial se entrega como un único `.zip` por grupo, `Parcial_Cap1a6_<NombreDelGrupo>.zip`, con dos carpetas (`parcial/` y `despliegue/`). Las reglas duras de la consigna dicen que un proyecto que no levanta, que no crea su esquema con `alembic upgrade head` sobre una base vacía o que contiene credenciales reales en el zip **no se corrige**. C-09 (parcial completo) y C-11 (despliegue en línea) ya están cerrados: falta armar el zip de forma reproducible, comprobar que no filtra secretos y que el proyecto levanta desde el zip extraído, sin tocar el código.

## What Changes

- Se arma `Parcial_Cap1a6_Las_chicas.zip` (Q-01: grupo "Las chicas"; en el nombre del archivo el espacio se reemplaza por guion bajo) **fuera del repo**, sólo con `parcial/` y `despliegue/` tal como están versionados en `HEAD` (nada de la raíz, `knowledge-base/`, `openspec/`, `.claude/`, `.atl/`, `CHANGES.md`, la consigna, etc.).
- El zip no contiene `.git` (Q-15 resuelta: sin `.git`), `.venv`, `__pycache__`, `*.pyc` ni `.env` en ningún nivel; los finales de línea y bytes de cada archivo son los del commit (`.gitattributes` `-text`).
- La evidencia de C-14 es doble: el texto `parcial/evidencia/C-14_solo_agregado.txt` **y** una captura de pantalla de la salida de psql, `parcial/evidencia/C-14_captura_psql.png`, que toma el usuario. Esa captura y el ajuste del `README.md` de `parcial/` (que debe mencionar el `.png` junto al `.txt`) se commitean en un commit aparte **antes** de armar el zip; este change no edita `parcial/`.
- `despliegue/evidencia/local/` **se incluye** porque `DEPLOY.md` la enlaza (evidencia de la prueba local de C-10, IN-06 e IN-07); quitarla dejaría enlaces rotos.
- Verificación antes de entregar: listado de entradas revisado y aprobado por el usuario, búsqueda de secretos sobre el contenido extraído, comparación byte a byte contra `HEAD`, y puesta en marcha desde el zip extraído (`venv`, `pip install`, `alembic upgrade head`, `python seed.py`, `/health/ready`) contra un PostgreSQL 16 descartable; `docker build` de `despliegue/` desde el zip extraído.
- Planificación: Q-15 queda resuelta en `knowledge-base/10_preguntas_abiertas.md`; Q-13 (fecha límite en el campus) es sólo informativa. Al archivar se marca C-12 `[x]` en `CHANGES.md` y en `CLAUDE.md`/`AGENTS.md`.
- **Fuera de alcance**: modificar `parcial/` o `despliegue/` desde este change (regla 9; la captura y el README de `parcial/` los aporta el usuario en su commit previo), tocar el VPS, subir el zip al campus (lo hace un integrante), commitear o pushear sin pedido explícito (regla 11).

## Capabilities

### New Capabilities
- `empaquetado-entrega`: contenido, nombre, exclusiones, ausencia de secretos y verificabilidad (levanta desde cero) del `.zip` de entrega del parcial.

### Modified Capabilities
(ninguna)

## Impact

- **Archivos del repo**: ninguno de `parcial/` ni `despliegue/` por parte de este change (precondición: el commit previo del usuario con la captura y el README); sólo planificación (`knowledge-base/10_preguntas_abiertas.md`, `knowledge-base/12_entregables_del_parcial.md`, `CHANGES.md`, `CLAUDE.md`/`AGENTS.md`) y los artefactos de este change.
- **Fuera del repo**: el zip en `C:\Users\agusf\Desktop\Entrega_Parcial\` (no se versiona, no ensucia la raíz del repo — spec `tp-snapshots`) y un directorio descartable en el scratchpad para extraerlo y probarlo.
- **Recursos locales temporales**: contenedor `postgres:16-alpine`, red e imagen Docker de prueba con nombres `c12-*`, borrados al terminar.
- **Governance ALTO** (filtrado de credenciales): el usuario aprueba el listado del zip y el zip final.
