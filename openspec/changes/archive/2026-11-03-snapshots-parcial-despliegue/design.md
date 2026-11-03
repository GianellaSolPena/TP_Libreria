# Design

## Context

- Motivación: ver `proposal.md` - Why. Requisitos: `specs/tp-snapshots/spec.md`.
- El TP entregado es el commit `e337710e3b411c7b84e282a264280ad9b577c1f8`. `git ls-tree -r e337710` da 64 archivos; los 62 del alcance son los de `app/`, `migrations/`, `test/` (incluye 4 PNG en `test/C-07_CapturasPantalla/`, nombres con espacios) + `alembic.ini`, `requirements.txt`, `env.example`, `README.md`. Fuera: `PLAN.md`, `TP_Cap1a4_Consigna.pdf`, `.gitignore`.
- Estado observado del working tree (no lo genera este change): `.gitignore` modificado (+`.atl/`) y `TP_Cap1a4_Consigna.pdf` borrado. Los archivos del TP (`app/`, `migrations/`, `test/`, etc.) están limpios según `git status`.
- **Fin de línea (hallazgo clave)**: `core.autocrlf=true` y no hay `.gitattributes`. Los blobs de `e337710` ya contienen CRLF en varios archivos (mezcla CRLF/LF). Consecuencias medidas:
  - `git archive e337710` aplica la conversión de checkout y **agrega** CR: no da bytes iguales al blob.
  - `git -c core.autocrlf=false archive e337710` sí da bytes iguales al blob.
  - Los archivos de la raíz difieren byte a byte del blob (49 de 62) aunque `git status` diga limpio, por la conversión del checkout. `git hash-object` con autocrlf normaliza CRLF→LF y tampoco coincide con blobs que ya tienen CRLF.
- Python: `py` → Python 3.13 disponible; `python`/`python3` son el alias de la Microsoft Store (no sirven). `pytest` no está instalado.

## Goals / Non-Goals

**Goals:**
- Copias byte-idénticas a los blobs de `e337710` en `parcial/` y `despliegue/`, reproducibles con un solo comando.
- Verificación automática (pytest + CLI) de: lista exacta, contenido, artefactos prohibidos, raíz intacta, tag.
- Que la identidad byte a byte sobreviva a futuros commits/clones en Windows.

**Non-Goals:**
- Mover `main.py` (C-03), infra pytest+PostgreSQL en `parcial/` (C-02), Dockerfile/DEPLOY (C-19..C-21).
- Restaurar `TP_Cap1a4_Consigna.pdf` o revertir `.gitignore` de la raíz (cambios previos del usuario, fuera del alcance).
- Commit / push del tag (lo decide el usuario después del apply).

## Decisions

### D1. Copiar desde git con `git -c core.autocrlf=false archive e337710 -- <paths> | tar -x -C <destino>`
- Por qué: fuente = commit entregado, no el working tree (que podría tener cambios o conversiones); `autocrlf=false` garantiza bytes = blob; `archive` nunca trae `.git`, `.venv`, `__pycache__` ni `.env` (no están versionados).
- Implementación: la extracción la hace `tools/snapshots.py` en Python (`subprocess` → `git archive --format=tar`, lectura con `tarfile` de stdlib), así no depende de `tar` de Git Bash y funciona igual en PowerShell. Se rechaza si el destino ya existe y no está vacío (no pisa trabajo).
- Alternativas: `git show <commit>:<path>` archivo por archivo (más llamadas, mismo resultado; queda como fallback); `cp -r` del working tree (rechazado: CRLF convertidos y riesgo de arrastrar `__pycache__`/`.env`); `git worktree` (trae `.git` y deja metadata).

### D2. Lista de archivos derivada del commit, no hardcodeada
- `archivos_esperados()` = `git ls-tree -r --name-only e337710 -- app migrations test alembic.ini requirements.txt env.example README.md`. Los tests además fijan el conteo (62) y la presencia de rutas ancla (`app/main.py`, `migrations/versions/0002_agrega_genero.py`, un PNG) para detectar que el filtro de paths esté mal.

### D3. Verificación de snapshots por hash de blob sobre bytes crudos
- Para cada archivo: `sha1(b"blob <len>\0" + bytes)` comparado con el SHA de `git ls-tree -r e337710`. Puro stdlib, sin filtros de git, exacto. Reporta `faltantes`, `sobrantes`, `distintos`, `prohibidos` (recorrido recursivo buscando `.git`, `.venv`, `__pycache__`, `*.pyc`, `.env`, `.env.test`, `.pytest_cache`).
- Alternativa rechazada: `git hash-object`/`git diff --no-index` (aplican normalización de EOL → falsos negativos/positivos, ver Context).

### D4. `.gitattributes` en la raíz: `parcial/** -text` y `despliegue/** -text`
- Para que al commitear/clonar git no convierta EOL en las copias y la verificación byte a byte siga valiendo. No afecta a archivos de la raíz del TP. Es configuración del repo, no código del TP.
- Alternativa: verificar normalizando EOL (rechazada: menos estricta y los blobs ya mezclan CRLF/LF).

### D5. Raíz intacta verificada con la vista de git, no con bytes
- `git diff --quiet e337710 -- <paths TP + PLAN.md>` y `git status --porcelain --untracked-files=all -- <paths>` vacío. Bytes crudos no sirven en la raíz (checkout con autocrlf, ver Context).

### D6. Tests: pytest mínimo en `tests/` de la raíz, stdlib + `subprocess git`
- C-02 arma pytest+PostgreSQL **dentro de `parcial/`** para el código del parcial; esta suite es del repo (integridad de copias), no del TP, y debe correr desde la raíz, por eso vive en `tests/` (raíz) y no en `parcial/test/` ni en `test/` (que es del TP y no se toca).
- `pytest` se instala en `.venv` de la raíz (`py -m venv .venv`; `.venv/Scripts/python -m pip install pytest`), ya ignorado por `.gitignore`. Se agrega `requirements-dev.txt` en la raíz con `pytest` (no se toca `requirements.txt` del TP). Comando: `.venv/Scripts/python -m pytest tests -q`.
- Capas: **unitarias** sobre `tmp_path` (crear copia → verifica limpio; alterar/borrar/agregar archivo, crear `__pycache__`/`.env` → la verificación lo reporta; parametrizadas para triangular) y **de aceptación** sobre `parcial/`, `despliegue/`, raíz y tag reales.
- `pytest.ini`/`[tool.pytest]` mínimo en la raíz con `testpaths = tests` para que `pytest` en la raíz no recolecte `parcial/` (cuando C-02 agregue sus tests, se corren desde `parcial/`).

### D7. Vida útil de los tests de aceptación
- `despliegue/`: el chequeo estricto queda permanente; C-19 agrega una lista explícita de archivos permitidos extra/modificados (`Dockerfile`, `.dockerignore`, `DEPLOY.md`, `evidencia/`, `env.example`).
- `parcial/`: el chequeo estricto sólo vale como aceptación de C-01. El primer change que modifique `parcial/` (C-02) debe retirarlo o convertirlo (p. ej. sólo "deriva de `tp-cap1a4-entregado`"). Se deja anotado en el test.

### D8. Tag `tp-cap1a4-entregado` anotado y local
- `git tag -a tp-cap1a4-entregado e337710 -m "TP Cap 1-4 tal como se entregó"`. Idempotente: si existe y apunta a `e337710`, no se recrea; si apunta a otro commit, el comando falla. No se pushea en el apply.

## Risks / Trade-offs

- [Alguien copia a mano o con `git archive` sin `-c core.autocrlf=false`] → la verificación byte a byte falla de inmediato; el único camino documentado es `py tools/snapshots.py crear`.
- [`.gitattributes` con `-text` hace que diffs de `parcial/` muestren CRLF] → aceptable; preserva fidelidad. Si molesta, se puede relajar sólo para `parcial/` en C-02 retirando a la vez su test estricto.
- [pytest en la raíz recolecta `parcial/test/` en el futuro] → `testpaths = tests` + `norecursedirs` con `parcial despliegue`.
- [Nombres con espacios en PNG] → manejados por `tarfile`/`pathlib`, sin shell.

## Migration Plan

1. Crear tag; 2. `py tools/snapshots.py crear parcial` y `... crear despliegue`; 3. `py tools/snapshots.py verificar` → código 0; 4. pytest verde. Rollback: borrar `parcial/`, `despliegue/` (no versionados aún) y `git tag -d tp-cap1a4-entregado`.


## Nota posterior a la implementación (2026-11-03)

Las copias `parcial/` y `despliegue/` se crearon y verificaron con `tools/snapshots.py` (resultado `OK`, 62 archivos cada una, 31 tests en verde). Después, a pedido del usuario, se eliminaron `tools/`, `tests/`, `pytest.ini`, `requirements-dev.txt` y el `.venv` de la raíz: eran andamiaje de verificación y no forman parte de la entrega. Por eso se quitó el requisito "Verificación ejecutable" de la spec. Quedan las dos copias, `.gitattributes` y el tag local `tp-cap1a4-entregado`.
