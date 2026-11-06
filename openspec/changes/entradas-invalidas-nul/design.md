# Design

## Context

Ver `proposal.md` (Why) y los deltas `specs/errores-api` y `specs/casos-prueba`.

Estado observado en `parcial/` (FastAPI 0.162, Pydantic 2.14, SQLAlchemy 2.1, asyncpg, bcrypt 5.0 en `.venv`):

- **Ningún contrato rechaza U+0000.** Los textos se declaran como `str = Field(min_length=1)` (catálogo, libros, clientes), `str = Field(min_length=1, max_length=120)` (nombre en registro/personal), `Email` con `StringConstraints(pattern=r"^[^@\s]+@[^@\s]+$")` (definido dos veces: `usuarios/schemas.py` con `AfterValidator(_normalizar_email)` y `clientes/schemas.py` sin normalizar; `\s` no incluye `\x00`, comprobado: `'a\x00@b.com'` pasa) y `PasswordBcrypt` en `core/security.py` (`min_length=1` + `_max_72_bytes`).
- **Inventario de textos de entrada** (lo que hay que cubrir):

  | Origen | Campos |
  |--------|--------|
  | `editoriales/schemas.py` | `EditorialCreate.nombre, pais`; `EditorialUpdate.nombre, pais` |
  | `generos/schemas.py` | `GeneroCreate.nombre`; `GeneroUpdate.nombre` |
  | `autores/schemas.py` | `AutorCreate.nombre, nacionalidad`; `AutorUpdate.nombre, nacionalidad` |
  | `libros/schemas.py` | `LibroCreate.isbn, titulo`; `LibroUpdate.titulo` |
  | `clientes/schemas.py` | `ClienteCreate.nombre, email`; `ClienteUpdate.nombre, email`; `PerfilCreate.telefono, direccion` |
  | `usuarios/schemas.py` | `RegistroIn.email, nombre, password`; `LoginIn.email, password`; `CambiarPasswordIn.password_actual, password_nueva`; `PersonalIn.email, nombre, password` |
  | Query | `GET /libros?titulo=` (`libros/router.py`, `titulo: str \| None = Query(None)`) |

  Ya cerrados por tipo (no necesitan cambio): `LibroAutorCreate.rol` (`Literal`), `PersonalIn.rol` / `AsignarRolIn.rol` / ruta `{rol}` (enum `Rol`), `vence_en` (`AwareDatetime`), todos los ids/cantidades/`page`/`size`/`genero_id` (enteros acotados). `ventas/schemas.py` no tiene textos de entrada. No hay parámetros de ruta de texto libre ni encabezados leídos como datos (la `ip` sale de `request.client`). Los esquemas `*Read`/`*Out` son de salida y no se tocan.
- **Columnas**: todas `AutoString` sin largo (VARCHAR sin límite): no hay truncamiento (22001) posible hoy.
- **`traducir_errores`** (`core/errores.py`) envuelve el cuerpo de **todos** los handlers que tocan la base (verificado en los 8 routers; `health` no la usa y no recibe texto). Su rama `DBAPIError` convierte sólo 22003 en 409 y relanza el resto → 500 (sin texto de la base, pero 500).
- **Formas de 422 existentes**: (a) validación del contrato de FastAPI: `{"detail": [{"type", "loc", "msg", "input", "ctx"?}]}`; (b) 422 del dominio vía `HTTPException`: `{"detail": "La página 4 no existe: hay 3"}` (cadena). No hay `exception_handler` propios en `main.py`.
- **Cookie/JWT**: `get_usuario_actual` lee la cookie, `leer_token` captura `jwt.InvalidTokenError` y `ValueError` y devuelve `None` → 401; el `sub` sale de un token firmado y se convierte a `int`. Ningún texto de la cookie llega a la base.

## Goals / Non-Goals

**Goals:**
- Rechazo de U+0000 en el contrato para cada campo del inventario (422 estándar de FastAPI), con un único tipo reutilizable para que un campo nuevo no se olvide.
- Red de seguridad en `traducir_errores` para errores de dato de la base que se escapen al contrato: 422 con mensaje propio, sin texto de la base, sin tapar errores reales.
- Verificación manual (DD-01): caso `.http` extra, curl de los dos reproductores, regresión de los casos existentes y grep de capas.

**Non-Goals:**
- Rechazar otros caracteres de control (U+0001..U+001F, U+007F): PostgreSQL los acepta, no producen 500 y el PDF no lo pide.
- Normalizar o recortar textos (salvo el correo de `usuarios`, que ya se normaliza), agregar `max_length` a campos que hoy no lo tienen o cambiar mensajes de validación existentes.
- Un manejador global de excepciones en `main.py`, cambios de esquema o migraciones, `despliegue/`, README (F-03), evidencia (F-02), zip (F-04).

## Decisions

### D1 — Tipo `TextoSinNulo` en `app/core/validacion.py`, aplicado por anotación

```python
def rechazar_nulo(valor: str) -> str:
    if "\x00" in valor:
        raise ValueError("El texto no puede contener el carácter nulo (U+0000)")
    return valor

TextoSinNulo = Annotated[str, AfterValidator(rechazar_nulo)]
```

- Los campos pasan de `nombre: str = Field(min_length=1)` a `nombre: TextoSinNulo = Field(min_length=1)` (Pydantic fusiona la metadata del `Annotated` con la de `Field`); opcionales: `TextoSinNulo | None = Field(default=None, min_length=1)`. Las restricciones existentes (`min_length`, `max_length`) no cambian.
- `Email` (en los dos módulos) y `PasswordBcrypt` agregan `AfterValidator(rechazar_nulo)` **antes** de sus validadores actuales (en `Email` de `usuarios`, antes de `_normalizar_email`, así el error no depende de la normalización). Las contraseñas también lo rechazan: bcrypt 5 acepta `\x00` (comprobado), pero «cualquier texto» incluye la contraseña, la regla es una sola y evita que un `0x00` se trate distinto según el campo; no hay contraseñas con `\x00` en el seed.
- Query: `titulo: Annotated[TextoSinNulo | None, Query()] = None` en `listar_libros`. FastAPI aplica los validadores de `Annotated` a parámetros de consulta y el error sale con `loc: ["query", "titulo"]`.
- **Ubicación**: módulo nuevo en `app/core/` (junto a `paginacion.py`/`errores.py`), porque lo usan seis módulos y `core/security.py`; `errores.py` queda para traducción de errores (ya aloja `IdPath`, pero mezclar validadores de texto ahí lo vuelve un cajón de sastre). `security.py` importa de `validacion.py` (sin ciclo: `validacion.py` no importa nada de la app).
- **Alternativas descartadas**: (a) un `model_validator` en una clase base que recorra todos los `str` — implícito, también tocaría los esquemas de salida y no cubre query params; (b) cambiar el patrón del correo a `[^@\s\x00]` — mensaje de error críptico y no sirve para los demás campos; (c) un middleware que rechace `\x00` en el cuerpo crudo/URL — no conoce el campo (`loc`), devolvería una forma de 422 distinta y vería también `\u0000` escapado en JSON de forma frágil.
- **Respuesta resultante** (forma estándar, igual que C-01): `422 {"detail": [{"type": "value_error", "loc": ["body", "email"], "msg": "Value error, El texto no puede contener el carácter nulo (U+0000)", "input": "admin\u0000@example.com", "ctx": {...}}]}`. El `input` ecoa lo que mandó el cliente (como cualquier 422 de FastAPI): no es texto de la base.

### D2 — Red de seguridad: SQLSTATE de dato inválido → 422 en `traducir_errores`

En la rama `except DBAPIError` (que ya excluye `IntegrityError` porque esa rama va antes):

```python
NUMERIC_VALUE_OUT_OF_RANGE = "22003"          # sigue → 409 MENSAJE_DESBORDE
DATO_INVALIDO = frozenset({
    "22021",  # character_not_in_repertoire (p. ej. 0x00 en UTF-8)
    "22P05",  # untranslatable_character
    "22P02",  # invalid_text_representation
    "22001",  # string_data_right_truncation
    "22007",  # invalid_datetime_format
    "22008",  # datetime_field_overflow
})
MENSAJE_DATO_INVALIDO = "Algún dato enviado no es válido"
...
sqlstate = getattr(exc.orig, "sqlstate", None)
if sqlstate == NUMERIC_VALUE_OUT_OF_RANGE:
    raise HTTPException(409, MENSAJE_DESBORDE) from None
if sqlstate in DATO_INVALIDO:
    raise HTTPException(422, MENSAJE_DATO_INVALIDO) from None
raise
```

- **Lista explícita, no toda la clase 22**: la clase 22 también incluye errores que sólo pueden venir de un defecto propio (22012 división por cero, 22004 nulo no permitido, 22023 parámetro inválido de una función); convertirlos en 422 culparía al cliente y ocultaría un bug. La lista contiene sólo códigos que, con parámetros ligados, únicamente provienen de un valor enviado por el cliente. Lo que no está en la lista sigue relanzándose (500 sin texto de la base, comportamiento actual).
- **Sin texto de la base**: mensaje fijo y `from None` (igual que las ramas 409), así el `__cause__` no viaja en la traza que pudiera mostrar un depurador; FastAPI sólo serializa `detail`.
- **Forma**: `HTTPException(422, "<cadena>")` → `{"detail": "Algún dato enviado no es válido"}`, la misma forma que el otro 422 que nace después del contrato (página inexistente). No puede usar la forma de lista porque no se sabe qué campo falló (la base no lo dice de forma fiable y no se debe exponer su texto).
- **409 intacto**: `IntegrityError` se atiende en su rama anterior (orden de `except` sin cambios) y 22003 conserva su 409 (spec «Desborde numérico de la base traducido a 409»).
- **Transacción**: el error ocurre dentro del `async with uow`, que hace rollback al propagarse la excepción; `traducir_errores` envuelve por fuera del servicio, así que no quedan escrituras. En login, si el error saliera en la consulta del conteo de intentos (UoW propio, DD-09), tampoco se escribe nada.
- **Sin manejador global**: la regla de capas dice que el router traduce; todos los handlers con base ya usan `traducir_errores`, así que la red cubre toda la API sin tocar `main.py`.
- **Checkpoint de implementación**: antes de escribir D2 se reproduce el 500 y se confirma en la consola de uvicorn que el SQLSTATE real es 22021 y que `exc.orig.sqlstate` está presente (la rama 22003 ya depende de ese atributo, pero se verifica para este caso). Si asyncpg fallara del lado del cliente antes de enviar (otra excepción, sin `sqlstate`), se detiene y se reporta: D2 cambiaría.

### D3 — Orden de implementación que prueba las dos capas por separado

1. Línea base: reproductores → 500.
2. D2 primero: los mismos reproductores dan 422 con `detail` cadena (la red de seguridad funciona de verdad, no sólo en teoría).
3. D1 después: los reproductores dan 422 con `detail` lista (el contrato corta antes de la base).

Así cada requisito del delta de `errores-api` tiene una observación real, sin pytest (DD-01) y sin código de prueba temporal.

### D4 — Caso `.http` extra: `parcial/test/RN-15_caracter_nulo.http`

- Nombre sin número C para no confundirlo con los casos del PDF (C-01..C-16); prefijo `RN-15` por la regla que demuestra. Mismas convenciones que `C-01_parametro_no_entero.http`: encabezado con precondiciones (`alembic upgrade head`, `python seed.py`, `uvicorn main:app`), variables `@host`/credenciales del seed, `# @name` + `# @no-cookie-jar` + `Cookie:` por sesión, y comentario `# Esperado:` en cada petición.
- Peticiones: (a) `GET /libros?titulo=a%00b` → 422 `loc ["query","titulo"]`; (b) `POST /auth/login` con `"admin\u0000@example.com"` → 422 `loc ["body","email"]`; (c) login con `\u0000` en la contraseña → 422; (d) login ADMIN válido → 200; (e) `POST /generos` con `"Ens\u0000ayo"` → 422; (f) `PATCH /libros/1` con título con `\u0000` → 422; (g) `POST /auth/registro` con nombre con `\u0000` → 422; (h) control: `GET /libros?titulo=ficc` → 200 total 1. El U+0000 viaja como escape JSON `\u0000` en los cuerpos (REST Client no puede escribir el byte crudo) y como `%00` en la URL.
- Lo agrega al README la change F-03 (fuera de este alcance).

### D5 — JWT y cookie: sin cambios

Ningún texto de la cookie llega a la base: `leer_token` valida firma y `exp` y convierte `sub` a `int` capturando `InvalidTokenError`/`ValueError` (→ 401). Se agrega una sola comprobación de regresión (cookie `access_token` basura con `%00` → 401, no 500) en las tareas, sin código nuevo.

## Risks / Trade-offs

- [Un campo de texto nuevo declarado como `str` pelado se saltea D1] → La red de D2 lo convierte en 422 igual (nunca 500); y la tarea de grep final lista los `: str` de los esquemas de entrada para revisarlos.
- [D2 podría clasificar como 422 un error de dato que en realidad es un defecto propio] → Lista explícita y acotada a códigos que con parámetros ligados sólo vienen de la entrada; todo lo demás sigue siendo 500.
- [El 422 de D2 no dice qué campo falló] → Aceptado: es la red de seguridad; el caso normal lo corta D1 con `loc`. Decirlo exigiría leer el texto de la base (prohibido por RN-15).
- [Cambio de comportamiento del login: U+0000 en correo/contraseña daba 500 y ahora 422 sin contar intento] → Coherente con los demás 422 del contrato (correo mal formado, contraseña > 72 bytes tampoco cuentan); C-04/C-05 no usan U+0000, no cambian.
- [El `input` del 422 de FastAPI ecoa el texto del cliente] → Es el comportamiento ya aceptado en C-01 y demás 422; no contiene datos de la base.
- [El zip entregado queda desactualizado] → Explícito en el plan: F-04 lo rearma sólo con pedido del usuario.

## Migration Plan

Sin migración ni cambios de esquema. Despliegue = reiniciar uvicorn en `parcial/`. Rollback = revertir el commit (los cambios son anotaciones de tipo y una rama del `except`).
