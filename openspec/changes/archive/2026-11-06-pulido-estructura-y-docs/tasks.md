# Tasks

> Sin pytest (DD-01): cada tarea se verifica con `grep`, `ls`, `git diff` o, en los opcionales, con `.http` contra uvicorn. Governance BAJO. No se toca la lógica de `despliegue/`, ni el zip entregado, ni el VPS, ni `CHANGES.md`; no se commitea sin pedido.

## 1. Decisión de estructura: `dependencies.py` (D1)

- [x] 1.1 (confirmado por el usuario: D1 se queda en `app/core/`) **CHECKPOINT — confirmación del usuario**: presentar D1 (dejar `parcial/app/core/dependencies.py` donde está, por la fila literal de la p. 8 del PDF). Si el usuario pide moverlo, detenerse y replantear el change con `/opsx:update`. Verificación: respuesta anotada aquí
- [x] 1.2 Agregar **DD-11 — `dependencies.py` en `app/core/` importando de `usuarios`** en `knowledge-base/09_decisiones_y_supuestos.md`, después de DD-10, con: decisión, fila literal del PDF (p. 8), por qué la dependencia `core → modules.usuarios` es inevitable (roles vigentes de `asignacion_rol`, RN-04), por qué las capas siguen respetadas (dependencia nivel router, ningún servicio recibe sesión) y la nota sobre el tipo `SesionActual` usado en `ventas/service.py`. Verificación: `grep -n "^### DD-11" knowledge-base/09_decisiones_y_supuestos.md` devuelve una línea
- [x] 1.3 En `knowledge-base/08_arquitectura_propuesta.md` §Estructura, reemplazar «hoy vive en app/main.py: ver Q-03» por la ubicación actual (`parcial/main.py`, DD-08) y agregar en la línea de `dependencies.py` la referencia a DD-11. Verificación: `grep -n "hoy vive en app/main.py" knowledge-base/08_arquitectura_propuesta.md` vacío
- [x] 1.4 Comprobar que no cambió código: `git diff --stat -- parcial/app` vacío; `grep -rn "AsyncSession" parcial/app/modules/*/service.py` vacío (capas)

## 2. `despliegue/DEPLOY.md`: comandos partidos (D2)

- [x] 2.1 Guardar en el scratchpad la versión actual de cada comando a partir (l. ~19, ~42, ~43, ~107, ~127, ~137), con espacios normalizados
- [x] 2.2 Partir esos comandos con `\` al final de línea y continuaciones con dos espacios de sangría, en los límites de opción o de la tubería; el `docker exec … sh -c '…'` se parte antes de `sh -c`, nunca dentro de las comillas. Sólo cambia el texto de `DEPLOY.md`
- [x] 2.3 Verificación: `awk '/^ *```/{f=!f;next} f && length>100' despliegue/DEPLOY.md` vacío; al unir las continuaciones (`sed ':a;/\\$/{N;s/\\\n *//;ba}'`) y normalizar espacios, cada comando es idéntico al guardado en 2.1; `git diff --stat -- despliegue` sólo lista `DEPLOY.md`

## 3. Carpeta `app/` suelta en la raíz (D3)

- [x] 3.1 (2026-11-06: `ls app` -> no existe; nada que borrar) Al proponer (2026-11-06) `app/` **no existe** en la raíz. Volver a comprobar con `ls -a` en la raíz y `git status --short --ignored`. Si sigue sin existir, anotar aquí «no existe, nada que borrar» y cerrar la tarea
- [x] 3.2 (no aplica: `app/` no existe, nada que borrar) Sólo si reapareció: `find app -type f | grep -v "/__pycache__/"` debe estar vacío; entonces borrar `app/`. Si lista algún archivo, **no borrar**: detenerse y consultar al usuario. Verificación: `ls app` → no existe; `git status` sin cambios versionados

## 4. `parcial/README.md` (D4)

- [x] 4.1 Agregar a la tabla de «Casos de prueba» la fila de `RN-15_caracter_nulo.http` marcada como extra (U+0000 en cuerpos y en `?titulo=` → 422, nunca 500) y ajustar la línea de `test/` en «Estructura» (hoy dice «un .http por caso C-01 a C-16 (salvo C-14) y solo_agregado.sql»). Verificación: `grep -n "RN-15_caracter_nulo" parcial/README.md` con al menos una coincidencia
- [x] 4.2 **Depende de F-02 `evidencia-casos-reproducible` aplicado**: con `ls parcial/evidencia/` (nombres reales, no inventados), nombrar cada archivo nuevo en la línea de `evidencia/` de «Estructura» y en la columna «Evidencia» de la tabla (o en un párrafo para la evidencia de migraciones `upgrade → downgrade → upgrade`). Si F-02 todavía no está aplicado, dejar esta tarea abierta y avisar
- [x] 4.3 Verificación de coherencia (spec `guia-puesta-en-marcha`): cada archivo de `ls parcial/test parcial/evidencia` aparece en el README y cada archivo de `test/` o `evidencia/` nombrado en el README existe (`grep -o "evidencia/[^ \`)|]*" parcial/README.md` contra `ls`)

## 5. Cierre

- [x] 5.1 Revisión final: `git status` sólo muestra `knowledge-base/08…`, `knowledge-base/09…`, `despliegue/DEPLOY.md`, `parcial/README.md` y los artefactos del change (más lo que agreguen los opcionales si se hacen); casos `.http` sin cambios de código no requieren nueva corrida
- [x] 5.2 Recordar que `CHANGES.md` (F-03 `[x]`) se actualiza al archivar, coordinado con F-02

## 6. Opcionales (no los pide el PDF; NO son condición para cerrar el change)

> Sólo si el usuario los pide explícitamente. Cada uno se verifica con `python seed.py` + uvicorn (base a confirmar con el usuario: `seed.py` hace `TRUNCATE`).

- [x] 6.1 (opcional) `parcial/test/RN-03_rol_ya_vigente.http`: como ADMIN, `POST /usuarios/{id}/roles` con un rol que el usuario ya tiene vigente → 409 «El usuario ya tiene ese rol vigente», respuesta esperada en comentario; fila extra en la tabla del README
- [ ] 6.2 (DESCARTADA por decisión del usuario, no se hizo) (opcional) `parcial/test/token_vencido.http`: condición `ACCESS_TOKEN_EXPIRE_SECONDS=5` al arrancar uvicorn; login, esperar más de 5 s, `GET /auth/yo` con la misma cookie → 401; fila extra en el README con la condición
- [ ] 6.3 (DESCARTADA por decisión del usuario, no se hizo) (opcional) Escapar `%`, `_` y `\` del parámetro `titulo` en `parcial/app/modules/libros/repository.py` (`ilike(..., escape="\\")`, sigue siendo parámetro ligado); agregar a C-16 o a un `.http` extra `GET /libros?titulo=%25` → 200 total 0 y `GET /libros?titulo=_` → 200 total 0. Verificación: C-16 completo sin regresiones
