# Design

## Context

Ver proposal.md (Why). Lo observado en la sonda del 2026-11-06 (base `postgres:16-alpine` descartable + uvicorn propio en otro puerto, sin `.env`) separa **dos mecanismos** de 500:

1. **El manejador por defecto del 422 no puede serializar su propia respuesta.** FastAPI responde `{"detail": jsonable_encoder(exc.errors())}` y cada error repite `input` (y a veces `ctx`). Si `input` es un `float('inf')`/`nan` (JSON `NaN`, `Infinity`, `1e400` sin comillas, que Python parsea a float), `JSONResponse` usa `allow_nan=False` → `ValueError: Out of range float values are not JSON compliant` → 500. Si `input` o `loc` contiene un sustituto suelto, `.encode("utf-8")` → `UnicodeEncodeError` → 500. Pasa en **todo** campo numérico (Pydantic ya rechaza bien `Decimal` no finito y `int` desde `inf`, pero el 422 se cae) y en todo error que repita el texto, incluido el caso en que el error es "campo obligatorio faltante" y `input` es el cuerpo entero, o una clave sobrante cuyo nombre trae el sustituto. Los bytes crudos `ED A0 80` también llegan como sustituto: `json.loads` sobre bytes decodifica con `surrogatepass`.
2. **El texto pasa el contrato y el driver no lo puede codificar.** `titulo` de `POST/PATCH /libros` y `nombre` de `PATCH /clientes/{id}`: asyncpg lanza `DataError: invalid input for query argument $N` (causa: `UnicodeEncodeError`), sin SQLSTATE, envuelto en `sqlalchemy.exc.DBAPIError`; `traducir_errores` lo relanza → 500.

Ya funcionan bien (no se tocan): `"NaN"` y `"1e400"` entre comillas (422), enteros enormes en cuerpo/ruta/consulta (422 por `le=INT4_MAX`), `%00` (422, F-01), `%ED%A0%80`/`%FF` en consulta y ruta (Starlette decodifica con `errors="replace"` → U+FFFD → 200 o 422), JSON roto (422), UTF-8 inválido en el cuerpo y anidamiento profundo (400 "There was an error parsing the body"), número de 5000 dígitos (400), títulos de 1 MB (sin 500), cookies/Bearer basura y `alg: none` (401). Las cabeceras llegan como latin-1: no pueden traer sustitutos.

`rechazar_nulo` (en `app/core/validacion.py`) ya es el validador compartido de `TextoSinNulo`, `Email` y `PasswordBcrypt` (29 usos en `app/`).

## Goals / Non-Goals

**Goals:**
- Cero 500 para los 27 reproductores de la sonda, con 422 de la forma estándar.
- Mismo cuerpo de 422 que hoy para toda entrada que ya era serializable (las corridas de `parcial/evidencia/` no cambian).
- `RenglonVentaRepository` real en el flujo de la venta, sin cambiar respuestas, transacción ni número de consultas.

**Non-Goals:**
- Recortar o dejar de repetir `input` en general (los cuerpos grandes se repiten, pero no dan 500).
- Normalizar Unicode (NFC) de los textos: no lo pide el PDF y cambiaría datos guardados.
- Tocar `despliegue/`, migraciones, el zip o el VPS.

## Decisions

### D1. Extender el validador compartido en lugar de crear otro tipo
`rechazar_nulo` pasa a rechazar también cualquier carácter en U+D800–U+DFFF, con un mensaje propio distinto del del nulo ("El texto no puede contener sustitutos UTF-16 sueltos"). Se conserva el nombre de la función y de `TextoSinNulo` para no tocar 29 referencias; se actualiza su docstring (y, si se prefiere, un alias `rechazar_no_representable = rechazar_nulo`; no se renombra). Como `PasswordBcrypt` lo corre antes de `_max_72_bytes`, la contraseña con sustituto da 422 de `value_error` y nunca llega a `encode` ni a bcrypt.
- *Alternativa*: un tipo `TextoValido` nuevo y cambiar todos los esquemas → más diff sin beneficio.
- *Alternativa*: `str.encode("utf-8")` dentro de try → equivalente, pero el rango explícito documenta mejor qué se rechaza.
Los pares válidos (emoji) no se ven afectados: en Python ya llegan como un solo punto de código > U+FFFF.

### D2. Manejador propio de `RequestValidationError` que sanea, no que reescribe
Se registra en `main.py` un manejador definido en `app/core/errores.py` (junto a `traducir_errores`, que ya es el lugar de la traducción de errores) que hace lo mismo que el de FastAPI —`422` con `{"detail": jsonable_encoder(exc.errors())}`— pero pasa el resultado por una función recursiva `_serializable(valor)`:
- `float` no finito → su texto (`"NaN"`, `"Infinity"`, `"-Infinity"`);
- `str` con sustitutos → se reemplazan por su escape visible (`"\\ud800"`, vía `encode("utf-8", "backslashreplace")`), así el cliente ve qué mandó;
- `dict` (claves incluidas) / `list` / `tuple` → recursivo; el resto queda igual.
Para cualquier entrada ya serializable la función es la identidad, así que los 422 actuales (C-01, C-07, C-16, RN-15…) quedan byte a byte iguales. No se agrega `allow_inf_nan` ni validadores de "finito" por campo: Pydantic **ya** rechaza esos valores (`finite_number`, `int_from_float`…); el defecto estaba sólo en la respuesta.
- *Alternativa*: quitar `input`/`ctx` de todos los 422 → cambia la forma de todas las respuestas y la evidencia ya entregada.
- *Alternativa*: `response_class` con `allow_nan=True` → produciría JSON inválido (`NaN` no es JSON).
- *Alternativa*: parsear el cuerpo con `parse_constant` que rechace `NaN`/`Infinity` → no cubre `1e400` ni los sustitutos, e implica tocar el parseo de FastAPI.

### D3. Red de seguridad para el error de codificación del driver
En `traducir_errores`, rama `DBAPIError`: si la cadena de causas de `exc.orig` (`__cause__`/`__context__`) contiene un `UnicodeEncodeError` (asyncpg lo envuelve en `DataError` sin SQLSTATE), responder 422 con `MENSAJE_DATO_INVALIDO`, igual que la lista `DATO_INVALIDO` de F-01. Se reconoce por la **causa**, no por el texto del mensaje, y no se amplía a "todo `DataError`", para no presentar como 422 errores que no son del cliente. Con D1 este camino no debería ejecutarse; queda como defensa en profundidad (RN-15 pide que *ninguna* entrada termine en 500).
- *Checkpoint (MEDIO)*: confirmar en la base descartable que la cadena realmente expone el `UnicodeEncodeError` (la traza de la sonda lo muestra como causa). Si no lo expusiera, detenerse y consultar antes de elegir otro criterio.

### D4. `RenglonVentaRepository` con alta en lote
Alcance según la consigna: "Cada entidad tiene su repositorio, con métodos que se nombran por lo que traen" + `BaseRepository[T]` con `add`/`update` que hacen `flush()`. Se agrega en `app/modules/ventas/repository.py`:
`class RenglonVentaRepository(BaseRepository[RenglonVenta])` con un método `add_varios(renglones) -> list[RenglonVenta]` (`session.add_all` + **un** `flush`, nunca `commit`). `VentasUnitOfWork` expone `self.renglones`. En `ventas/service.py::crear`: se arma la venta sin asignar `venta.renglones`, `await uow.ventas.add(venta)` (INSERT de la venta, obtiene id), se fija `venta_id` en cada renglón y `await uow.renglones.add_varios(renglones)`; el resto (movimientos en orden de `libro_id`, `get_detalle` con `populate_existing`) no cambia.
- Un solo `flush` mantiene el INSERT en lote (`insertmanyvalues`) que hoy se ve en `parcial/evidencia/C-15_consultas_detalle_venta.txt`; usar `add` por renglón daría un INSERT por renglón.
- No se toca `Venta.renglones` (sigue `lazy="raise_on_sql"`, sin cascada nueva ni migración); el detalle sigue leyéndose con `selectinload` en `get_detalle`, así que el GET con 2 y con 4 renglones mantiene sus SELECT fijos.
- Sólo el alta pasa por el repositorio nuevo: no hay otras lecturas de renglones fuera de la precarga del detalle, y no se inventan métodos que nadie usa (más allá de los heredados).
- *Alternativa*: dejar la cascada y agregar un repositorio sin uso → no responde a la observación de la auditoría.
- `seed.py` sigue insertando renglones con la sesión directa (no es una operación de la API; fuera del alcance de las capas).

### D5. Verificación manual (DD-01, sin pytest)
Archivo nuevo `parcial/test/RN-15b_sustitutos_y_no_finitos.http` (el de F-01 queda como está) con los reproductores representativos y la respuesta esperada en comentario; un script de sonda en el scratchpad recorre los 27 casos y las regresiones. Todo sobre `postgres:16-alpine` descartable + uvicorn propio en un puerto ≠ 8000, corrido desde un directorio sin `.env` y con variables de entorno temporales; el contenedor se borra al final.

## Risks / Trade-offs

- [El manejador propio deja de seguir mejoras futuras del de FastAPI] → replica exactamente su forma (`detail` = `jsonable_encoder(exc.errors())`) y se verifica igualdad byte a byte de los 422 de la evidencia.
- [Reemplazar el sustituto en `input` cambia lo que el cliente ve] → sólo para entradas que hoy dan 500; se usa el escape visible.
- [El cambio en `crear` altera el orden de los INSERT o la cantidad de consultas] → comparar el log `SQL_ECHO` del POST de C-15 con la evidencia: mismo INSERT de venta, un INSERT en lote de renglones, mismos movimientos; GET con 2 y 4 renglones con la misma cantidad de SELECT.
- [Detectar el error del driver por causa depende de cómo asyncpg encadena] → checkpoint D3; si cambia la versión de asyncpg, D1 sigue cubriendo el contrato.
- [El zip entregado queda desactualizado] → el usuario lo rearma a mano con `git archive` desde el commit nuevo (F-04); no comprimir carpetas (hay `.env`, `.venv` y `__pycache__` locales).

## Migration Plan

Sin migración de esquema (`alembic check` debe dar "No new upgrade operations detected"). Despliegue: no aplica (`despliegue/` no recibe el parcial). Rollback: revertir el commit.
