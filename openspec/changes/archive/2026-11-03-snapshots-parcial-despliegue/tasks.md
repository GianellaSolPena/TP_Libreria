# Tasks

> Strict TDD: cada grupo arranca con tests en ROJO ejecutados, luego el mínimo código para VERDE, triangulación (>=2 casos por comportamiento) y refactor con tests verdes. Comando de tests: `.venv/Scripts/python -m pytest tests -q` desde la raíz. Usar `py` (no `python`/`python3`, que son el alias de la Store).

## 1. Entorno de pruebas del repo (sin tests propios: scaffolding)

- [x] 1.1 Crear `.venv` en la raíz con `py -m venv .venv`, agregar `requirements-dev.txt` (raíz) con `pytest` e instalarlo; verificar con `.venv/Scripts/python -m pytest --version`
- [x] 1.2 Agregar `pytest.ini` en la raíz con `testpaths = tests`, `pythonpath = .` y `norecursedirs = parcial despliegue .venv .git`; verificar que `git status --porcelain -- app migrations test alembic.ini requirements.txt env.example README.md PLAN.md` sigue vacío (la raíz del TP no se tocó)

## 2. Lista de archivos esperados

- [x] 2.1 RED: `tests/test_snapshots.py` con tests de `archivos_esperados()` de `tools/snapshots.py` (aún inexistente): 62 rutas; contiene `app/main.py`, `migrations/versions/0002_agrega_genero.py`, `test/C-07_CapturasPantalla/Captura de pantalla 2026-10-14 160726.png`, `README.md`; no contiene `PLAN.md`, `TP_Cap1a4_Consigna.pdf`, `.gitignore`. Ejecutar y ver que fallan
- [x] 2.2 GREEN/REFACTOR: implementar `tools/snapshots.py::archivos_esperados()` vía `git ls-tree -r e337710` filtrado por las rutas del alcance (D2); constante `COMMIT_TP = "e337710"`; tests verdes

## 3. Verificación de una copia (unitaria sobre tmp_path)

- [x] 3.1 RED: tests de `verificar_copia(destino)` usando una copia creada en `tmp_path` por `crear_copia(tmp_path / "x")`: copia fiel -> sin discrepancias; parametrizados: archivo alterado (`app/main.py`) -> `distintos`; archivo borrado -> `faltantes`; archivo extra -> `sobrantes`; `app/__pycache__/x.pyc`, `.env`, `.venv/`, `.pytest_cache/` -> `prohibidos`. Ejecutar y ver ROJO
- [x] 3.2 GREEN: implementar `crear_copia(destino)` con `git -c core.autocrlf=false archive --format=tar e337710 -- <paths>` + `tarfile` (D1; falla si destino existe y no está vacío) y `verificar_copia(destino)` por hash de blob sobre bytes crudos (D3); tests verdes
- [x] 3.3 TRIANGULATE: agregar casos: destino no vacío -> `crear_copia` lanza error sin escribir; verificación de un PNG con espacios en el nombre; archivo con CRLF del blob verificado byte a byte (el test documenta que `git archive` sin `autocrlf=false` lo rompería). Tests verdes; REFACTOR con tests verdes

## 4. Raíz intacta, tag y CLI

- [x] (simplificado a pedido del usuario) 4.1 RED: tests de `verificar_raiz()` (usa `git diff --quiet e337710 -- <paths>` + `git status --porcelain --untracked-files=all`, D5): sobre el repo real devuelve sin discrepancias; triangular con un repo git temporal en `tmp_path` (commit inicial, luego modificar un archivo y agregar uno nuevo bajo `app/`) -> reporta ambos (parametrizar la ruta del repo y el commit). Ejecutar ROJO, implementar, VERDE
- [x] (simplificado a pedido del usuario) 4.2 RED: test de `verificar_tag()` -> `tp-cap1a4-entregado^{commit}` == `e337710e3b411c7b84e282a264280ad9b577c1f8` (falla hasta crear el tag); test de CLI `py tools/snapshots.py verificar` con `subprocess`: código 0 en estado correcto y != 0 con mensaje sobre una raíz/copia alterada en `tmp_path`. Ejecutar ROJO
- [x] 4.3 GREEN: implementar `main()` con subcomandos `crear <destino>` y `verificar` (snapshots `parcial/` y `despliegue/`, raíz y tag; imprime cada discrepancia); crear el tag anotado local `git tag -a tp-cap1a4-entregado e337710 -m "TP Cap 1-4 tal como se entregó"` (D8, sin push); tests de 4.1-4.2 verdes salvo los de aceptación de grupo 5

## 5. Crear los snapshots reales (checkpoint MEDIO)

- [x] 5.1 RED: tests de aceptación `test_parcial_identico_a_e337710` y `test_despliegue_identico_a_e337710` (llaman `verificar_copia` sobre las carpetas reales, sin discrepancias) + `test_raiz_intacta`; el de `parcial/` con comentario "retirar/convertir en C-02 (D7)". Ejecutar: ROJO porque no existen
- [x] 5.2 Agregar `.gitattributes` en la raíz con `parcial/** -text` y `despliegue/** -text` (D4); verificar con `git check-attr text -- parcial/app/main.py` -> `unset`
- [x] 5.3 GREEN: `py tools/snapshots.py crear parcial` y `py tools/snapshots.py crear despliegue`; luego `py tools/snapshots.py verificar` -> código 0 y suite completa verde. CHECKPOINT: mostrar al usuario el árbol de `parcial/` y `despliegue/` (62 archivos c/u) y la salida de la verificación antes de seguir

## 6. Documentación de la regla de layout

- [x] 6.1 (ajustada: ver nota final) Agregar en `CLAUDE.md` y `AGENTS.md` (idénticos) bajo "Layout del repo" una línea: snapshots creados con `py tools/snapshots.py crear`, verificados con `py tools/snapshots.py verificar` / `pytest tests`; `despliegue/` sólo recibe Docker/VPS (C-19..C-21). Verificar con `diff CLAUDE.md AGENTS.md` sin diferencias y que el comando documentado corre tal cual (código 0)
- [x] 6.2 Marcar `Estado: [x]` de C-01 en `CHANGES.md` y verificar que el resto del archivo no cambió (`git diff CHANGES.md` sólo esa línea, si está versionado; si no, revisión visual)

## Workflow follow-up

- Revisar con el usuario si commitear `parcial/`, `despliegue/`, `tools/`, `tests/`, `.gitattributes`, `pytest.ini`, `requirements-dev.txt` y si pushear el tag.
- Archivar el change con `/opsx:archive` una vez revisado.


## Nota posterior a la implementación (2026-11-03)

Las copias `parcial/` y `despliegue/` se crearon y verificaron con `tools/snapshots.py` (resultado `OK`, 62 archivos cada una, 31 tests en verde). Después, a pedido del usuario, se eliminaron `tools/`, `tests/`, `pytest.ini`, `requirements-dev.txt` y el `.venv` de la raíz: eran andamiaje de verificación y no forman parte de la entrega. Por eso se quitó el requisito "Verificación ejecutable" de la spec. Quedan las dos copias, `.gitattributes` y el tag local `tp-cap1a4-entregado`.

- [x] 6.1 Línea de layout agregada en CLAUDE.md/AGENTS.md (sin referencia a tools/, que se eliminó)
- [x] 6.2 C-01 marcado [x] en CHANGES.md
