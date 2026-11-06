# Tasks

> Sin pytest (DD-01): se verifica con comandos. **Governance ALTO** (filtrado de credenciales): las tareas marcadas **[APROBACIÓN]** muestran el resultado/comando al usuario y esperan un "sí" explícito. No se modifica nada de `parcial/` ni `despliegue/` (regla 9); el zip va fuera del repo y no se versiona; sin commits ni push sin pedido explícito (regla 11). Nunca se imprime en el chat el valor de una contraseña o clave (ni las de prueba ni las de `parcial/.env`).
>
> Atajos (Git Bash): `R=/c/Users/agusf/Desktop/TP_Libreria`; `S=<scratchpad de la sesión>/c12`; `OUT=/c/Users/agusf/Desktop/Entrega_Parcial`; `Z="$OUT/Parcial_Cap1a6_Las_chicas.zip"` (el nombre ya no lleva espacio; igual se citan las variables por prolijidad). Scripts auxiliares en `$S/tools/`; Python sobre el árbol extraído siempre con `-I`.

## 1. Precondiciones

- [x] 1.1 Decisiones del usuario ya tomadas (2026-11-06): nombre `Parcial_Cap1a6_Las_chicas.zip`, destino `C:\Users\agusf\Desktop\Entrega_Parcial\`, evidencia de C-14 = texto + captura. Verifica: anotadas en el resumen.
- [x] 1.2 **Precondición (el usuario, fuera de este change):** existe `parcial/evidencia/C-14_captura_psql.png` (captura de psql tomada por el usuario) y está commiteada, junto con la actualización de `parcial/README.md` para que mencione el `.png` además de `C-14_solo_agregado.txt`, en un commit aparte previo al zip. Verifica: `git -C "$R" ls-files parcial/evidencia/C-14_captura_psql.png` lo lista y `grep -n "C-14_captura_psql" "$R/parcial/README.md"` coincide; si falta, se frena y no se arma el zip.
- [x] 1.3 Comprobar árbol limpio y anotar el commit de origen (el posterior al commit de 1.2): `git -C "$R" status --porcelain -- parcial despliegue` vacío y `git -C "$R" rev-parse HEAD`. Verifica: salida vacía + hash anotado.
- [x] 1.4 Comprobar herramientas: `python --version` (≥ 3.12), `docker info` responde, `C:/Windows/System32/tar.exe --version`. Verifica: los tres responden.

## 2. Armado del zip

- [x] 2.1 Crear `$OUT` (si ya existe un zip con ese nombre, preguntar antes de sobrescribir) y armar: `git -C "$R" archive --format=zip --output="$Z" HEAD parcial despliegue`. Verifica: el archivo existe y `git -C "$R" status --porcelain` no muestra nada nuevo.
- [x] 2.2 Listar: `python -I -m zipfile -l "$Z" > "$S/listado.txt"` y `C:/Windows/System32/tar.exe -tf "$Z" | wc -l`. Verifica: ambos lectores lo abren; el número de archivos (sin directorios) es 176 (175 + `C-14_captura_psql.png`) = `git -C "$R" ls-files parcial despliegue | wc -l`.
- [x] 2.3 Chequeo estructural sobre el listado (script en `$S/tools/`): toda entrada empieza por `parcial/` o `despliegue/`, ninguna contiene `\`, ninguna coincide con `\.git/|\.venv/|__pycache__/|\.pyc$|/\.env$|/\.env\.|\.pytest_cache|knowledge-base|openspec|\.claude|\.atl|CHANGES\.md|Consigna`; están los archivos obligatorios de la spec (parcial: `main.py`, `seed.py`, `app/`, `requirements.txt`, `env.example`, `alembic.ini`, migraciones 0001-0004, `test/*.http`, `test/solo_agregado.sql`, `README.md`, `evidencia/C-14_solo_agregado.txt`, `evidencia/C-14_captura_psql.png`, `evidencia/C-15_*`; despliegue: `Dockerfile`, `.dockerignore`, `env.example`, `DEPLOY.md`, `evidencia/D-01_*`..`D-08_*`, `evidencia/local/`). Verifica: el script imprime 0 faltantes y 0 prohibidas.

## 3. Verificación de contenido (zip extraído)

- [x] 3.1 Extraer en un directorio nuevo: `python -I -m zipfile -e "$Z" "$S/extraido"`. Verifica: existen `$S/extraido/parcial` y `$S/extraido/despliegue` y nada más en `$S/extraido`.
- [x] 3.2 Fidelidad byte a byte: comparar `git hash-object` de cada archivo extraído con el blob de `git -C "$R" ls-tree -r HEAD -- parcial despliegue` (mismo conjunto de rutas). Verifica: 176/176 coinciden, 0 sobrantes, 0 faltantes (incluye EOL CRLF/mixed sin cambios).
- [x] 3.3 Enlaces: resolver cada enlace relativo de `despliegue/DEPLOY.md` y de `parcial/README.md` dentro de `$S/extraido`. Verifica: 0 enlaces rotos (incluye `evidencia/local/`).
- [x] 3.4 Integrantes y evidencia: `grep -n "Integrantes" "$S/extraido/parcial/README.md"` y `grep -n "C-14_captura_psql" "$S/extraido/parcial/README.md"`. Verifica: lista Agustina Fontagnol, Martina Suarez y Gianella Peña, y el README menciona el `.png` de C-14 (que existe en `$S/extraido/parcial/evidencia/`).
- [x] 3.5 Búsqueda de secretos por patrón sobre `$S/extraido` (`grep -rnI -E`): `(POSTGRES_PASSWORD|JWT_SECRET_KEY)=\S`, `postgres(ql)?(\+asyncpg)?://[^:/ ]+:[^@ ]+@` excluyendo el marcador `usuario:password@<host>`, `PRIVATE KEY`, `ssh -i`, `IdentitiesOnly`, `agus-grupo1`, `/VPS/`, `C:\\Users`, `/c/Users`. Verifica: 0 coincidencias fuera de las permitidas por la spec (seed de mentira de Q-05, marcadores de `env.example`); cada coincidencia permitida se justifica en el resumen.
- [x] 3.6 Inventario de IPv4 (`grep -rnoI -E '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b'`, agrupado). Verifica: sólo la IP del VPS de la URL pública declarada, `127.0.0.1`, `0.0.0.0` y `172.16-31.x` internas de Docker; cualquier otra se muestra al usuario.
- [x] 3.7 Valores reales locales: escribir en `$S/valores.tmp` los valores no vacíos de `POSTGRES_PASSWORD` y `JWT_SECRET_KEY` de `$R/parcial/.env` (sin imprimirlos), correr `grep -rFlI -f "$S/valores.tmp" "$S/extraido" | wc -l` y borrar `$S/valores.tmp`. Verifica: conteo 0 y el archivo temporal ya no existe.

## 4. Verificación funcional desde el zip extraído

- [x] 4.1 Base descartable: generar `PW` y `JWT` con `python -c "import secrets; print(secrets.token_urlsafe(24))"` guardados sólo en `$S/`; `docker network create c12-net`; `docker run -d --name c12-pg --network c12-net -p 127.0.0.1:55432:5432 -e POSTGRES_USER=libreria -e POSTGRES_DB=libreria -e POSTGRES_PASSWORD="$PW" postgres:16-alpine`; esperar `docker exec c12-pg pg_isready -U libreria`; `docker exec c12-pg createdb -U libreria libreria_tp`. Verifica: `pg_isready` OK y `\l` lista `libreria` y `libreria_tp` (puertos alternativos si 55432 está ocupado).
- [x] 4.2 `parcial/` desde cero siguiendo su README: en `$S/extraido/parcial` crear `.env` desde `env.example` (`POSTGRES_PORT=55432`, `POSTGRES_PASSWORD=$PW`, `JWT_SECRET_KEY=$JWT`); `python -m venv .venv`; `.venv/Scripts/python -m pip install -r requirements.txt`. Verifica: pip termina sin error.
- [x] 4.3 `.venv/Scripts/alembic upgrade head` y `.venv/Scripts/alembic current`. Verifica: sin error y revisión actual = 0004 (head).
- [x] 4.4 `.venv/Scripts/python seed.py`; arrancar `.venv/Scripts/uvicorn main:app --port 18000` en segundo plano; `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:18000/health/ready` y `/libros/`; detener uvicorn. Verifica: seed sin error, 200 y 200.
- [x] 4.5 `despliegue/`: `docker build -t c12-libreria-check "$S/extraido/despliegue"`. Verifica: build sin error.
- [x] 4.6 `docker run -d --name c12-app --network c12-net -e DATABASE_URL="postgresql+asyncpg://libreria:$PW@c12-pg:5432/libreria_tp" -e SQL_ECHO=false c12-libreria-check`; esperar `docker inspect -f '{{.State.Health.Status}}' c12-app` = `healthy`; `docker exec c12-app wget -qO- http://127.0.0.1:8000/health/ready`; `docker logs c12-app` (revisar que no muestre la URL con contraseña al copiar al resumen). Verifica: `healthy`, respuesta OK y Alembic aplicó 0001-0002 sin error.
- [x] 4.7 Limpieza: `docker rm -f c12-app c12-pg`; `docker network rm c12-net`; `docker rmi c12-libreria-check`; borrar `$S/extraido`, `$S/*.tmp` y los valores de prueba. Verifica: `docker ps -a --filter name=c12-` vacío, `docker network ls --filter name=c12-` vacío, `$S/extraido` no existe; `git -C "$R" status --porcelain` sin cambios en `parcial/`/`despliegue/`.

## 5. Aprobación y cierre

- [x] 5.1 **[APROBACIÓN]** Presentar al usuario: commit de origen, ruta, tamaño y `sha256sum "$Z"`, el listado completo de entradas agrupado por carpeta (`$S/listado.txt`) y el resumen de las secciones 2-4 (incluidas las coincidencias permitidas). Verifica: "sí" explícito del usuario; si pide cambios, se frena (cambios en `parcial/`/`despliegue/` van aparte, se commitean y se rearma desde 2.1).
- [x] 5.2 Planificación: en `knowledge-base/10_preguntas_abiertas.md` marcar Q-15 resuelta (2026-11-06, el usuario: el zip no incluye `.git`) y anotar en Q-13 que la fecha se consulta en el campus (informativa). Verifica: `grep -n "Q-15\|Q-13" knowledge-base/10_preguntas_abiertas.md` muestra las anotaciones.
- [x] 5.3 Recordar al usuario que el zip lo sube **una sola integrante** a la tarea del campus antes de la fecha publicada, y que si después se commitea algo en `parcial/` o `despliegue/` hay que rearmarlo y reverificarlo. Verifica: incluido en el resumen final.

Recordatorio final: el zip lo sube **una sola integrante** a la tarea del campus antes de la fecha publicada; si después se commitea algo en `parcial/` o `despliegue/`, hay que rearmarlo y reverificarlo.
