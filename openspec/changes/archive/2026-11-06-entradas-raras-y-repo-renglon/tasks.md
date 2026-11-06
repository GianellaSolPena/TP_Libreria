# Tasks

> Verificación manual (DD-01, sin pytest). Entorno de prueba SIEMPRE descartable: contenedor `postgres:16-alpine` con nombre `ra-f05-pg` y contraseña aleatoria fuera del repo, uvicorn propio en un puerto ≠ 8000 corrido desde un directorio sin `.env` (variables de entorno temporales, `PYTHONPATH=parcial`, `--app-dir parcial`). Nunca la base del usuario, el puerto 8000 ni un `.env`. Governance MEDIO: detenerse y consultar en los checkpoints marcados.

## 1. Línea base

- [x] 1.1 Levantar el entorno descartable (`alembic upgrade head` + `python seed.py`) y correr el script de sonda (punto de partida usado en el propose: `C:/Users/agusf/AppData/Local/Temp/claude/ddf220411b4612e1/84f4a130-e896-475c-b31a-cf8c450c047b/scratchpad/f05run/probe.py`, puerto 8765; si ya no existe, rehacerlo desde design.md) con los 27 reproductores (sustitutos sueltos en cuerpos/clave sobrante/bytes `ED A0 80`; `NaN`/`±Infinity`/`1e400` sin comillas en `precio`, `stock_inicial`, `editorial_id`, `cantidad`, `cliente_id`) más los vectores de consulta, ruta, cookie y Bearer; verificar que reproduce exactamente los 500 descritos en design.md (Context) y guardar la salida en el scratchpad como "antes"
- [x] 1.2 Correr todos los `.http` existentes (C-01..C-13, C-15, C-16, RN-02, RN-03, RN-15; re-sembrar entre archivos) y `test/solo_agregado.sql`; verificar que coinciden con los comentarios de respuesta esperada y con `parcial/evidencia/` (línea base sin fallas previas; si alguna falla, detenerse y reportar)

## 2. Contrato: sustitutos sueltos

- [x] 2.1 Extender `rechazar_nulo` en `parcial/app/core/validacion.py` para rechazar U+D800–U+DFFF con mensaje propio (D1), sin renombrar `TextoSinNulo` ni la función; verificar con la sonda que `titulo`/`isbn` de `POST /libros`, `PATCH /libros/1`, `PATCH /clientes/1`, `POST /clientes/1/perfil` y los nombres de editorial/autor/género dan 422 con `loc` del campo (o, mientras falte el grupo 3, que ya no llegan a la base: sin `DataError` en la consola)
- [x] 2.2 Verificar que un emoji como par válido (`"Ensayo 😀"` en `POST /generos`) sigue dando 201 y que `GET /libros?titulo=ficc` no cambia

## 3. Respuesta 422 siempre serializable

- [x] 3.1 Agregar en `parcial/app/core/errores.py` el manejador de `RequestValidationError` con la función recursiva de saneo (D2) y registrarlo en `parcial/main.py`; verificar con la sonda que los 27 reproductores responden 422 con JSON válido (incluidos la clave sobrante con sustituto, los bytes `ED A0 80`, el login con sustituto en correo/contraseña sin fila nueva en `intento_acceso`, y `POST /libros` sin `autores` con `"precio": Infinity`)
- [x] 3.2 Verificar igualdad byte a byte de los 422 existentes: comparar las respuestas de C-01, C-07 (vencimiento inválido), C-16 (paginación) y RN-15 con `parcial/evidencia/`; cualquier diferencia es un defecto

## 4. Red de seguridad del driver

- [x] 4.1 CHECKPOINT: con D1 desactivado temporalmente (sólo en la prueba, sin guardar), enviar `POST /libros` con sustituto en `titulo` y confirmar que el `DBAPIError` expone un `UnicodeEncodeError` en la cadena de causas de `exc.orig`; si no lo expone, detenerse y consultar antes de elegir el criterio
- [x] 4.2 Agregar en `traducir_errores` la rama del error de codificación → 422 con `MENSAJE_DATO_INVALIDO` (D3), sin ampliar a todo `DataError`; verificar con la misma prueba de 4.1 que responde 422 sin texto del driver ni traza, y luego restaurar D1 y confirmar `git diff` sin restos de la prueba

## 5. Repositorio de renglones de venta

- [x] 5.1 Agregar `RenglonVentaRepository(BaseRepository[RenglonVenta])` con `add_varios` (un `add_all` + un `flush`, sin `commit`) en `parcial/app/modules/ventas/repository.py` y exponerlo como `renglones` en `VentasUnitOfWork`; verificar que importa (`python -c "import main"` con el entorno temporal)
- [x] 5.2 Cambiar `crear` en `parcial/app/modules/ventas/service.py` para dar de alta la venta y luego los renglones por `uow.renglones.add_varios` (D4), sin asignar `venta.renglones`; verificar C-10 (201 idéntico a `evidencia/C-10_corrida.txt` salvo fecha), C-11 y C-12 (409 sin renglones nuevos, por psql) y C-13
- [x] 5.3 Con `SQL_ECHO=true`, correr C-15 y comparar con `evidencia/C-15_consultas_detalle_venta.txt`: el POST emite el INSERT de venta, UN INSERT en lote de renglones y los movimientos; el GET con 2 y con 4 renglones emite la misma cantidad de SELECT que antes; `lazy="raise_on_sql"` sigue en `models.py`
- [x] 5.4 Grep de capas: sin `AsyncSession`/`session`/`commit(`/`rollback(` en servicios; sin `commit(` en repositorios; routers sin cambios; verificar que cada clase de tabla de `parcial/app/modules` tiene su repositorio (14/14)

## 6. Casos y documentación

- [x] 6.1 Crear `parcial/test/RN-15b_sustitutos_y_no_finitos.http` con el formato de `RN-15_caracter_nulo.http` (precondiciones, `@no-cookie-jar`, respuesta esperada en comentario): título con sustituto (POST /libros), contraseña con sustituto (login), nombre con sustituto (registro), teléfono con sustituto (perfil), precio `NaN`, `Infinity` y `1e400`, cantidad `NaN` en venta, clave sobrante con sustituto y el emoji válido (201); correrlo y verificar que cada respuesta coincide con su comentario
- [x] 6.2 Guardar la corrida en `parcial/evidencia/RN-15b_corrida.txt` (sin secretos ni la contraseña de la base) y refrescar `C-10_corrida.txt`/`C-15_consultas_detalle_venta.txt` sólo si su contenido relevante cambió en 5.2/5.3; verificar que lo guardado coincide con los comentarios del `.http`
- [x] 6.3 Actualizar `parcial/README.md` (árbol de `test/` y `evidencia/` y tabla de casos) con RN-15b; verificar que cada archivo nombrado existe

## 7. Integración y cierre

- [x] 7.1 Regresión completa: todos los `.http` (C-01..C-16, RN-02, RN-03, RN-15, RN-15b) y `solo_agregado.sql` contra una base re-sembrada; sonda final con los 27 reproductores en 422 y cero 500 en la consola de uvicorn; guardar la salida "después" en el scratchpad
- [x] 7.2 `alembic check` sobre la base descartable: "No new upgrade operations detected" (sin migración)
- [x] 7.3 Borrar el contenedor `ra-f05-pg` y detener el uvicorn de prueba; verificar con `docker ps -a --filter name=ra-` que no queda nada y con `git status` que no hay cambios fuera de `parcial/` y del change (nada en `despliegue/`, sin `.env`)
- [x] 7.4 Marcar F-05 `[x]` en `CHANGES.md` (bloque, Resumen y "Próximo change") y en CLAUDE.md/AGENTS.md (idénticos, `diff` vacío), dejando anotado que el usuario rearma el zip a mano con `git archive` desde el commit nuevo (F-04); no armar el zip ni commitear sin pedido
