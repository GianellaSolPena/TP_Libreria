# Tasks

> Sin pytest (DD-01): cada tarea se verifica con `python seed.py`, `.http` contra uvicorn, psql o la consola con `SQL_ECHO=true`. Comandos desde `parcial/`. No se toca `app/`, `main.py`, `migrations/` ni `despliegue/`; si un caso revela un defecto de la API, se anota y se consulta antes de corregir. Las tareas siguen las recomendaciones QA-01..QA-05 del design.

## 1. `seed.py` (spec `datos-iniciales`)

- [x] 1.1 Crear `parcial/seed.py` según D1-D3: `asyncio.run`, `get_settings()` + `create_engine` + `create_session_factory`, una transacción, `TRUNCATE` de `SQLModel.metadata.sorted_tables` con `RESTART IDENTITY CASCADE`, `engine.dispose()` en `finally`; verificar que `python seed.py` sobre la base en head termina con código 0 y que `SELECT count(*)` de cada tabla da 0 antes de agregar datos (corrida intermedia)
- [x] 1.2 Cargar catálogo según D4 (3 editoriales, 3 géneros, 6 autores, 5 libros con `stock = 0`, autorías) con comprobación de ids tras cada `flush`; verificar con `GET /libros?size=2` (total 5, pages 3, ids 1 Rayuela 25000.00 y 2 Antología 30000.00) una vez cargado el stock (1.4)
- [x] 1.3 Cargar personas según D5: hashear las cinco contraseñas con `hashear_password` antes de abrir la transacción, usuarios 1-5, asignaciones abiertas, clientes 1-3 (perfil de Lucía, `usuario_id = 4` en Ana Paz); verificar login 200 de los cinco y `debe_cambiar_password` true sólo en `nuevo@example.com`, y `/auth/yo` con los roles de la spec
- [x] 1.4 Escribir el stock y la venta 1 según D6 con `LibroRepository.aplicar_movimiento` (5 «Stock inicial» por admin; venta 1 de Lucía con renglones a precio copiado y total 69000.00; dos «Venta» −1/−2 por vendedor) y la comprobación `stock == SUM(movimientos)` con rollback si falla; verificar `GET /ventas/1` (69000.00), `GET /libros/1/movimientos` (+11, −1) y la consulta psql de 7 movimientos e invariante en los cinco libros
- [x] 1.5 Agregar la línea `SISTEMA` «Carga de los datos iniciales» y el resumen impreso (D7); verificar `GET /eventos` con total 1 y `intento_acceso` vacía
- [x] 1.6 Verificar idempotencia y errores: correr `python seed.py` dos veces seguidas después de crear una venta y un usuario por la API y comparar conteos e ids (iguales); verificar que sin `JWT_SECRET_KEY` en el entorno el script termina con error que nombra la variable sin escribir nada; verificar que `test/solo_agregado.sql` sigue rechazando UPDATE/DELETE tras el seed (disparador intacto)
- [x] 1.7 Anotar en `knowledge-base/10_preguntas_abiertas.md` la resolución aplicada de IN-02, IN-03, Q-05 y Q-08 (datos de D4/D5/D6, «Stock inicial» por admin) y verificar que no queda la marca de abierta en esas entradas

## 2. Casos `.http` sobre el seed (spec `casos-prueba`)

- [x] 2.1 Crear `test/C-01_parametro_no_entero.http`, `C-02_registro_correo_repetido.http`, `C-03_cookie_login.http` y `C-04_credenciales_indistinguibles.http` según D8 (encabezado de precondiciones, sesiones con `# @name`/`# @no-cookie-jar`/`Cookie:`, respuesta esperada en comentario, psql comentado de C-02, extras de D9 marcados «(extra)»); verificar corriendo cada uno tras `python seed.py`: todas las respuestas coinciden con su comentario
- [x] 2.2 Crear `C-05_limite_intentos.http`, `C-06_401_403_lo_propio.http`, `C-07_revocar_rol_sesion_abierta.http`, `C-08_autoproteccion_admin.http` y `C-09_cambio_obligatorio.http` según D8; verificar cada uno tras `python seed.py` (incluida la consulta psql de los 5 fallos en `intento_acceso` y la fila revocada de C-07)
- [x] 2.3 Crear `C-10_venta_valida.http`, `C-11_venta_sin_stock.http`, `C-12_venta_inexistentes_o_baja.http` y `C-13_reponer_baja_reuso_isbn.http` según D8; verificar cada uno tras `python seed.py`, incluido el aviso del comprobante en la consola de uvicorn después de la respuesta (C-10) y el psql comentado `stock == SUM(movimientos)` en C-10, C-11 y C-12
- [x] 2.4 Reescribir `C-15_detalle_consultas_fijas.http` sobre el seed (venta 1 + venta nueva de 4 renglones, detalles con el mismo VENDEDOR, sin prefijo `c08.` ni psql previo) y crear `C-16_busqueda_paginacion_patch.http` según D8; verificar ambos tras `python seed.py` (C-15 con `SQL_ECHO=true`: mismos 4 SELECT en los dos detalles)
- [x] 2.5 Verificar el orden arbitrario: correr C-16, C-13 y C-07 en ese orden, cada uno tras `python seed.py`, y confirmar los mismos resultados que en el orden numérico
- [x] 2.6 Retirar `test/seed.sql`, `C-01_parametro_no_entero.http`… `C-08_busqueda_segura.http` del TP (los que no fueron reemplazados por nombre), `C-07_consultas_fijas.http`, `C-07_CapturasPantalla/`, `auth.http`, `autorizacion.http` y `libros_clientes_ventas.http` (D9, QA-03); verificar con `ls test/` que quedan exactamente los 15 `.http` de C-01..C-13, C-15, C-16 y `solo_agregado.sql`, y con `grep -rn "c0[5-8]\.\|seed.sql" test/` que no quedan referencias

## 3. Evidencia (specs `casos-prueba`, `migraciones-esquema`, `lecturas-relaciones`)

- [x] 3.1 Tras `python seed.py`, correr `test/solo_agregado.sql` en psql y guardar stdout+stderr con encabezado (comando, fecha) en `evidencia/C-14_solo_agregado.txt` (D10); verificar que contiene «UPDATE no permitido», «DELETE no permitido» y conteo 7 antes y después
- [x] 3.2 Tras `python seed.py`, con uvicorn `SQL_ECHO=true` y la salida a un archivo temporal, correr `C-15_detalle_consultas_fijas.http` y regenerar `evidencia/C-15_consultas_detalle_venta.txt` con el bloque de cada detalle (2 y 4 renglones) y su conteo de SELECT; verificar que ambos conteos son iguales y que `grep -n "c08\." evidencia/` no da resultados

## 4. README (spec `guia-puesta-en-marcha`)

- [x] 4.1 Reescribir `parcial/README.md` según D11: integrantes (QA-01), requisitos, pasos 1-6 con comandos Windows/POSIX, tabla de variables y generación de `JWT_SECRET_KEY`, usuarios del seed con contraseñas de mentira, estructura cap. 1-6, endpoints actuales sin barra final con `page`/`size`, tabla de casos C-01..C-16 con archivo, condición (`SQL_ECHO`, psql) y evidencia; verificar con `grep -n "seed.sql\|limit\|offset" README.md` sin instrucciones vigentes del TP y que no hay ningún secreto real
- [x] 4.2 Verificar el README desde cero siguiéndolo literalmente: `alembic downgrade base` → `alembic upgrade head` → `python seed.py` → `uvicorn main:app` → `GET /health/ready` 200 y `GET /libros` con los cinco libros; corregir el README si algún paso no funciona tal como está escrito

## 5. Integración final

- [x] 5.1 Corrida completa: los 15 `.http` en orden numérico, cada uno tras `python seed.py`, sin ningún 500 ni traza en la consola de uvicorn; anotar en este archivo el resultado por caso
  Resultado de la corrida completa (2026-11-06; PostgreSQL 17 local temporal, uvicorn con `SQL_ECHO=true`, runner propio que interpreta los `.http` porque no hay REST Client en el entorno; `python seed.py` antes de cada archivo; códigos HTTP en orden de petición, 0 respuestas 500 y 0 trazas en la consola):
  - C-01: 200 422 200 422 422 404 · C-02: 201 409 409 409 422 422 · C-03: 200 200 401 401 200 422 · C-04: 401 401
  - C-05: 401×5 429 429 200 (5 filas en `intento_acceso`) · C-06: 401 200 403 201 200 200 403 200 403 · C-07: 200 200 200 200 403 200 200 422 422 201 200 (fila revocada confirmada por psql)
  - C-08: 200 409 200 200 · C-09: 200 403 200 200 200 200 401 200 200 409 · C-10: 200 200 201 200 200 200 200 200 (stock 8/2; aviso del comprobante después de la respuesta)
  - C-11: 200 409 200 200 200 · C-12: 200 200 409 409 204 409 409 200 200 · C-13: 200 200 204 200 404 409 201 409 200 200 · C-15: 200 201 200 200 (4 SELECT en ambos detalles) · C-16: 200 200 200 200 422 422 200 422 200 200
  - `stock == SUM(movimientos)` comprobado por psql tras C-10 (9 mov.), C-11 y C-12 (7 mov.). Lo que NO se verificó: la ejecución con la extensión REST Client real (en particular `{{login.response.headers.Set-Cookie}}` y `{{x.response.body.$.id}}`; el runner replica la misma sustitución) y la base de 5432 del usuario (no hay `.env`).
- [x] 5.2 Confirmar con `git status` que no cambió nada en `parcial/app/`, `parcial/main.py`, `parcial/migrations/` ni `despliegue/`, y que `.env` no está en el árbol versionado

## Workflow follow-up

- Confirmar con el grupo QA-01 (integrantes, Q-06) antes de la entrega; si cambian, sólo se edita el README.
- Archivar el change con `/opsx:archive seed-casos-readme` y marcar C-09 `[x]` en `CHANGES.md`.
- Commit (Conventional Commits en español) sólo a pedido explícito.
