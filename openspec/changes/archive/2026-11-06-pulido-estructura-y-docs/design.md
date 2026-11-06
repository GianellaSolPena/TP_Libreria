# Design

## Context

Lo que se encontró al proponer (2026-11-06, sólo lectura):

- **`parcial/app/core/dependencies.py`** define `SesionActual`, `get_usuario_actual` (lee la cookie, verifica el token, abre un `UnitOfWork` base de sólo lectura sobre la sesión de `get_session` y usa `UsuarioRepository` y `AsignacionRolRepository` para traer el usuario y sus roles vigentes), `UsuarioActualDep`, `requiere_rol` (con `solo_admin` y `personal`) y `exigir_password_al_dia`. Importa `Rol`, `Usuario` de `app.modules.usuarios.models` y los dos repositorios de `app.modules.usuarios.repository`. Lo usan los routers de autores, clientes, editoriales, géneros, libros, usuarios y ventas, y `ventas/service.py` (sólo el tipo `SesionActual`).
- **PDF, «Estructura obligatoria del proyecto» (p. 8)**, fila literal: `app/core/dependencies.py` — «Usuario actual, roles vigentes, control del cambio obligatorio y `requiere_rol`». La organización es «por módulo funcional, con las mismas capas en todos los módulos»; `AsignacionRol` vive en `usuarios`. No dice nada sobre de dónde puede importar `core`.
- **`despliegue/DEPLOY.md`**: líneas de comando de más de 100 caracteres en los bloques de las l. 19 (`tar … | ssh …`), 42 (`docker run … --network …`), 43 y 127 (`docker exec … psql …`), 107 y 137 (`docker run` genérico). Las l. 19 y 42 tienen tramos de varios espacios seguidos donde evidentemente hubo saltos de línea con `\` que se perdieron.
- **`app/` en la raíz**: no existe (`ls app` → «No such file or directory»; `git status --short --ignored` sólo lista `.atl/` como ignorado). La auditoría la vio antes; algo la borró o era de otra copia de trabajo.
- **`parcial/README.md`**: la tabla de «Casos de prueba» tiene C-01..C-16 pero no `RN-15_caracter_nulo.http` (agregado en F-01); «Estructura» y la tabla nombran sólo la evidencia de C-14 y C-15. F-02 (en paralelo) agregará en `parcial/evidencia/` la salida de `upgrade → downgrade → upgrade`, las corridas reales de los casos que escriben datos y la captura cruda de C-15; los nombres exactos los define F-02.
- **KB 08 §Estructura** (l. 32) todavía dice que `main.py` «hoy vive en `app/main.py`: ver Q-03», desactualizado desde C-02 / DD-08.
- Último DD de `knowledge-base/09`: **DD-10**.

## Goals / Non-Goals

**Goals:**
- Dejar registrada y justificada la ubicación de `dependencies.py` (DD-11) para que el corrector y el grupo la puedan defender.
- `DEPLOY.md` legible y copiable, con los mismos comandos.
- README coherente con `parcial/test/` y `parcial/evidencia/` después de F-01 y F-02.

**Non-Goals:**
- Mover o reescribir `dependencies.py`, cambiar rutas, respuestas o esquema.
- Tocar la lógica de `despliegue/` (sólo el texto de `DEPLOY.md`).
- Rearmar el zip (F-04) o editar `CHANGES.md`.
- Los opcionales no son condición para cerrar el change.

## Decisions

### D1 — `dependencies.py` se queda en `app/core/` (a confirmar por el usuario) → DD-11

**Decisión**: no se mueve. Se agrega DD-11 en `knowledge-base/09_decisiones_y_supuestos.md`.

**Por qué (del PDF)**:
1. La tabla de la p. 8 fija la **ruta exacta** `app/core/dependencies.py` y le asigna exactamente lo que hoy contiene: usuario actual, roles vigentes, control del cambio obligatorio y `requiere_rol`. Moverlo a `app/modules/usuarios/` **rompería** la letra del PDF (la regla 12 del proyecto: el PDF manda).
2. «Roles vigentes» se leen de `asignacion_rol` en cada petición (RN-04, regla dura 8), y el PDF ubica `AsignacionRol` en `usuarios`. Cualquier implementación de lo que el PDF pide en `core/dependencies.py` tiene que usar el modelo/repositorio de `usuarios`: la dependencia `core → modules.usuarios` es consecuencia directa de la consigna, no un desvío.
3. Las capas siguen respetadas: `get_usuario_actual` es una dependencia de FastAPI (nivel router): recibe la sesión de `get_session`, arma el UoW y los repositorios, y ningún servicio recibe `AsyncSession` (regla dura 1). Es el mismo papel que cumple un router.

**Alternativas consideradas**:
- *Mover todo a `app/modules/usuarios/dependencies.py`*: rechazada, contradice la ruta del PDF y obliga a tocar 8 imports sin ganancia funcional.
- *Dejar en `core` sólo `requiere_rol`/`exigir_password_al_dia` y mover `get_usuario_actual` a `usuarios`*: rechazada, parte en dos lo que el PDF agrupa en una sola fila.
- *Usar `UsuariosUnitOfWork` en lugar de `UnitOfWork` + repos sueltos*: equivalente, pero ese UoW arrastra repositorios que la dependencia no usa (clientes, eventos, intentos) y cambiaría código ya verificado; no se hace.

**Observación (sin acción)**: `ventas/service.py` importa el tipo `SesionActual` de `core/dependencies.py` para la comprobación de dueño (RN-14). Es sólo un tipo de datos, no abre sesiones ni depende de HTTP; se menciona en DD-11 para que quede explicado.

### D2 — `DEPLOY.md`: partir con `\`, mismo comando

Cada comando de más de ~100 caracteres se parte en el límite natural de las opciones (`--exclude …`, `-p`, `--network`, `--env-file`, la tubería `|`), con `\` al final y sangría de dos espacios en las continuaciones. El `sh -c '…'` del `docker exec` se parte **fuera** de las comillas simples (antes de `sh -c`), para no alterar la cadena que interpreta el contenedor. Verificación: unir las líneas (`sed ':a;/\\$/{N;s/\\\n *//;ba}'`) y comparar con el texto original salvo espacios.

### D3 — `app/` suelta: verificación, no borrado a ciegas

Como no existe, la tarea es comprobar de nuevo al aplicar; si reapareció, listar su contenido con `find app -type f` y borrar sólo si todo está bajo `__pycache__`. Cualquier otro archivo frena la tarea y se consulta.

### D4 — README después de F-02

La fila de RN-15 y la corrección de la línea de `test/` en «Estructura» se hacen ya. Los archivos nuevos de `parcial/evidencia/` se agregan cuando F-02 esté aplicado, tomando los nombres reales con `ls parcial/evidencia/` (no se inventan nombres).

### D5 — Opcionales

- `.http` RN-03: `POST /usuarios/{id}/roles` con un rol que ya está vigente → 409 «El usuario ya tiene ese rol vigente» (el 409 sale del índice único parcial, no de un `SELECT` previo).
- `.http` token vencido: requiere arrancar el servidor con `ACCESS_TOKEN_EXPIRE_SECONDS` chico (p. ej. 5), loguear, esperar y pedir `/auth/yo` → 401. Va en un archivo aparte con la condición indicada.
- Escape de `%` y `_` en `titulo`: hoy `ilike(f"%{titulo}%")` es seguro (parámetro ligado), sólo que `%`/`_` actúan de comodines. Escaparlos con `escape="\\"` en el repositorio de libros; ampliar C-16 o un `.http` extra con `titulo=%25` (no debe devolver todo).

## Risks / Trade-offs

- [El corrector podría leer `core → modules` como violación de capas] → DD-11 lo explica con la fila literal del PDF; el usuario confirma la decisión antes de aplicar.
- [Partir mal un comando de `DEPLOY.md` lo rompe] → verificación de igualdad al unir líneas (D2); no se cambia ningún argumento.
- [F-02 se demora o cambia nombres de archivos] → la tarea del README que depende de F-02 queda abierta y el change no se archiva sin ella (o se archiva sólo si el usuario lo decide).
- [Opcionales tocan código] → se hacen sólo si el usuario los pide; si se hace el escape, regresión con C-16.
