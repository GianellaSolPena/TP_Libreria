# Proposal

## Why

La auditoría post-entrega (`informe-cumplimiento/index.html`, 2026-11-06) dejó varios requisitos en **parcial** o **no verificable** sólo por falta de evidencia, no por defectos: el ciclo `upgrade → downgrade → upgrade` de Alembic nunca quedó registrado; los casos que escriben datos (C-02, C-05, C-07, C-08, C-10..C-13 y los PATCH de C-16) tienen la respuesta esperada en comentario pero ninguna corrida guardada; la evidencia de C-15 es un resumen recortado a mano (líneas truncadas con `[...]`, sin parámetros ni líneas `INFO: ... HTTP/1.1`), y el aviso del comprobante de C-10 en la consola de uvicorn no está capturado. Además, `C-14_solo_agregado.txt` se tomó sobre PostgreSQL 17 y no coincide con `C-14_captura_psql.png`. F-01 ya está aplicado, así que ahora se puede correr todo sobre el código definitivo antes de rearmar el zip (F-04).

## What Changes

- Corrida reproducible, sin tocar código de la aplicación, sobre un **contenedor descartable `postgres:16-alpine`** (contraseña aleatoria fuera del repo; nunca la base local del usuario ni el contenedor `libreria-pg`), descartado al terminar.
- Evidencia nueva en `parcial/evidencia/`:
  - `migraciones_ida_y_vuelta.txt`: salida de `alembic upgrade head` → `downgrade base` → `upgrade head` sobre base vacía, con el estado de la base entre pasos.
  - Un archivo `C-NN_corrida.txt` por cada caso que escribe datos (C-02, C-05, C-07, C-08, C-10, C-11, C-12, C-13, C-16): cada petición tal como está en el `.http`, su `# Esperado:`, la respuesta real (estado, encabezados relevantes, cuerpo) y si coincide; más las consultas psql comentadas del archivo con su resultado.
  - C-10: el fragmento de consola de uvicorn con el aviso «Comprobante de la venta N enviado al cliente» después de la línea de la respuesta.
- `C-15_consultas_detalle_venta.txt` se **reemplaza** por la captura cruda de la consola con `SQL_ECHO=true` (sin recortes), conservando el encabezado de «cómo se obtuvo» y el conteo.
- C-14: se ofrece regenerar `C-14_solo_agregado.txt` sobre el contenedor PostgreSQL 16 sembrado y un paso **opcional del usuario** para rehacer `C-14_captura_psql.png` con la base sembrada (7 movimientos), para que txt y png coincidan.
- Sin cambios en `parcial/app/`, `main.py`, `seed.py`, `migrations/`, `parcial/test/`, `.env`, `despliegue/` ni el zip entregado. Si una corrida no coincide con su comentario, se detiene y se reporta (el arreglo sería otro change).

## Capabilities

### New Capabilities
<!-- ninguna -->

### Modified Capabilities
- `casos-prueba`: la evidencia de C-15 pasa a ser captura cruda; se agrega el requisito de evidencia de corrida de los casos que escriben datos (incluido el aviso del comprobante de C-10) y la coherencia entre el txt y el png de C-14.
- `migraciones-esquema`: el ciclo `upgrade → downgrade → upgrade` MUST quedar registrado en `parcial/evidencia/`.

## Impact

- **Archivos**: sólo `parcial/evidencia/` (nuevos `migraciones_ida_y_vuelta.txt` y `C-NN_corrida.txt`; reemplazo de `C-15_consultas_detalle_venta.txt`; eventualmente `C-14_solo_agregado.txt` y `C-14_captura_psql.png`).
- **Código / API / esquema**: ninguno.
- **Entorno**: usa Docker (imagen `postgres:16-alpine` ya descargada), el `.venv` de `parcial/` y un ejecutor de los `.http` fuera del repo (ver design). Los puertos 5432 y 8000 de la máquina están ocupados por otro proyecto: la corrida usa otros puertos sin editar los `.http`.
- **Fuera de alcance**: README de `parcial/` (lo actualiza F-03), casos que no escriben datos (C-01, C-03, C-04, C-06, C-09, RN-15) salvo que el usuario lo pida, rearmado del zip (F-04), `despliegue/evidencia/`.
