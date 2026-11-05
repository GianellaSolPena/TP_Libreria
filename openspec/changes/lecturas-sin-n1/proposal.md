# Proposal

## Why

El Ej. 8 del PDF (6 pts) exige que toda respuesta con datos de una relación los obtenga con carga anticipada declarada en el repositorio, que el detalle de una venta use un número fijo de consultas (caso C-15, con evidencia en consola) y que ninguna lectura dependa de la carga perezosa. La revisión del código de `parcial/` tras C-07 muestra que **la precarga ya está resuelta en todos los métodos de lectura** (no se encontró ningún N+1 real); lo que falta es *garantizarlo* (hoy los modelos conservan `lazy="select"` por defecto, así que una precarga olvidada sólo se descubre como `MissingGreenlet` → 500), *demostrarlo* (C-15 con `SQL_ECHO=true` y salida en `parcial/evidencia/`) y cerrar el repaso final del Ej. 3/6/8 que CHANGES asigna a este change.

Por eso el change se **reduce**: no reescribe repositorios ni servicios; blinda los modelos, agrega el caso C-15 y deja constancia del repaso.

## What Changes

- Todas las relaciones de los modelos de `parcial/app/modules/*/models.py` declaran `lazy="raise_on_sql"` (vía `sa_relationship_kwargs`): una lectura que no precargó la relación falla con un error explícito del ORM en lugar de intentar una consulta perezosa. Sin cambios de esquema ni migraciones (es configuración del ORM).
- Se conservan, sin cambios, las precargas existentes dentro de los repositorios (`VentaRepository.get_detalle`/`listar`, `LibroRepository.get_detalle`/`listar_vigentes`, `ClienteRepository.get_con_perfil`/`listar_con_perfil`); se confirma con `SQL_ECHO` que cada una emite una cantidad fija de SELECT.
- Nuevo caso `parcial/test/C-15_detalle_consultas_fijas.http`: crea una venta de 2 renglones y otra de 4 (ids tomados de la respuesta, no del seed) y pide el detalle de ambas; respuesta y cantidad de consultas esperadas en comentario.
- Evidencia `parcial/evidencia/C-15_consultas_detalle_venta.txt` con el fragmento de consola de uvicorn (`SQL_ECHO=true`) de los dos detalles.
- Repaso final documentado (sin cambios de código previstos salvo hallazgo): listados paginados con `total` filtrado, búsqueda ligada, ids `int4` acotados, handlers `async def` sin llamadas bloqueantes y el `grep` de sesión/`commit(`/`rollback(` en servicios y routers.
- Aclaración de spec: el `grep` de capas admite la sesión en routers **sólo** en la dependencia que construye el Unit of Work (lo que exige el propio PDF); en servicios sigue sin admitirse.

## Capabilities

### New Capabilities
- `lecturas-relaciones`: carga anticipada declarada en el repositorio, prohibición de la carga perezosa, detalle de venta con cantidad fija de consultas (incluye libro dado de baja), handlers asincrónicos sin llamadas bloqueantes y evidencia C-15.

### Modified Capabilities
- `capas-persistencia`: el escenario de revisión por `grep` distingue servicios (ninguna referencia a la sesión) de routers (sólo la dependencia que construye el Unit of Work).
- `modelo-datos`: la navegación recíproca entre los dos extremos de una relación requiere que ambas colecciones se hayan precargado (consecuencia de prohibir la carga perezosa).

## Impact

- Código: `parcial/app/modules/{clientes,libros,ventas,usuarios,autores,editoriales,generos}/models.py` (sólo kwargs de `Relationship`). Ningún cambio en repositorios, servicios, routers ni schemas salvo que el repaso encuentre un defecto.
- Pruebas/evidencia: `parcial/test/C-15_detalle_consultas_fijas.http`, `parcial/evidencia/` (nueva carpeta).
- Sin cambios de API, contratos de respuesta, migraciones ni dependencias.
- Comportamiento verificado en C-05/C-06/C-07 debe seguir igual: se re-ejecutan `auth.http`, `autorizacion.http` y `libros_clientes_ventas.http` tras el blindaje.
- Desbloquea C-09 (seed, `.http` definitivos C-01..C-16 y README), que regenerará la evidencia C-15 sobre el seed final.
