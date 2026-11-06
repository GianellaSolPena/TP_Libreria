# Tasks

> Sin pytest (DD-01): cada tarea se verifica con `.http` contra uvicorn, `curl`, la consola de uvicorn o `grep`. Comandos desde `parcial/`. Governance MEDIO: los **CHECKPOINT** detienen el trabajo y se reportan al usuario antes de seguir. No se toca `despliegue/` ni el zip de `C:\Users\agusf\Desktop\Entrega_Parcial\` ni el VPS; no se commitea sin pedido.

## 1. Línea base (antes de tocar código)

- [x] 1.1 **CHECKPOINT — base de datos**: `python seed.py` hace `TRUNCATE` (DD-10). Confirmar con el usuario qué base usar (la local de desarrollo de los changes anteriores o un contenedor descartable `postgres:16-alpine`) antes del primer seed; anotar aquí la elegida. Verificación: respuesta del usuario anotada
- [x] 1.2 Con la base migrada (`alembic upgrade head`), `python seed.py` y `uvicorn main:app`, reproducir los dos defectos: `curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/libros?titulo=a%00b"` y `curl -s -w "\n%{http_code}" -H "Content-Type: application/json" -d '{"email":"admin\u0000@example.com","password":"admin1234"}' http://localhost:8000/auth/login`; verificación: ambos responden 500 y la traza de uvicorn muestra el SQLSTATE; anotar aquí el código y la clase de excepción
- [x] 1.3 **CHECKPOINT — SQLSTATE**: confirmar que la excepción es un `DBAPIError` de SQLAlchemy (p. ej. `DataError`) con `exc.orig.sqlstate == "22021"` (design D2). Si es otra clase, no tiene `sqlstate` o falla del lado de asyncpg antes de enviar, detenerse y reportar: D2 cambia. Verificación: código observado anotado aquí
- [x] 1.4 Correr como línea base `test/C-01_parametro_no_entero.http`, `C-02_registro_correo_repetido.http`, `C-03_cookie_login.http`, `C-04_credenciales_indistinguibles.http`, `C-05_limite_intentos.http` y `C-16_busqueda_paginacion_patch.http` (con `python seed.py` antes de cada uno) y anotar que coinciden con sus comentarios; si alguno falla, detenerse y reportarlo como falla previa (no se corrige en F-01)

## 2. Red de seguridad en `traducir_errores` (D2)

- [x] 2.1 En `app/core/errores.py`: agregar `DATO_INVALIDO` (22021, 22P05, 22P02, 22001, 22007, 22008, cada uno con su nombre en comentario) y `MENSAJE_DATO_INVALIDO`; en la rama `except DBAPIError` mantener 22003 → 409 y agregar `sqlstate in DATO_INVALIDO` → `HTTPException(422, MENSAJE_DATO_INVALIDO) from None`; el resto sigue con `raise`; actualizar el comentario de la rama. Verificación: con uvicorn reiniciado, los dos `curl` de 1.2 responden 422 con cuerpo exacto `{"detail":"Algún dato enviado no es válido"}`, sin `invalid byte sequence`, `0x00`, SQLSTATE ni nombres de tablas; la consola de uvicorn no muestra traza
- [x] 2.2 Comprobar que la red no tapa los 409: alta de editorial duplicada (`POST /editoriales` con «Emecé» como ADMIN) → 409 «Ya existe una editorial con ese nombre»; `POST /libros/1/reponer` con `cantidad` 2147483647 → 409 «El valor supera el máximo permitido». Verificación: códigos y mensajes anotados aquí

## 3. Rechazo de U+0000 en el contrato (D1)

- [x] 3.1 Crear `app/core/validacion.py` con `rechazar_nulo` y `TextoSinNulo = Annotated[str, AfterValidator(rechazar_nulo)]` (sin imports de la app). Verificación: `python -c "from app.core.validacion import TextoSinNulo"` sin errores
- [x] 3.2 Aplicar `TextoSinNulo` a los campos de texto de entrada del inventario del design en `editoriales`, `generos`, `autores` y `libros` (`schemas.py`), conservando `min_length`/`default`. Verificación: `POST /generos` con `{"nombre": "Ens\u0000ayo"}` (ADMIN) → 422 `loc ["body","nombre"]`; `PATCH /libros/1` con título con `\u0000` → 422; alta de género válido → 201
- [x] 3.3 Aplicar a `clientes/schemas.py` (`nombre`, `telefono`, `direccion` y el `Email` local con `AfterValidator(rechazar_nulo)`). Verificación: `POST /clientes` (VENDEDOR) con correo con `\u0000` → 422 `loc ["body","email"]`; `POST /clientes/{id}/perfil` con dirección con `\u0000` → 422
- [x] 3.4 Aplicar a `usuarios/schemas.py` (`Email` con `rechazar_nulo` antes de `_normalizar_email`, `nombre`) y a `PasswordBcrypt` en `core/security.py` (antes de `_max_72_bytes`). Verificación: el `curl` de login de 1.2 → 422 con `detail` lista y `loc ["body","email"]` (ya no la cadena de 2.1); login con `\u0000` en la contraseña → 422; `POST /auth/registro` con nombre con `\u0000` → 422; `SELECT count(*) FROM intento_acceso` no cambia con esos 422
- [x] 3.5 En `libros/router.py`, `titulo: Annotated[TextoSinNulo | None, Query()] = None`. Verificación: `GET /libros?titulo=a%00b` → 422 con `loc ["query","titulo"]`; `GET /libros?titulo=ficc` → 200 total 1; `GET /libros?titulo=%27%20OR%20%271%27%3D%271` → 200 total 0
- [x] 3.6 **CHECKPOINT — cobertura**: `grep -n ": str\b\|: str |\|: str =" app/modules/*/schemas.py` y revisar que cada coincidencia restante es de un esquema de salida (`*Read`/`*Out`) o un `Literal`/enum; cualquier `str` de entrada sin `TextoSinNulo` se corrige o se reporta. Verificación: lista revisada anotada aquí

## 4. Caso `.http` extra (D4)

- [x] 4.1 Crear `parcial/test/RN-15_caracter_nulo.http` con el estilo de `C-01_parametro_no_entero.http` (precondiciones, credenciales del seed, `# @name`/`# @no-cookie-jar`/`Cookie:`) y las peticiones (a)..(h) de D4, cada una con `# Esperado:`. Verificación: tras `python seed.py`, correrlo completo contra uvicorn; todas las respuestas coinciden con los comentarios y ninguna es 500

## 5. Regresión e integración

- [x] 5.1 Re-correr los `.http` de 1.4 (seed antes de cada uno) y además `C-06`, `C-09`, `C-10`, `C-12` y `C-13` (tocan cuerpos con textos: login, registro, cambio de contraseña, altas de libro y clientes). Verificación: mismas respuestas que la línea base y que sus comentarios; la consola de uvicorn sin `Traceback` ni 500
- [x] 5.2 Cookie: `curl -s -w "\n%{http_code}" -H "Cookie: access_token=abc%00def" http://localhost:8000/auth/yo` → 401 «No autenticado», no 500 (D5)
- [x] 5.3 Capas: `grep -rn "AsyncSession\|commit(\|rollback(" app/modules/*/service.py` vacío; `grep -rn "commit(\|rollback(" app/modules/*/router.py` vacío; `AsyncSession` en routers sólo en las dependencias que construyen el UoW y `async_sessionmaker` sólo en `get_intentos_uow` (DD-09); `grep -rn "exception_handler" main.py app` vacío (sin manejador global). Verificación: salida anotada aquí
- [x] 5.4 Alcance: `git status --short` muestra cambios sólo en `parcial/app/core/{errores,validacion,security}.py`, `parcial/app/modules/*/schemas.py`, `parcial/app/modules/libros/router.py`, `parcial/test/RN-15_caracter_nulo.http` y `openspec/changes/entradas-invalidas-nul/`; nada en `despliegue/`, `parcial/migrations/` ni el zip. Verificación: salida anotada aquí
- [x] 5.5 Marcar F-01 `[x]` en `CHANGES.md` (estado y tabla Resumen) y mover «Próximo change» a F-02 en `CHANGES.md`, `CLAUDE.md` y `AGENTS.md` (`diff CLAUDE.md AGENTS.md` vacío). Verificación: diff vacío y líneas actualizadas

## Notas de aplicación (2026-11-06)

- 1.1: base elegida por el usuario = contenedor descartable `postgres:16-alpine` (base `libreria_f01`); no se tocó la base local.
- 1.2/1.3: antes del arreglo ambos reproductores respondieron 500; excepción `sqlalchemy.exc.DBAPIError` (genérica) con `exc.orig.sqlstate == "22021"` (`asyncpg CharacterNotInRepertoireError`, `invalid byte sequence ... 0x00`). Confirmado D2.
- 2.1: con sólo la red de seguridad, ambos reproductores → 422 `{"detail":"Algún dato enviado no es válido"}`. 2.2: editorial duplicada → 409 «Ya existe una editorial con ese nombre»; reponer 2147483647 → 409 «El valor supera el máximo permitido».
- 3.x: con el contrato, los reproductores → 422 con `detail` lista (`loc` body.email / query.titulo); `intento_acceso` sin cambios con esos 422. 3.6: los `str` restantes son de esquemas `*Read`/`*Out`.
- 5.x: regresión C-01..C-06, C-09, C-10, C-12, C-13, C-16 y RN-15 coinciden con sus comentarios (verificado con un runner local; C-06d y C-10f dependen de `{{nombre.response.body.$.id}}`, que ese runner no resuelve); sin `Traceback` ni 500 en uvicorn.
