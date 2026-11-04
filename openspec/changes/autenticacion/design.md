# Design

## Context

Motivo y alcance: ver `proposal.md`. Requisitos: `specs/autenticacion/spec.md` y `specs/intentos-acceso/spec.md`.

Estado actual de `parcial/` (observado):
- `app/core/config.py`: `Settings` ya tiene `JWT_SECRET_KEY` (sin default), `ACCESS_TOKEN_EXPIRE_SECONDS=1800`, `BCRYPT_ROUNDS=12`, `COOKIE_SECURE=False` (Q-04, C-02).
- `main.py` (lifespan): motor, fábrica y `app.state.hash_ficticio` calculado con `asyncio.to_thread(bcrypt.hashpw, b"hash-ficticio", ...)` — placeholder de C-02: sin semáforo y sobre una constante conocida.
- `app/modules/usuarios/models.py`: `Usuario` (email UNIQUE `uq_usuario_email`, nombre, password_hash, activo, debe_cambiar_password), `AsignacionRol` (índice único parcial abierto), `IntentoAcceso` (índice `(email, ip, cuando)`), `EventoSeguridad` (cuando, actor texto, accion). Sin schemas/repos/servicio/router.
- `app/modules/clientes/models.py`: `Cliente` con `uq_cliente_email` y `usuario_id` nulo UNIQUE. El módulo `clientes` sigue con el patrón del TP (sin repositorio) hasta C-07.
- `app/core/`: `UnitOfWork` base (commit al salir, rollback con excepción, no cierra), `BaseRepository[T]`, `get_session` (no confirma), `errores.traducir_errores` (23505 → 409 con mensaje propio).
- Librerías instaladas: `bcrypt` 5.0 (lanza `ValueError` con > 72 bytes), `PyJWT` 2.15 (exige `sub` string).

Restricciones: reglas duras de `CLAUDE.md` (capas, 72 bytes, bcrypt fuera del bucle, sin defaults de secretos, roles de la base, sin pytest), consigna Ej. 4 y Ej. 7 (el PDF manda).

## Goals / Non-Goals

**Goals:**
- Los cinco endpoints de `/auth` con el orden de login de la sección 5.5 y el `intento_acceso` aislado en un solo lugar comentado.
- Ninguna operación bcrypt con una conexión de la base tomada.
- Dejar `get_usuario_actual` y `roles_vigentes` listos para que C-06 los reutilice sin reescribirlos.

**Non-Goals:**
- Autorización por rol, control del cambio obligatorio, dos grupos de rutas (C-06). En C-05 las rutas existentes siguen abiertas.
- Revocar tokens / lista negra: la sesión dura hasta `exp` o logout (consigna).
- Normalización avanzada de correos (sólo minúsculas y recorte de espacios, ver D10).

## Decisions

### D1 — Frontera C-05 / C-06
C-05 crea `app/core/dependencies.py` con **`get_usuario_actual` completo** (401 sin cookie, token inválido/vencido, usuario inexistente o inactivo; sólo `request.cookies`, `Authorization` ignorado), porque `/auth/yo` y `/auth/cambiar-password` lo necesitan y la "versión mínima" sería la misma función. También crea `AsignacionRolRepository.roles_vigentes(usuario_id)` porque el token y `/auth/yo` los necesitan. C-06 agrega: la dependencia de roles vigentes para autorizar, `requiere_rol` (403), el control del cambio obligatorio (403), los dos grupos de rutas en `main.py`, `/usuarios`, `/eventos` y los eventos de personal/roles. Diferencia con `CHANGES.md`: allí `get_usuario_actual` figura en el scope de C-06; C-06 lo reutiliza en lugar de crearlo (actualizar la línea de C-06 al archivar C-05).
- Alternativa descartada: una dependencia "mínima" sólo para `/auth` que C-06 reemplace — duplicaría la validación del token.

### D2 — `app/core/security.py`
- `PasswordBcrypt = Annotated[str, StringConstraints(min_length=1), AfterValidator(_max_72_bytes)]`: `len(v.encode("utf-8")) > 72` → `ValueError` → 422 en el contrato. Se usa en registro, login (`password`) y cambio (`password_actual`, `password_nueva`).
- `async def hashear_password(plano) -> str` y `async def verificar_password(plano, hash) -> bool`: `async with _SEMAFORO: await asyncio.to_thread(bcrypt.hashpw/checkpw, ...)`; costo `get_settings().BCRYPT_ROUNDS`.
- Semáforo: `_SEMAFORO = asyncio.Semaphore(BCRYPT_CONCURRENTES)` a nivel de módulo con `BCRYPT_CONCURRENTES = 4` (constante comentada). Desde Python 3.10 el semáforo no se ata a un bucle al construirse (lo toma en el primer `acquire`), así que crearlo al importar es seguro, a diferencia del motor (regla 7). El PDF sólo exige configurable el costo, no la concurrencia; por eso no se agrega variable de entorno.
  - Alternativa: semáforo en `app.state` creado en el lifespan — obligaría a pasarlo por router → servicio en cada operación sin beneficio.
- `crear_token(usuario_id, roles) -> str`: `jwt.encode({"sub": str(id), "exp": ahora + ACCESS_TOKEN_EXPIRE_SECONDS, "roles": roles}, JWT_SECRET_KEY, "HS256")`.
- `leer_token(token) -> PayloadToken | None`: `jwt.decode(..., algorithms=["HS256"], options={"require": ["sub", "exp"]})`; cualquier `jwt.InvalidTokenError` (incluye vencido) o `sub` no entero → `None`.
- `poner_cookie_sesion(response, token)` / `borrar_cookie_sesion(response)`: `set_cookie("access_token", token, max_age=ACCESS_TOKEN_EXPIRE_SECONDS, httponly=True, samesite="lax", secure=COOKIE_SECURE, path="/")` y `delete_cookie` con los mismos atributos (si difieren, algunos navegadores no la borran).
- Constante `COOKIE_SESION = "access_token"`.

### D3 — Hash ficticio en el lifespan
`app.state.hash_ficticio = await security.hashear_password(secrets.token_urlsafe(32))`: mismo costo y mismo camino (hilo + semáforo) que un hash real, sobre un valor aleatorio que nadie conoce. Además el servicio exige `usuario is not None` para dar éxito, así que aunque la verificación contra el ficticio diera `True`, el login falla. Se corrige el placeholder actual (constante `b"hash-ficticio"`).

### D4 — Módulo `usuarios` por capas
- `schemas.py` (todos `BaseModel`, entradas con `extra="forbid"`): `RegistroIn {email, nombre, password}`, `LoginIn {email, password}`, `CambiarPasswordIn {password_actual, password_nueva}`, `UsuarioRead {id, email, nombre, activo, debe_cambiar_password}` (`from_attributes`, nunca `password_hash`), `LoginOut {mensaje, debe_cambiar_password, expira_en_segundos}`, `YoOut {usuario: UsuarioRead, roles_vigentes: list[Rol], roles_token: list[str]}`, `MensajeOut {mensaje}`.
- `repository.py`: `UsuarioRepository(BaseRepository[Usuario])` + `get_by_email`; `AsignacionRolRepository` + `roles_vigentes(usuario_id)` (`revocada_en IS NULL AND (vence_en IS NULL OR vence_en > :ahora)`, ordenado); `IntentoAccesoRepository` + `fallos_recientes(email, ip, ahora)` (D6); `EventoSeguridadRepository` (sólo `add`).
- `clientes/repository.py`: `ClienteRepository(BaseRepository[Cliente])` sin métodos extra (C-07 lo amplía).
- `unit_of_work.py`: `UsuariosUnitOfWork(session)` con `usuarios`, `asignaciones`, `clientes`, `eventos`, `intentos` (este último sólo para **leer** el límite). `IntentosAccesoUnitOfWork(session_factory)` (D5).
- `router.py`: `router = APIRouter(prefix="/auth", tags=["auth"])` con `get_uow` (desde `get_session`) y `get_intentos_uow` (desde `request.app.state.session_factory`). El servicio recibe ambos UoW sin abrir. `main.py`: `app.include_router(auth_router)`. C-06 sumará el router `/usuarios` en el mismo módulo.

### D5 — `intento_acceso` en su propio UoW (DD-09)
`IntentosAccesoUnitOfWork` recibe la **fábrica** (no una sesión): en `__aenter__` abre una sesión propia y crea `self.intentos`; en `__aexit__` confirma (o revierte si hubo excepción) y **cierra** la sesión, porque esta vez la creó él. El comentario obligatorio de tres puntos va en esta clase:
- *Qué hace distinto*: abre su propia sesión y transacción y confirma siempre, independiente del UoW de la petición.
- *Por qué*: el fallo que se quiere contar (401) es el mismo que revierte la transacción de la petición; si compartiera la transacción, el intento fallido desaparecería con el rollback y el límite de RN-07 nunca se alcanzaría.
- *Costo*: deja filas aunque la petición falle (es lo buscado) y usa una segunda conexión del pool durante la escritura.
El servicio lo usa en un solo punto: `async with intentos_uow: await intentos_uow.intentos.add(IntentoAcceso(...))`. Sigue sin tocar sesiones.

### D6 — Consulta del límite (una consulta)
```sql
SELECT cuando FROM intento_acceso
WHERE email = :email AND ip = :ip AND NOT exito
  AND cuando > :ahora - interval '60 s'
  AND cuando > COALESCE((SELECT max(cuando) FROM intento_acceso
                         WHERE email = :email AND ip = :ip AND exito), '-infinity')
ORDER BY cuando DESC LIMIT 5
```
(escrita con `select()` de SQLAlchemy, subconsulta escalar). Si devuelve 5 filas → bloqueado; `Retry-After = ceil(quinta.cuando + 60 s − ahora)`, mínimo 1: es el momento en que el fallo más viejo de esos cinco sale de la ventana. Usa el índice `(email, ip, cuando)`. `ahora` sale de Python (`datetime.now(UTC)`), igual que el default de `cuando`, para no mezclar relojes. Constantes `MAX_FALLOS = 5`, `VENTANA = timedelta(seconds=60)` en el servicio.

### D7 — Orden del login (sección 5.5) sin conexión tomada durante bcrypt
```
async with uow:                                   # bloque 1: sólo lecturas
    fallos = intentos.fallos_recientes(...)       # 1) límite: una consulta
    si bloqueado → raise DemasiadosIntentos(retry_after)   # 429, sin hash, sin registrar (Q-20)
    usuario = usuarios.get_by_email(email)
# fuera del bloque: la conexión vuelve al pool
ok = await verificar_password(password, usuario.password_hash si existe, si no hash_ficticio)   # 2)
exito = ok and usuario is not None and usuario.activo
async with intentos_uow: registrar intento (email, ip, exito)   # 3) siempre, sesión propia
si no exito → raise CredencialesInvalidas("Correo o contraseña incorrectos")   # 401
async with uow: roles = asignaciones.roles_vigentes(usuario.id)   # bloque 2: sólo en el éxito
token = crear_token(usuario.id, roles) → ResultadoLogin(token, debe_cambiar_password, expira)
```
El router pone la cookie con `security.poner_cookie_sesion` y devuelve `LoginOut` con `mensaje="Sesión iniciada"`. Los roles se leen recién después de verificar y sólo si el login es correcto (segundo bloque del mismo UoW; el UoW base no cierra la sesión, así que se puede volver a abrir): así los dos caminos de fallo — correo inexistente y contraseña mala — hacen exactamente las mismas consultas y el mismo bcrypt (RN-08).
- La IP sale de `request.client.host` (en el router; si es `None`, `"desconocida"`).

### D8 — `get_usuario_actual` sin conexión retenida
Dependencia en `app/core/dependencies.py`: lee `request.cookies.get(COOKIE_SESION)`; `leer_token` → `None` → 401; carga el usuario con `UsuarioRepository(session).get_by_id(sub)` dentro de `async with UnitOfWork(session)` (sólo lectura: al salir confirma, no hay cambios, y la conexión vuelve al pool antes de que el servicio llame a bcrypt). `session` sale de `Depends(get_session)`, la misma que usa el UoW del router (FastAPI cachea la dependencia por petición). Con `expire_on_commit=False` el objeto sigue cargado. Inexistente o inactivo → 401. Devuelve `SesionActual(usuario, roles_token)` (dataclass); alias `UsuarioActualDep`. Todos los 401 llevan `{"detail": "No autenticado"}` y `WWW-Authenticate` no se envía (no es esquema Bearer).
- Alternativa descartada: dejar la transacción implícita abierta tras la lectura — en `cambiar-password` la conexión quedaría tomada durante la verificación bcrypt, justo lo que el PDF prohíbe.

### D9 — Registro y cambio de contraseña
- Registro: `hash = await hashear_password(...)` **antes** de `async with uow:`; dentro: `usuarios.add(Usuario(...))` (flush → id), `asignaciones.add(AsignacionRol(usuario_id, rol=CLIENTE))`, `clientes.add(Cliente(nombre, email, usuario_id))`. Correo repetido en `usuario` o en `cliente` → `IntegrityError` 23505 en el flush → el UoW revierte todo → el router lo traduce con `traducir_errores("Ya existe una cuenta o un cliente con ese correo")` → 409. Sin consulta previa (unicidad garantizada por la base). Un único mensaje para los dos UNIQUE: distinguirlos exigiría leer el nombre de la restricción del error de la base. No deja evento: RN-16 cubre alta de **personal**, cambio de rol y cambio de contraseña; el auto-registro de un cliente no es ninguno (el PDF no lo pide).
- Cambio: `ok = await verificar_password(actual, usuario.password_hash)` (fuera de transacción, gracias a D8); falso → `CredencialesInvalidas("La contraseña actual no es correcta")` → 401 (Q-11). `nuevo = await hashear_password(nueva)`; luego `async with uow:` releer el usuario por id, `usuarios.update(u, {password_hash, debe_cambiar_password: False})`, `eventos.add(EventoSeguridad(actor=u.email, accion="Cambio de contraseña"))`. Respuesta 200 `{"mensaje": "Contraseña actualizada"}`, sin tocar la cookie.

### D10 — Correo
Mismo patrón que `clientes/schemas.py` (`^[^@\s]+@[^@\s]+$`, mínimo 3), recortado y en minúsculas con un `AfterValidator`, en registro y login, para que `Ana@Example.com` y `ana@example.com` no sean dos cuentas ni dos contadores de intentos. No se usa `EmailStr`: `email-validator` puede rechazar dominios reservados y los datos del PDF usan `example.com`.

### D11 — Errores del dominio
En `app/core/errores.py`: `CredencialesInvalidas(mensaje)` → 401 y `DemasiadosIntentos(retry_after: int)` → 429 con `{"detail": "Demasiados intentos fallidos; probá de nuevo más tarde"}` y header `Retry-After`. Se agregan a `traducir_errores` (no cambia su firma). Los 401 de la dependencia se lanzan como `HTTPException` directamente (es capa HTTP).

### D12 — Decisiones del usuario (Q resueltas)
Regla del usuario: "donde la consigna no dice nada de errores, se usa el default; donde dice algo, se sigue la consigna".
- **Q-09**: el registro crea usuario + CLIENTE + ficha con `nombre` del cuerpo, en una transacción; correo repetido (usuario o cliente) → 409 por UNIQUE, sin filas sueltas y sin apropiarse de la ficha existente (D9).
- **Q-11**: contraseña actual incorrecta → 401 con mensaje propio (la tabla del PDF sólo admite 200/401/422).
- **Q-20**: el 429 no se anota en `intento_acceso` (no extiende el bloqueo; C-05 del PDF pide que estén "los cinco fallos").
- **Q-05** (contraseñas del seed): se difiere a C-09.

### D13 — Verificación sin pytest (DD-01)
Un archivo `parcial/test/auth.http` con los casos C-02..C-05 del PDF, cada pedido con su respuesta esperada en comentario y sesiones con `# @name` / `# @no-cookie-jar` / `Cookie:`. Como `seed.py` llega en C-09, el archivo arranca registrando sus propios usuarios y crea el cliente sin usuario con `POST /clientes/` (ruta del TP, aún abierta). Precondición: base migrada (`alembic upgrade head`) y vaciada de las filas de prueba (se documenta el `TRUNCATE` en la cabecera del archivo). C-09 lo reparte en los archivos definitivos por caso (los nombres `C-0N_*.http` actuales son de la numeración del TP, IN-04).

## Risks / Trade-offs

- [Diferencias de tiempo residuales entre correo existente e inexistente] → ambos caminos hacen 2 consultas + 1 bcrypt del mismo costo + 1 INSERT; la variación que queda es ruido de red/base. C-04 del PDF pide "tiempo parecido".
- [Semáforo a nivel de módulo] → si algún día se usa con varios bucles (p. ej. tests con bucles distintos) fallaría; hoy hay un solo bucle de uvicorn y no hay pytest.
- [`intento_acceso` usa una segunda conexión] → con `DB_POOL_SIZE=5` y ráfagas de logins puede esperar por el pool; es breve (un INSERT) y ocurre después de liberar la del bloque 1.
- [IP detrás de un proxy] → `request.client.host` sería la del proxy y el límite se compartiría; en el parcial uvicorn corre directo. No se confía en `X-Forwarded-For` (falsificable).
- [Cambio de contraseña no invalida tokens] → exigido por la consigna; documentado.
- [Reloj] → `cuando` y `ahora` salen del mismo proceso Python; no hay mezcla con `now()` de PostgreSQL.

## Migration Plan

Sin migraciones ni cambios de esquema. Despliegue: reiniciar uvicorn. Rollback: revertir el commit (las rutas `/auth` desaparecen; las filas en `usuario`/`intento_acceso` quedan sin uso).

## Open Questions

Ninguna que cambie specs o tareas. Mensajes exactos de 401/409/429 elegidos en D8, D9 y D11 (el PDF sólo exige "mensaje propio").
