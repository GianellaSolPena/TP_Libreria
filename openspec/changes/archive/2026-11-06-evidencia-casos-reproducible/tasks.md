# Tasks

> Sin pytest (DD-01) y **sin código**: sólo se escriben archivos en `parcial/evidencia/`. Comandos desde `parcial/` en Git Bash; el intérprete es siempre `.venv/Scripts/python.exe` (`python` a secas es el alias de Microsoft Store). Governance BAJO; los **CHECKPOINT** se detienen y reportan. No se toca `parcial/app/`, `main.py`, `seed.py`, `migrations/`, `parcial/test/`, `.env`, `despliegue/`, el contenedor `libreria-pg`, los contenedores `turnos-odontologia-*` ni el zip; no se edita `CHANGES.md` hasta 6.4; no se commitea sin pedido.

## 1. Prerrequisitos y entorno

- [x] 1.1 Verificar herramientas: `.venv/Scripts/python.exe --version` (3.12 o superior; hoy 3.13.15), `.venv/Scripts/python.exe -c "import fastapi, sqlalchemy, asyncpg, alembic, httpx"`, `docker info --format '{{.ServerVersion}}'`, `docker image inspect postgres:16-alpine --format '{{.Id}}'`. Verificación: versiones anotadas aquí; si algo falta, detenerse
- [x] 1.2 Verificar puertos libres: `127.0.0.1:55432` y `8001` sin uso (`netstat -ano | grep -E ":55432|:8001"` vacío) y que no exista un contenedor `libreria-f02`. Verificación: salida vacía anotada
- [x] 1.3 Resolver con el usuario las Open Questions del design (Q-A ejecutor, Q-B C-14, Q-C alcance, Q-D puertos) si no fueron respondidas al aprobar el plan; anotar las respuestas aquí y ajustar las tareas siguientes

## 2. Contenedor descartable y destino seguro (D1, D2)

- [x] 2.1 Generar en el scratchpad de la sesión un archivo de entorno (fuera del repo) con `POSTGRES_PASSWORD` y `JWT_SECRET_KEY` aleatorias (`secrets.token_urlsafe`) y el resto de las variables de D2 (`POSTGRES_HOST=127.0.0.1`, `POSTGRES_PORT=55432`, `POSTGRES_USER=libreria`, `POSTGRES_DB=libreria`, `SQL_ECHO=false`, `DB_POOL_SIZE=5`, `ACCESS_TOKEN_EXPIRE_SECONDS=1800`, `BCRYPT_ROUNDS=12`, `COOKIE_SECURE=false`). Verificación: `git status --short` no muestra archivos nuevos fuera de `openspec/changes/evidencia-casos-reproducible/`
- [x] 2.2 `docker run -d --rm --name libreria-f02 -e POSTGRES_USER=libreria -e POSTGRES_DB=libreria -e POSTGRES_PASSWORD=... -p 127.0.0.1:55432:5432 postgres:16-alpine` y esperar a `docker exec libreria-f02 pg_isready -U libreria`. Verificación: `docker exec libreria-f02 psql -U libreria -d libreria -tAc "select version()"` empieza con `PostgreSQL 16.` y `\dt` no muestra tablas
- [x] 2.3 **CHECKPOINT — destino**: con las variables exportadas, `.venv/Scripts/python.exe -c "from app.core.config import get_settings as g; s=g(); print(s.POSTGRES_HOST, s.POSTGRES_PORT, s.POSTGRES_DB)"` imprime `127.0.0.1 55432 libreria`. Si muestra otro host/puerto, abortar (no correr `alembic` ni `seed.py`) y aplicar la alternativa de D2

## 3. Ciclo de migraciones (D6)

- [x] 3.1 Sobre la base vacía: `alembic upgrade head`, estado; `alembic downgrade base`, estado; `alembic upgrade head`, estado (estado = `\dt`, `select version_num from alembic_version`, `select count(*) from pg_proc where proname='movimiento_stock_solo_agregado'`), capturando stdout+stderr y código de salida de cada comando. Verificación: tres códigos 0; tras el downgrade sólo `alembic_version` (sin filas) y función ausente; estado final igual al del primer upgrade
- [x] 3.2 Escribir `parcial/evidencia/migraciones_ida_y_vuelta.txt` con el encabezado de D6 y la salida de 3.1. Verificación: contiene las líneas `Running upgrade` (0001→0004), `Running downgrade` (0004→0001) y las del segundo upgrade; ninguna contraseña

## 4. Ejecutor y servidor (D3, D4, D5)

- [x] 4.1 Escribir en el scratchpad el ejecutor de D4 (parseo del `.http` sin modificarlo, sustitución de `host` por `http://localhost:8001`, `Set-Cookie` y `response.body.$.campo` resueltos, salida por petición, JWT reemplazado por `<jwt>`). Verificación: no queda ningún archivo nuevo en el repo fuera de `parcial/evidencia/` y del change
- [x] 4.2 `seed.py` + uvicorn de prueba: `.venv/Scripts/python.exe seed.py`; luego `.venv/Scripts/python.exe -m uvicorn main:app --port 8001` en segundo plano con stdout+stderr a un log del scratchpad. Verificación: `curl -s http://localhost:8001/health/ready` → 200 y `curl -s "http://localhost:8001/libros?size=2"` → `total` 5, `pages` 3
- [x] 4.3 Prueba del ejecutor sobre `test/C-01_parametro_no_entero.http` (sólo lectura): comparar cada respuesta con su comentario y con un `curl` equivalente de una petición. Verificación: todas coinciden; si alguna petición se parsea mal, corregir el ejecutor antes de seguir

## 5. Corridas de los casos que escriben datos

> Para cada archivo: `.venv/Scripts/python.exe seed.py` justo antes; correr el `.http` completo con el ejecutor; ejecutar cada consulta psql comentada del final con `docker exec -i libreria-f02 psql -U libreria -d libreria -c "..."`; revisar petición por petición contra su `# Esperado:` y escribir `parcial/evidencia/C-NN_corrida.txt` (D6). Ante cualquier «NO coincide»: **CHECKPOINT** (D8), detenerse y reportar.

- [x] 5.1 C-02 (`C-02_registro_correo_repetido.http`): 201; los dos 409 con mensaje propio; psql sin filas sueltas. Verificación: `C-02_corrida.txt` todo coincide
- [x] 5.2 C-05 (`C-05_limite_intentos.http`), sin pausas entre peticiones: sexto intento 429 con `Retry-After`; psql con los cinco fallos en `intento_acceso`. Verificación: `C-05_corrida.txt` todo coincide
- [x] 5.3 C-07 (`C-07_revocar_rol_sesion_abierta.http`): 403 con la misma cookie tras revocar, `/auth/yo` con la diferencia, 422 en los vencimientos inválidos; psql con la fila revocada. Verificación: `C-07_corrida.txt` todo coincide
- [x] 5.4 C-08 (`C-08_autoproteccion_admin.http`): 409 al revocarse el propio ADMIN. Verificación: `C-08_corrida.txt` todo coincide
- [x] 5.5 C-10 (`C-10_venta_valida.http`): 201 con precios copiados y total 77000.00, stock y movimientos; psql `stock == SUM(movimientos)`; esperar ≥ 1 s y copiar del log de uvicorn el fragmento desde `"POST /ventas HTTP/1.1" 201` hasta «Comprobante de la venta N enviado al cliente» (N = id creado). Verificación: `C-10_corrida.txt` todo coincide, la petición con `{{ventaValida.response.body.$.id}}` quedó resuelta y el aviso está después de la línea de la respuesta
- [x] 5.6 C-11 (`C-11_venta_sin_stock.http`): 409; Rayuela sigue en 10; psql sin venta nueva y `stock == SUM(movimientos)` en los cinco libros. Verificación: `C-11_corrida.txt` todo coincide
- [x] 5.7 C-12 (`C-12_venta_inexistentes_o_baja.http`): 409 en los tres; psql sin escrituras. Verificación: `C-12_corrida.txt` todo coincide
- [x] 5.8 C-13 (`C-13_reponer_baja_reuso_isbn.http`): reponer 200, baja 204, fuera del catálogo, alta con mismo ISBN 201, segundo vigente 409, venta vieja con «Ficciones». Verificación: `C-13_corrida.txt` todo coincide
- [x] 5.9 C-16 (`C-16_busqueda_paginacion_patch.http`): búsqueda `' OR '1'='1` total 0, paginación y 422, PATCH parciales y PATCH con `stock` 422. Verificación: `C-16_corrida.txt` todo coincide
- [x] 5.10 C-15 crudo: detener uvicorn, reiniciarlo con `SQL_ECHO=true` y un log nuevo; `seed.py` antes; correr `C-15_detalle_consultas_fijas.http`; reemplazar `parcial/evidencia/C-15_consultas_detalle_venta.txt` con el encabezado + el fragmento crudo del log (del login al segundo `GET /ventas/... 200`, sin recortes) + anotación final del conteo. Verificación: ninguna línea termina en `[...]`; 4 SELECT para la venta de 2 renglones y 4 para la de 4
- [x] 5.11 (Sólo si Q-C = sí) Corridas de C-01, C-03, C-04, C-06, C-09 y RN-15 con el mismo procedimiento

## 6. C-14, limpieza y cierre

- [x] 6.1 (Según Q-B) `seed.py`, luego regenerar `C-14_solo_agregado.txt` con el procedimiento de D7 sobre PostgreSQL 16, conservando el formato del archivo actual. Verificación: 7 movimientos antes y después, los dos errores del disparador, encabezado con PostgreSQL 16
- [x] 6.2 **Paso opcional del usuario**: con el contenedor aún arriba y sembrado, pasarle al usuario el comando de 6.1 para que rehaga `C-14_captura_psql.png` (7 movimientos). Esperar su respuesta; si no la rehace, dejarlo anotado aquí. Verificación: png y txt muestran los mismos conteos, o constancia de que el usuario lo omitió
- [x] 6.3 Limpieza y control: detener uvicorn; `docker stop libreria-f02` (se borra por `--rm`); `docker ps -a --filter name=libreria-f02` vacío; `libreria-pg` y `turnos-odontologia-*` en el mismo estado que en 1.2; `grep -rF` de la contraseña y la clave de la sesión sobre `parcial/` vacío; borrar el archivo de entorno del scratchpad; `git status --short` muestra cambios sólo en `parcial/evidencia/` y `openspec/changes/evidencia-casos-reproducible/`. Verificación: salidas anotadas aquí
- [x] 6.4 Marcar F-02 `[x]` en `CHANGES.md` (estado y tabla Resumen) y mover «Próximo change» según el estado de F-03, en `CHANGES.md`, `CLAUDE.md` y `AGENTS.md` (`diff CLAUDE.md AGENTS.md` vacío); avisar a F-03 que `parcial/README.md` debe mencionar los archivos nuevos de `parcial/evidencia/`. Verificación: diff vacío y líneas actualizadas

## Notas de ejecución (2026-11-06)

- 1.1: Python 3.13.15 (venv), fastapi/sqlalchemy/asyncpg/alembic/httpx importan, Docker 29.9.2, imagen `postgres:16-alpine` presente. 1.2: puertos 55432 y 8001 libres, sin `libreria-f02`.
- 1.3: Q-A script httpx temporal en el scratchpad (no versionado); Q-B regenerar el txt de C-14 sobre PostgreSQL 16 y el usuario rehace el png; Q-C sí, también los de sólo lectura (C-01, C-03, C-04, C-06, C-09, RN-15); Q-D puertos alternativos (55432 / 8001).
- 2.x: PostgreSQL 16.15 en `libreria-f02`; CHECKPOINT de destino impreso `127.0.0.1 55432 libreria` antes de alembic/seed.
- Desvío del plan: el ejecutor usa `http://127.0.0.1:8001` en vez de `localhost` (en esta máquina `localhost` agrega ~2 s por IPv6 y distorsiona los tiempos de C-04/C-05).
- 5.x: las 13 corridas (C-01..C-13 sin C-14/C-15, C-16, RN-15) coinciden con sus `# Esperado:`; sin «NO coincide». C-15 reemplazado por el log crudo (4 SELECT y 4 SELECT).
- Observación (no es un «NO coincide»): uvicorn muestra `UserWarning: Pydantic serializer warnings ... field_name='rol'` (stderr) al responder `DELETE /usuarios/{id}/roles/{rol}`; la respuesta es correcta. Ver reporte.
- 6.1: `C-14_solo_agregado.txt` regenerado sobre PostgreSQL 16.15. 6.2: el usuario rehace `C-14_captura_psql.png` después (el contenedor se descartó; ver el comando en el reporte); el png actual sigue sin coincidir hasta entonces.
- 6.3: uvicorn detenido, `libreria-f02` eliminado, `libreria-pg` y `turnos-*` sin cambios, grep de contraseña/clave vacío, archivo de entorno borrado, `git status` sólo con cambios en `parcial/evidencia/` y el change (más CHANGES.md/CLAUDE.md/AGENTS.md por 6.4).
- 6.4: F-02 `[x]`; próximo change F-03. Aviso a F-03: `parcial/README.md` debe mencionar los archivos nuevos de `parcial/evidencia/` (`*_corrida.txt`, `migraciones_ida_y_vuelta.txt`, C-14 y C-15 regenerados).
