# Tasks

> Sin pytest (DD-01): cada tarea se verifica con `.http` contra uvicorn, consola con `SQL_ECHO=true`, `grep` o `alembic`. Comandos desde `parcial/`. Las tareas reflejan las recomendaciones QA-01..QA-05 del design; si el usuario elige otra opción, ajustar el grupo indicado en la QA.

## 1. Línea base (antes de tocar código)

- [x] 1.1 Con la base migrada y `SQL_ECHO=true`, correr `test/auth.http`, `test/autorizacion.http` y `test/libros_clientes_ventas.http` (precondiciones de cada archivo) y anotar en este archivo que todas las respuestas coinciden con el comentario esperado; si alguna falla, detener y reportarla como falla previa (no se corrige en C-08)
  - Línea base (uvicorn en :8013, `SQL_ECHO=true`, sin modelos tocados), con los runners httpx equivalentes a cada `.http`: auth 70 chequeos sin fallas; autorización 80/80; libros/clientes/ventas 185 OK y 2 fallas previas que no son del código: `CAT-4b` (artefacto del renombrado de prefijo en el runner, la consulta manual da total 1) y `CL-12` (el runner conserva la expectativa anterior a QA-12; hoy responde 409 por diseño). Los chequeos finales del runner (`FIN ...`) fallan porque no se pudo limpiar sin desactivar el disparador append-only.
- [x] 1.2 Con la misma consola, registrar la cantidad de SELECT de `GET /ventas/{id}` (venta de 2 renglones), `GET /libros/{id}` (libro con 1 y con 3 autores), `GET /libros?size=20` y `GET /clientes`, y verificar que coincide con el inventario del design (detalle de venta: 2 SELECT del repositorio + 2 de la sesión)
  - Línea base: detalle de venta vendedor 4 (2 y 4 renglones), dueña 5; `GET /libros/{id}` 2 (1 y 3 autores); `GET /libros?size=20` 2; `GET /clientes` 4. Coincide con el inventario del design.

## 2. Blindaje contra la carga perezosa (QA-01 opción A; se omite con la opción C)

- [x] 2.1 Agregar `"lazy": "raise_on_sql"` a `sa_relationship_kwargs` de los 26 `Relationship` de `app/modules/{clientes,libros,ventas,usuarios,autores,editoriales,generos}/models.py`, fusionando con `foreign_keys`/`uselist` existentes en `usuarios/models.py`; verificar con `grep -c "raise_on_sql" app/modules/*/models.py` que la suma es 26 y con `grep -n "Relationship(" app/modules/*/models.py` que ninguno quedó sin la opción
  - Hecho: 26 `Relationship` con `"lazy": "raise_on_sql"` (autores 1, clientes 4, editoriales 1, generos 1, libros 10, usuarios 4, ventas 5); `grep -n "Relationship("` da 26 líneas, ninguna sin la opción.
- [x] 2.2 Verificar que el cambio no altera el esquema: `alembic check` (o `alembic revision --autogenerate` en seco, descartando el archivo) no detecta diferencias, y `uvicorn main:app` arranca sin errores de mapeo
  - `alembic check`: "No new upgrade operations detected"; `compileall` sin errores; `configure_mappers()` y arranque de uvicorn sin errores.
- [x] 2.3 Re-ejecutar los tres `.http` de 1.1 y confirmar las mismas respuestas y la misma cantidad de SELECT de 1.2; cualquier `InvalidRequestError ... raise_on_sql` es una precarga faltante: agregarla dentro del método del repositorio que hace la lectura (D1) y repetir
  - Regresión idéntica a la línea base: auth 70/70, autorización 80/80, libros/clientes/ventas 185 OK con las mismas 2 fallas previas del runner; mismos SELECT (venta 4/5, libro 2, catálogo 2, clientes 4); log de uvicorn sin `raise_on_sql`, `InvalidRequestError`, `MissingGreenlet`, Traceback ni 500. No hizo falta ninguna precarga nueva.

## 3. Caso C-15 y evidencia

- [x] 3.1 Crear `test/C-15_detalle_consultas_fijas.http` según D4 (precondiciones y limpieza con prefijo `c08.`, ADMIN por psql, 4 libros y un cliente de prueba, venta de 2 y de 4 renglones, detalle de cada una con el mismo usuario, baja de un libro vendido y nuevo detalle), con respuesta y cantidad de consultas esperadas en comentario; verificar corriéndolo completo contra uvicorn
  - Creado `parcial/test/C-15_detalle_consultas_fijas.http` (arranque, 4 libros y cliente `c08.`, ventas de 2 y 4 renglones, D-01/D-02, baja, D-04, D-05). Corrido completo contra uvicorn :8013: 21 casos, 0 fallas.
- [x] 3.2 Con `SQL_ECHO=true`, copiar de la consola el fragmento de los dos detalles (2 y 4 renglones) y del detalle tras la baja a `evidencia/C-15_consultas_detalle_venta.txt`, con una línea de encabezado por petición y el conteo de SELECT; verificar que los tres conteos son iguales y que el renglón del libro dado de baja muestra su título
  - Evidencia en `parcial/evidencia/C-15_consultas_detalle_venta.txt`: SELECT por detalle (vendedor) = 4 con 2 renglones, 4 con 4 renglones y 4 tras la baja; el renglón del libro dado de baja muestra `c08.Libro uno`.

## 4. Repaso final (verificación; sólo se corrige si un chequeo falla)

- [x] 4.1 Paginación: verificar en `GET /libros?titulo=ficc&size=1` total 1 y pages 1, `page=2` → 422 y `size=500` → 422; y revisar que cada servicio con `Pagina` cuenta con los mismos filtros que lista (libros `_filtros`, `ventas.contar(cliente_id)`, clientes, catálogo, eventos, movimientos); anotar resultado
  - OK: `titulo=c08.r.ficc&size=1` total 1/pages 1 (`titulo=ficc` da 3 por filas de prueba, igual al conteo psql); `page=2` sobre 1 página -> 422 «La página 2 no existe: hay 1»; `page=0` y `size=500` -> 422. Revisión de código: libros `_listar` usa los mismos `**filtros` en `contar_vigentes` y `listar_vigentes`; ventas/clientes-ventas `contar(cliente_id)`; clientes, autores, editoriales, géneros y eventos `count()` sin filtros extra con `listar` sin filtros; movimientos `contar_de_libro(libro_id)` con el mismo filtro.
- [x] 4.2 Búsqueda ligada: `GET /libros?titulo=' OR '1'='1` → 200 con lista vacía y total 0; con `SQL_ECHO=true` la consola muestra `ILIKE` con parámetro ligado
  - OK: `titulo=' OR '1'='1` -> 200, items [], total 0; consola: `libro.titulo ILIKE $1::VARCHAR` con el valor en la línea de parámetros.
- [x] 4.3 Entradas fuera de `int4`: `GET /libros/99999999999`, `GET /ventas/99999999999`, `GET /libros?genero_id=99999999999` y un `POST /ventas` con `cantidad` 99999999999 responden 422, nunca 500
  - OK: `GET /libros/99999999999`, `GET /ventas/99999999999`, `GET /libros?genero_id=99999999999` y `POST /ventas` con `cantidad` 99999999999 -> 422; ningún 500 en el log.
- [x] 4.4 Asincronía: `grep -n "^def \|^    def " app/modules/*/router.py` sólo lista dependencias (`get_uow`, `get_libros_uow`, `get_intentos_uow`), no handlers; `grep -rn "time.sleep\|bcrypt\.\(hashpw\|checkpw\)" app` sólo encuentra bcrypt dentro de `asyncio.to_thread` en `core/security.py`
  - OK: los `def` de los routers son sólo `get_uow`, `get_libros_uow` y `get_intentos_uow`; todos los handlers decorados son `async def` (autores 5/5, clientes 6/6, editoriales 5/5, géneros 5/5, health 2/2, libros 7/7, usuarios 10/10, ventas 4/4); bcrypt sólo dentro de `asyncio.to_thread` en `core/security.py` (l. 38 y 45), sin `time.sleep`; el aviso usa `asyncio.sleep` (`ventas/service.py:21`).
- [x] 4.5 Capas (delta de `capas-persistencia`, QA-04): `grep -rn "AsyncSession\|commit(\|rollback(" app/modules/*/service.py` vacío; `grep -rn "commit(\|rollback(" app/modules/*/router.py` vacío; `grep -rn "AsyncSession" app/modules/*/router.py` sólo en las dependencias que construyen el UoW (y `async_sessionmaker` sólo en `get_intentos_uow`, DD-09); anotar la salida
  - OK: `grep AsyncSession|commit(|rollback(` en `service.py` de todos los módulos: vacío; `commit(|rollback(` en `router.py`: vacío; `AsyncSession` en routers sólo en import y en las dependencias `get_uow`/`get_libros_uow`; `async_sessionmaker` sólo en `usuarios/router.py` (`get_intentos_uow`, DD-09).

## 5. Cierre

- [x] 5.1 Correr en orden `auth.http`, `autorizacion.http`, `libros_clientes_ventas.http` y `C-15_detalle_consultas_fijas.http` sobre una base recién limpiada y confirmar que todas las respuestas coinciden con su comentario; verificar `stock == SUM(movimiento_stock.cantidad)` por libro con psql tras las ventas de C-15
  - Corrida final con servidor nuevo y log propio: autorización 80/80, auth sin fallas, libros/clientes/ventas 185 OK y las mismas 4 fallas previas de 1.1 (CAT-4b, CL-12 y los dos `FIN` por el residuo), incluidos los chequeos de consola (avisos == ventas confirmadas, orden 201/aviso, sin 500 ni Traceback); C-15 21 casos 0 fallas con SELECT 4/4/4. `stock == SUM(movimiento_stock.cantidad)` en todos los libros `c08.` (psql, 0 filas); libros reales 1..5 con stock 10/15/8/6/12 intactos. Nota: la base no quedó "recién limpiada" (el disparador append-only impide borrar las ventas de prueba sin desactivarlo); cada corrida usó un prefijo propio `c08.<x>.`.
- [x] 5.2 Marcar C-08 como completo en `CHANGES.md` y dejar anotado en su ficha que C-09 regenera la evidencia C-15 tras `python seed.py` y retira `test/C-07_consultas_fijas.http` del TP (QA-03)
  - `CHANGES.md`: C-08 marcado `[x]` (ficha y tabla) con la nota de que C-09 regenera la evidencia C-15 tras `python seed.py` y retira `test/C-07_consultas_fijas.http`.
