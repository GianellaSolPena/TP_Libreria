# Design

## Context

Ver proposal.md (Why) y la spec `empaquetado-entrega`. Estado observado al proponer (2026-11-06):

- `HEAD` = `3e1165d`; árbol limpio. `parcial/` y `despliegue/` suman 175 archivos versionados; con la captura `parcial/evidencia/C-14_captura_psql.png` (a commitear antes del zip) serán 176.
- En disco, fuera del control de versiones, hay `parcial/.env` (con valores reales locales), `parcial/**/__pycache__/` y `despliegue/.venv/`: todo ignorado por `.gitignore`, pero cualquier método que comprima la carpeta "tal cual" los arrastraría.
- `.gitattributes` marca `parcial/** -text` y `despliegue/** -text`: git no convierte finales de línea; el blob versionado = archivo en disco. Hay 12 archivos CRLF (módulos `autores`/`generos` y la 0003, heredados del TP) y 4 evidencias "mixed" (respuestas HTTP con cabeceras CRLF). Se entregan tal cual: Python, Alembic y Docker los aceptan, y así fueron probados.
- Decisiones del usuario (2026-11-06): nombre del zip `Parcial_Cap1a6_Las_chicas.zip`, destino `C:\Users\agusf\Desktop\Entrega_Parcial\` y evidencia de C-14 = texto + captura.
- Nombres de archivo: sólo ASCII; hay espacios en `despliegue/test/C-07_CapturasPantalla/Captura de pantalla ….png`.
- Herramientas: Python 3.13.5 del sistema (`python`/`py`; la consigna pide ≥ 3.12; C-10 usó el mismo intérprete para `despliegue/.venv`), GNU tar (no lee zip), `C:\Windows\System32\tar.exe` (bsdtar, sí lee/escribe zip), Docker 29.8, sin `zip`/`7z`.
- Búsqueda preliminar sobre los archivos versionados: sin `PRIVATE KEY`, sin la ruta/nombre de la clave SSH del VPS, sin rutas `C:\Users`; la única IP pública es la del VPS en `DEPLOY.md`/D-03/D-04 (URL declarada, exigida por la consigna); las demás son `127.0.0.1`, `0.0.0.0` y `172.x` internas de Docker.
- `despliegue/DEPLOY.md` enlaza `evidencia/local/` (IN-06, IN-07 y la prueba local de C-10).

## Goals / Non-Goals

**Goals:**
- Zip reproducible desde un commit, con exactamente los archivos versionados de `parcial/` y `despliegue/`.
- Verificación automática (listado, exclusiones, secretos, fidelidad) + verificación funcional desde el zip extraído.
- Cero cambios en `parcial/`, `despliegue/` y en la raíz versionada (salvo planificación).

**Non-Goals:**
- Subir el zip al campus (lo sube una integrante; es una entrega formal).
- Corregir archivos del proyecto si la verificación encuentra algo: se frena y se reporta (sería otro change o un ajuste aprobado).
- Revisar el historial de git (Q-15: el zip no lleva `.git`).
- Volver a correr los casos C o D completos (ya tienen evidencia en C-09 y C-11).

## Decisions

### D-01 Armar el zip con `git archive` desde `HEAD`
`git archive --format=zip --output="<destino>/Parcial_Cap1a6_Las_chicas.zip" HEAD parcial despliegue`

- Incluye sólo archivos versionados: `.env`, `.venv`, `__pycache__`, `*.pyc` quedan fuera **por construcción**, no por una lista de exclusiones que se pueda olvidar.
- Entradas con `/`, prefijos `parcial/` y `despliegue/`, bytes exactos del blob (con `-text` no hay conversión de EOL; no hay `export-subst`/`export-ignore` en `.gitattributes`).
- Reproducible y trazable: el zip corresponde a un commit concreto (se anota el hash en el resumen).
- Precondición: `git status --porcelain -- parcial despliegue` vacío (lo no commiteado no entraría).
- Alternativas descartadas: `Compress-Archive` (PowerShell 5.1 escribe `\` en las rutas y no excluye patrones), `tar.exe -a -cf` (correcto en separadores, pero requiere listar exclusiones a mano y arrastraría `.env` si se olvida una), copiar a una carpeta de staging y comprimir (más pasos, mismo riesgo). Python `zipfile` sólo se usa para **leer**/extraer.

### D-02 Destino fuera del repo
`C:\Users\agusf\Desktop\Entrega_Parcial\Parcial_Cap1a6_Las_chicas.zip`. Escribir en `dist/` dentro del repo obligaría a tocar `.gitignore` y contradice la spec `tp-snapshots` (la raíz sólo tiene planificación). Si el directorio ya existe con un zip previo, se sobrescribe sólo tras confirmarlo.

### D-03 Nombre sin espacio
Decisión del usuario: `Parcial_Cap1a6_Las_chicas.zip` (guion bajo, sin espacio). Evita problemas de citado en la línea de comandos, en scripts de corrección y en URL (`%20`). El nombre del grupo en prosa sigue siendo "Las chicas".

### D-07 Evidencia de C-14: texto + captura (precondición del zip)
`parcial/evidencia/C-14_solo_agregado.txt` se conserva y se suma `parcial/evidencia/C-14_captura_psql.png`, una captura de la salida de psql tomada por el usuario (la consigna pide "captura" para C-14). El usuario commitea, en un commit aparte **antes** de armar el zip, la captura y el cambio en `parcial/README.md` (que hoy dice que `evidencia/` tiene `C-14_solo_agregado.txt` y debe mencionar también el `.png`). Este change no edita `parcial/`: sólo verifica que el `.png` exista, esté commiteado y entre al zip (con él, 176 archivos). Sin ese commit, el zip no se arma.

### D-04 `despliegue/evidencia/local/` se incluye
Está versionada y `DEPLOY.md` la enlaza; no contiene secretos (revisado en la búsqueda). Quitarla rompería enlaces y obligaría a editar `DEPLOY.md` (regla 9).

### D-05 Verificación en tres capas, sobre el zip extraído
Todo en `$SCRATCH/c12/` (scratchpad de la sesión, fuera del repo); cada extracción en un directorio nuevo y vacío.

1. **Estructural** (Python `-I` con scripts en `$SCRATCH/c12/tools/`, nunca dentro del árbol extraído):
   - listado `python -I -m zipfile -l`; además `C:\Windows\System32\tar.exe -tf` para confirmar que un lector distinto lo abre;
   - raíz sólo `parcial/` y `despliegue/`, ningún `\`, ninguna entrada excluida (`.git/`, `.venv/`, `__pycache__/`, `.pyc`, `/.env`, `.pytest_cache`), archivos obligatorios presentes;
   - fidelidad: para cada archivo extraído `git hash-object <archivo>` == blob de `git ls-tree -r HEAD -- parcial despliegue`, y mismo conjunto de rutas (176);
   - enlaces relativos de `DEPLOY.md` y `README.md` resueltos dentro del árbol extraído.
2. **Secretos** (`grep -rnI -E` sobre el árbol extraído): asignaciones no vacías de `POSTGRES_PASSWORD=`/`JWT_SECRET_KEY=`/`DATABASE_URL=` con credenciales distintas del marcador `usuario:password@<host>`; `PRIVATE KEY`, `ssh -i`, `IdentitiesOnly`, `agus-grupo1`, `/VPS/`, `C:\Users`, `/c/Users`; inventario de IPv4 contra la lista permitida. Además, los **valores** de `parcial/.env` local se buscan con `grep -rFc -f <archivo temporal de valores>` imprimiendo sólo el conteo (nunca el valor); el archivo temporal se borra al terminar. La contraseña de la base del VPS no está en esta máquina: se cubre porque nunca se escribió en el repo (C-11) y por las búsquedas de patrón.
3. **Funcional**:
   - Postgres descartable: `docker network create c12-net`; `docker run -d --name c12-pg --network c12-net -p 127.0.0.1:55432:5432 -e POSTGRES_USER=libreria -e POSTGRES_DB=libreria -e POSTGRES_PASSWORD="$PW" postgres:16-alpine`, con `PW` y la clave JWT generadas con `python -c "import secrets; print(secrets.token_urlsafe(24))"` y guardadas sólo en `$SCRATCH/c12/` (nunca en el repo ni en el chat).
   - `parcial/`: `.env` en el árbol extraído a partir de `env.example` (`POSTGRES_PORT=55432`, `PW`, clave JWT); `python -m venv .venv`, `.venv/Scripts/python -m pip install -r requirements.txt`, `alembic upgrade head`, `alembic current` (0004), `python seed.py`, `uvicorn main:app --port 18000` en segundo plano, `curl /health/ready` → 200 y `curl /libros/` → 200; se detiene uvicorn.
   - `despliegue/`: base aparte `libreria_tp` en el mismo `c12-pg`; `docker build -t c12-libreria-check <extraído>/despliegue`; `docker run -d --name c12-app --network c12-net -e DATABASE_URL=postgresql+asyncpg://libreria:$PW@c12-pg:5432/libreria_tp -e SQL_ECHO=false c12-libreria-check`; esperar `healthy` y `docker exec c12-app wget -qO- http://127.0.0.1:8000/health/ready`; `docker logs` sin traza de error.
   - Limpieza: `docker rm -f c12-app c12-pg`, `docker network rm c12-net`, `docker rmi c12-libreria-check`, borrar `$SCRATCH/c12/` (incluye los `.env` de prueba). `postgres:16-alpine` se conserva si ya estaba.

### D-06 Gate de aprobación (Governance ALTO)
Antes de dar el zip por final: se muestra al usuario el listado completo (176 archivos agrupados por carpeta), el hash del commit, tamaño y SHA-256 del zip y el resumen de las tres capas. El zip sólo se declara listo con su "sí" explícito. Si después se commitea algo en `parcial/` o `despliegue/`, el zip se rearma y se repite la verificación.

## Risks / Trade-offs

- [Cambios sin commitear no entran al zip] → precondición de árbol limpio; se informa el hash usado.
- [Falso negativo en la búsqueda de secretos (p. ej. la contraseña del VPS con un formato no previsto)] → patrones + valores locales + revisión humana del listado; la contraseña del VPS nunca se escribió en el repo.
- [La captura de C-14 (`.png`) la toma el usuario y puede faltar o no estar commiteada] → precondición explícita en tasks 1.2 y 1.3: sin el `.png` commiteado (y el README actualizado) no se arma el zip.
- [Python 3.13 local vs. 3.12 de la consigna] → los requisitos son `>=`; `parcial/` ya se probó con 3.13; `despliegue/` corre en `python:3.12-alpine` dentro de Docker.
- [EOL CRLF/mixed en algunos archivos] → son los bytes entregados del TP; no afectan ejecución; no se normalizan (regla 9 y fidelidad).
- [Puertos 55432/18000 ocupados] → se eligen otros libres; sólo cambian los comandos de prueba.
- [El build de Docker necesita red para PyPI] → si falla por red, se reintenta; no cambia el contenido del zip.

## Migration Plan

No aplica (no hay despliegue ni migración). Rollback: borrar el zip y los recursos `c12-*`; el repo no cambia salvo planificación.

## Open Questions

(ninguna: nombre, destino y evidencia de C-14 quedaron decididos por el usuario el 2026-11-06).
