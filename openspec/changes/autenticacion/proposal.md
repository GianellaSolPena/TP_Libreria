# Proposal

## Why

El Ej. 4 del PDF (14 puntos) pide abrir el sistema a usuarios con contraseña: registro, login con cookie `access_token`, cierre de sesión, `GET /auth/yo` y cambio de contraseña, con bcrypt fuera del bucle y bajo semáforo, el orden del login de la sección 5.5 (límite de intentos → verificación real o contra hash ficticio) y el JWT sólo en una cookie HttpOnly. El Ej. 7 suma que cada intento de login se anote en `intento_acceso` con sesión y transacción propias. Las tablas (`usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`, `cliente.usuario_id`) ya existen desde C-03 y la base de capas desde C-04; falta el módulo que las usa. Es requisito de C-06 (autorización), que necesita el usuario actual y los roles vigentes.

## What Changes

- **Nuevo** `parcial/app/core/security.py`: hash y verificación bcrypt con `asyncio.to_thread` bajo un `asyncio.Semaphore`, costo `BCRYPT_ROUNDS` de `Settings`; tipo de contrato `PasswordBcrypt` (1..72 **bytes** UTF-8 → si no, 422); emisión y verificación del JWT (PyJWT, HS256, `sub`, `exp`, `roles`) con `JWT_SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_SECONDS`; helpers para poner y borrar la cookie `access_token` (HttpOnly, SameSite=Lax, Max-Age = duración del token, Secure = `COOKIE_SECURE`).
- **Nuevo** `parcial/app/core/dependencies.py` con `get_usuario_actual` (cookie de `request.cookies`; nunca `Authorization`; 401 sin cookie, token inválido/vencido, usuario inexistente o inactivo), que C-06 reutiliza y amplía.
- **Nuevo** módulo `usuarios` por capas: `schemas.py`, `repository.py` (usuario, asignación de rol con `roles_vigentes`, intento de acceso con la consulta del límite, evento de seguridad), `unit_of_work.py` (UoW de la petición + UoW propio de `intento_acceso` con sesión propia, DD-09), `service.py`, `router.py` con prefijo `/auth`.
- **Nuevo** `parcial/app/modules/clientes/repository.py` (`ClienteRepository`, mínimo para el registro; C-07 lo amplía).
- **Nuevos endpoints** (grupo abierto; el segundo grupo llega en C-06):
  - `POST /auth/registro` → 201/409/422: usuario + rol CLIENTE + ficha de cliente en un bloque (RN-02, Q-09).
  - `POST /auth/login` → 200/401/422/429: cuerpo `{mensaje, debe_cambiar_password, expira_en_segundos}`, token sólo en `Set-Cookie` (RN-07, RN-08).
  - `POST /auth/logout` → 200, borra la cookie siempre.
  - `GET /auth/yo` → 200/401: usuario, roles vigentes y roles del token.
  - `POST /auth/cambiar-password` → 200/401/422: contraseña + `debe_cambiar_password=false` + evento en un bloque (RN-16); actual incorrecta → 401 (Q-11); no emite token ni invalida sesiones.
- **Errores**: `app/core/errores.py` suma `CredencialesInvalidas` (401) y `DemasiadosIntentos` (429 + `Retry-After`) a `traducir_errores`.
- **Lifespan**: el hash ficticio pasa a calcularse con `security.hashear_password` sobre un valor aleatorio (hoy usa `bcrypt.hashpw` directo sobre una constante conocida).
- `main.py` incluye el router de `/auth`.
- Archivo `.http` con los casos C-02..C-05 del PDF (respuesta esperada en comentario).
- `knowledge-base/10_preguntas_abiertas.md`: Q-09, Q-11 y Q-20 pasan a resueltas.

Fuera de alcance (C-06): roles vigentes como dependencia de autorización, `requiere_rol`, control del cambio obligatorio, los dos grupos de rutas, `/usuarios`, `/eventos`, eventos de alta de personal y de roles. Seed y contraseñas del seed (Q-05) → C-09.

## Capabilities

### New Capabilities
- `autenticacion`: registro, login con cookie JWT, cierre de sesión, `/auth/yo`, cambio de contraseña, manejo de contraseñas con bcrypt y el usuario actual a partir de la cookie.
- `intentos-acceso`: registro de cada intento de login en su propia transacción y límite de intentos fallidos (RN-07) con `Retry-After`.

### Modified Capabilities
<!-- ninguna: `configuracion-ciclo-vida` ya exige el hash ficticio calculado una vez al arrancar; C-05 sólo cambia cómo se calcula. -->

## Impact

- Código: `parcial/app/core/{security,dependencies,errores}.py`, `parcial/app/modules/usuarios/{schemas,repository,unit_of_work,service,router}.py`, `parcial/app/modules/clientes/repository.py`, `parcial/main.py`, `parcial/test/` (un `.http` nuevo).
- API: cinco rutas nuevas bajo `/auth`. Las rutas existentes no cambian (siguen sin autorización hasta C-06).
- Sin cambios de esquema ni de migraciones; sin dependencias nuevas (`bcrypt` 5 y `PyJWT` ya están en `requirements.txt`).
- Governance CRÍTICO (auth): el apply requiere aprobación explícita del usuario.
