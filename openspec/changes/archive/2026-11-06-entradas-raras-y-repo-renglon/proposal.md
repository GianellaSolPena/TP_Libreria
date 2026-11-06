# Proposal

## Why

La segunda auditoría dejó dos requisitos del PDF en "parcial". (1) RN-16 de la tabla de reglas / Ej. 3 ("ninguna entrada inválida termina en un 500", ítems A-038 y B-023): F-01 cerró el U+0000, pero una sonda sobre una base descartable (2026-11-06) reprodujo **27 entradas que todavía responden 500**: un sustituto UTF-16 suelto (`"\ud800"` en JSON, o los bytes `ED A0 80`) en cualquier texto de un cuerpo —títulos, ISBN, nombres, correo, contraseña, teléfono, PATCH, incluso en el nombre de una clave sobrante— y los números JSON sin comillas `NaN`, `Infinity`, `-Infinity` y `1e400` en **cualquier** campo numérico (`precio`, `stock_inicial`, `editorial_id`, `cantidad`, `cliente_id`), no sólo en `precio`. (2) Ej. 6 dice "Cada entidad tiene su repositorio" (A-090, B-100): hay 13 repositorios para 14 entidades; `RenglonVenta` se persiste por cascada desde `Venta.renglones` y no tiene repositorio propio.

## What Changes

- Todo texto de entrada que contenga un sustituto UTF-16 suelto (U+D800–U+DFFF) se rechaza en el contrato con 422, igual que el U+0000 (mismo validador compartido por textos, correos y contraseñas).
- La respuesta 422 de validación del contrato es siempre serializable: conserva la forma actual (`{"detail": [{"type", "loc", "msg", "input", ...}]}`) pero nunca repite tal cual un texto no codificable en UTF-8 ni un número no finito (hoy esos dos casos hacen fallar al propio manejador del 422 y terminan en 500).
- Los números no finitos (`NaN`, `±Infinity`, `1e400` que desborda a infinito) en cualquier campo numérico del cuerpo responden 422.
- Red de seguridad: si un texto llega igual a la base y el driver no lo puede codificar, la operación responde 422 con mensaje propio (hoy relanza y da 500).
- Nuevo repositorio de renglones de venta, compuesto en el Unit of Work de ventas; el registro de la venta da de alta sus renglones por él, en la misma transacción y con el mismo INSERT en lote. Sin cambios en las respuestas ni en la cantidad de consultas del detalle (C-15).
- Casos `.http` nuevos con la respuesta esperada en comentario y su evidencia; `parcial/README.md` los menciona.
- Fuera de alcance: rearmar el zip (F-04, lo hace el usuario a mano con `git archive` después de este change), `despliegue/`, el VPS, migraciones (no cambia el esquema), recortar el eco de cuerpos grandes en el 422 (no es un 500).

## Capabilities

### New Capabilities
<!-- ninguna -->

### Modified Capabilities
- `errores-api`: se agregan requisitos para sustitutos sueltos, números no finitos, 422 siempre serializable y el error de codificación del driver como red de seguridad (RN-15 / Ej. 3).
- `capas-persistencia`: el requisito "Repositorio genérico por entidad" suma el escenario de los renglones de venta con repositorio propio (Ej. 6).

## Impact

- Código (sólo `parcial/`): `app/core/validacion.py` (validador compartido), `app/core/errores.py` (manejador del 422 y red de seguridad del driver), `main.py` (registro del manejador), `app/modules/ventas/repository.py`, `unit_of_work.py` y `service.py`.
- Pruebas/evidencia: `parcial/test/` (archivo `.http` nuevo para RN-15 con sustitutos y no finitos), `parcial/evidencia/` (corrida nueva; C-10/C-15 se revisan por el cambio de ventas), `parcial/README.md`.
- Sin cambios de API para entradas válidas, sin dependencias nuevas, sin migración (`alembic check` sin diferencias).
- Entrega: el zip ya entregado queda desactualizado; el usuario lo rearma a mano (F-04).
